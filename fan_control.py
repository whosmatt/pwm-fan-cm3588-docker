#!/usr/bin/python
import os
import time
import logging
from systemd.journal import JournalHandler

DEBUG = False

if DEBUG:
    logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
else:
    logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
   handlers=[
       JournalHandler(SYSLOG_IDENTIFIER="fan_control"),  # Send logs to systemd journal
#       logging.FileHandler('/var/log/fan_controller.log'),  # Optional: Log to a file as well
   ]
)


logger = logging.getLogger(__name__)

# Configuration variables
MODE_HEATING="heating"
MODE_COOLING="cooling"
SLEEP_TIMES = {
        MODE_HEATING : 5 if DEBUG else 15 ,
        MODE_COOLING : 10 if DEBUG else 30,
        }

MIN_STATE = 1
LOWER_TEMP_THRESHOLD = 45.0
UPPER_TEMP_THRESHOLD = 65.0
MIN_DELTA = 0.01 # Minimum temperature change to trigger speed change

THERMAL_DIR="/sys/class/thermal"
DEVICE_TYPE_PWM_FAN="pwm-fan"
THERMAL_ZONE_NAME="thermal_zone"
DEVICE_NAME_COOLING="cooling_device"
FILE_NAME_CUR_STATE="cur_state"


def get_fan_device():
    for device in os.listdir(THERMAL_DIR):
        if device.startswith(DEVICE_NAME_COOLING):
            dev_path = os.path.join(THERMAL_DIR, device)
            type_file = os.path.join(dev_path, "type")
            with open(type_file, 'r') as f:
                if DEVICE_TYPE_PWM_FAN in f.read().strip():
                    return dev_path
    return None


def get_fan_speed(device):
    try:
        cur_state_file = os.path.join(device, FILE_NAME_CUR_STATE)
        with open(cur_state_file, 'r') as f:
            res = int(f.read().strip())
            return res
    except Exception as e:
        logger.error(f"Error getting fan speed: {e}")
        return 0


def set_fan_speed(device, speed):
    try:
        cur_state_file = os.path.join(device, FILE_NAME_CUR_STATE)
        with open(cur_state_file, 'w') as f:
            f.write(str(speed))
        return True
    except Exception as e:
        logger.error(f"Error setting fan speed: {e}")
        return False


def get_current_temp():
    """Read CPU temperature from sys file."""
    temps = []
    for zone in os.listdir(THERMAL_DIR):
        if zone.startswith(THERMAL_ZONE_NAME):
            temp_file = os.path.join(THERMAL_DIR, zone, 'temp')
            if os.path.exists(temp_file):
                with open(temp_file, 'r') as f:
                    temp = float(f.read().strip()) / 1000.0
                    temps.append(temp)
    return max(temps) if temps else 0.0


def calculate_speed(temp, min_state, max_state):
    """Calculate fan speed based on current temperature."""
    range_temp = UPPER_TEMP_THRESHOLD - LOWER_TEMP_THRESHOLD
    #temp_per_state = max(1, range_temp / (max_state - min_state))
    temp_per_state = max(1, range_temp / max_state)
    res = min(max_state, 1 + ((temp - LOWER_TEMP_THRESHOLD) // temp_per_state))
    res = int(max(0, res))
    return res


prev_temp = None
desired_state = MIN_STATE
mode = MODE_HEATING
max_state = 0
fan_device = None


def adjust_speed_based_on_temperature():
    """Adjusts speed based on current temperature."""
    global prev_temp
    global desired_state
    global mode
    global fan_device

    current_temp = get_current_temp()

    if prev_temp is None:
        prev_temp = current_temp
        logger.debug("First run. No previous temperature to compare.")
        return # Skip first iteration to set initial state

    if current_temp > prev_temp:
        mode = MODE_HEATING
    else:
        mode = MODE_COOLING

    if abs(current_temp - prev_temp) <= MIN_DELTA:
        return
    
    if current_temp < LOWER_TEMP_THRESHOLD:
        desired_state = MIN_STATE
    elif current_temp > UPPER_TEMP_THRESHOLD:
        desired_state = max_state
    else:
        desired_state = int(calculate_speed(current_temp, MIN_STATE, max_state))

    # Update fan speed only if needed
    if get_fan_speed(fan_device) != desired_state:
        logger.info(f"current_temp: {format_temp(current_temp)} ({LOWER_TEMP_THRESHOLD} - {UPPER_TEMP_THRESHOLD}), Setting fan Speed: {desired_state} ({MIN_STATE} - {max_state})")
        set_fan_speed(fan_device, desired_state)
    else:
        logger.debug(f"current_temp: {format_temp(current_temp)} ({LOWER_TEMP_THRESHOLD} - {UPPER_TEMP_THRESHOLD}), Fan Speed unchanged: {desired_state} ({MIN_STATE} - {max_state})")
    prev_temp = current_temp

def format_temp(value):
    res = f"{value:.2f}°C"
    return res


def main():
    """Main function to control fan speed."""
    global fan_device
    global max_state

    logger.info('PWM Fan control service')

    fan_device = get_fan_device()
    if not fan_device:
        logger.error("No PWM fan device found")
        return

    logger.info(f'Fan device: {fan_device}')

    max_state = 0
    int(open(f"{fan_device}/max_state", 'r').read().strip())
    with open(f"{fan_device}/max_state", 'r') as f:
        max_state = int(f.read().strip())
    
    if max_state <= 0:
        logger.error(f"max_state could not be determined for {fan_device}")
        return
    
    while True:
        adjust_speed_based_on_temperature()
        sleep_time = SLEEP_TIMES[mode]
        logger.debug(f'sleeping for {sleep_time} seconds (mode: {mode})')
        time.sleep(sleep_time)  # Check temperature after a delay

if __name__ == "__main__":
    logger.info("Starting fan controller service")
    try:
        main()
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)

