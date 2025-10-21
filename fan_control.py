#!/usr/bin/python
import os
import time
import logging
import glob
import subprocess
import shutil

# Set debug mode based on the environment variable "DEBUG"
# The DEBUG variable can be set to "true", "True", or "1" (case-insensitive)
DEBUG = os.environ.get("DEBUG", "1").lower() in ["1", "true", "on"]


# Always log to stdout/stderr (container output)
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


logger = logging.getLogger(__name__)

# Configuration variables (read from environment)
SLEEP_TIME = int(os.environ.get("SLEEP_TIME", 5 if DEBUG else 15))
MIN_STATE = int(os.environ.get("MIN_STATE", 1))  # if you set it to 0, the fan will switch off when temperature falls below LOWER_TEMP_THRESHOLD
LOWER_TEMP_THRESHOLD = float(os.environ.get("LOWER_TEMP_THRESHOLD", 45.0))
UPPER_TEMP_THRESHOLD = float(os.environ.get("UPPER_TEMP_THRESHOLD", 65.0))
MIN_DELTA = float(os.environ.get("MIN_DELTA", 0.01))  # Minimum temperature change to trigger speed change

NVME_DEVICES = os.environ.get("NVME_DEVICES", "/dev/nvme?")
NVME_COMMAND = os.environ.get("NVME_COMMAND", "nvme")

THERMAL_DIR = os.environ.get("THERMAL_DIR", "/sys/class/thermal")
DEVICE_TYPE_PWM_FAN = os.environ.get("DEVICE_TYPE_PWM_FAN", "pwm-fan")
THERMAL_ZONE_NAME = os.environ.get("THERMAL_ZONE_NAME", "thermal_zone")
DEVICE_NAME_COOLING = os.environ.get("DEVICE_NAME_COOLING", "cooling_device")
FILE_NAME_CUR_STATE = os.environ.get("FILE_NAME_CUR_STATE", "cur_state")
# Or skip the cooling device detection and use a single specific fan such as "cooling_device0"
COOLING_DEVICE_OVERRIDE = os.environ.get("COOLING_DEVICE_OVERRIDE", "")


def format_temp(value):
    res = f"{value:.2f}°C"
    return res


def get_fan_device():
    if COOLING_DEVICE_OVERRIDE:
        dev_path = os.path.join(THERMAL_DIR, COOLING_DEVICE_OVERRIDE)
        if os.path.exists(dev_path):
            return dev_path
        else:
            logger.error(f"COOLING_DEVICE_OVERRIDE set to '{COOLING_DEVICE_OVERRIDE}', but device not found at {dev_path}")
            return None
    for device in os.listdir(THERMAL_DIR):
        if device.startswith(DEVICE_NAME_COOLING):
            dev_path = os.path.join(THERMAL_DIR, device)
            type_file = os.path.join(dev_path, "type")
            try:
                with open(type_file, "r") as f:
                    if DEVICE_TYPE_PWM_FAN in f.read().strip():
                        return dev_path
            except Exception as e:
                logger.error(f"Error while getting fan device: {e}")
    return None


def get_fan_speed(device):
    try:
        cur_state_file = os.path.join(device, FILE_NAME_CUR_STATE)
        with open(cur_state_file, "r") as f:
            res = int(f.read().strip())
            return res
    except Exception as e:
        logger.error(f"Error getting fan speed: {e}")
    return 0


def set_fan_speed(device, speed):
    try:
        logger.warning(f"setting fan speed to {speed}")
        cur_state_file = os.path.join(device, FILE_NAME_CUR_STATE)
        with open(cur_state_file, "w") as f:
            f.write(str(speed))
        return True
    except Exception as e:
        logger.error(f"Error setting fan speed: {e}")
    return False


def get_temperature_slots():
    """
    Creates predefined temperature thresholds and corresponding fan states.

    Returns:
        list of tuples: Each tuple contains (fan_state, temperature_threshold)
    """
    res = None
    max_state = 0
    fan_device = get_fan_device()
    try:
        int(open(f"{fan_device}/max_state", "r").read().strip())
        with open(f"{fan_device}/max_state", "r") as f:
            max_state = int(f.read().strip())
    except Exception as e:
        logger.error(f"Error while getting temperature slots: {e}")
        max_state = 0
        pass

    if max_state <= 0:
        logger.error(f"max_state could not be determined for {fan_device}")
    else:
        temperature_range = UPPER_TEMP_THRESHOLD - LOWER_TEMP_THRESHOLD
        slots = max_state
        step = temperature_range / (slots - 1)
        res = [(x + MIN_STATE, x * step + LOWER_TEMP_THRESHOLD) for x in range(slots)]
    return res


def adjust_speed_based_on_temperature(current_temp):
    """
    Adjusts the fan speed based on the current temperature.

    Args:
        current_temp (float): The current temperature.

    Returns:
        None
    """
    temperature_slots = get_temperature_slots()
    desired_slot = [
        (state, temp) for state, temp in temperature_slots if current_temp >= temp
    ]
    if desired_slot:
        desired_slot = desired_slot[-1]
    elif current_temp <= LOWER_TEMP_THRESHOLD:
        desired_slot = temperature_slots[0]
    else:
        desired_slot = temperature_slots[-1]

    logger.debug(
        f"desired_slot (current_temp: {format_temp(current_temp)}): {desired_slot} (out of {temperature_slots})"
    )

    desired_state, _ = desired_slot

    # Update fan speed only if needed
    fan_device = get_fan_device()
    if get_fan_speed(fan_device) != desired_state:
        logger.info(
            f"fan speed needs to be changed to: {desired_state} (current_temp: {format_temp(current_temp)} | slot: {desired_slot})"
        )
        set_fan_speed(fan_device, desired_state)


def check_command_exists(command):
    # Use shutil.which to find the command in the PATH
    res = shutil.which(command) is not None
    return res


def get_current_nvme_temperatures():
    """
    Reads the NVME temperatures from using nvme command.

    Returns:
        The list of nvme devices and their temperatures.

    Raises:
        Exception: If an error occurs while reading temperature data.
    """
    temps = []
    try:
        if not check_command_exists(NVME_COMMAND):
            return temps
        nvme_devices = glob.glob(NVME_DEVICES)
        for device in nvme_devices:
            try:
                logger.debug(f"Getting temperature for nvme: {device}")
                # Run the nvme smart-log command and capture the output
                result = subprocess.run(
                    [NVME_COMMAND, "smart-log", device],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                # Extract the line containing the temperature information
                for line in result.stdout.splitlines():
                    if line.lower().startswith("temperature"):
                        # Split the line to extract the temperature value
                        parts = line.split(":")
                        if len(parts) > 1:
                            temp_str = parts[1].strip().split()[0]
                            temp_str = "".join([x for x in temp_str if x.isnumeric()])
                            try:
                                # Convert the temperature string to a float
                                temperature_celsius = float(temp_str)
                                device_name = os.path.basename(device)
                                temps.append((device_name, temperature_celsius))
                            except ValueError:
                                logger.error(
                                    f"Error converting temperature to float: {temp_str}"
                                )
                        else:
                            logger.error("Unexpected output format")
            except subprocess.CalledProcessError as e:
                logger.error(f"Command failed with error: {e.stderr}")
            except Exception as e:
                logger.error(f"Command failed with error: {e}")
    except Exception as e:
        logger.error(f"Error while getting nvme temperatures: {e}")
    return temps


def get_current_cpu_temperatures():
    """
    Reads the CPU temperatures from system files.

    Returns:
        The list of cpu devices and their temperatures.

    Raises:
        Exception: If an error occurs while reading temperature data.
    """
    temps = []
    try:
        for zone in os.listdir(THERMAL_DIR):
            if zone.startswith(THERMAL_ZONE_NAME):
                temp_file = os.path.join(THERMAL_DIR, zone, "temp")
                if os.path.exists(temp_file):
                    with open(temp_file, "r") as f:
                        temp = float(f.read().strip()) / 1000.0
                        temps.append((zone, temp))
    except Exception as e:
        logger.error(f"Error while getting current temperature: {e}")
    return temps


def get_current_temp():
    temps = get_current_cpu_temperatures() + get_current_nvme_temperatures()
    temps.sort(key=lambda x: x[0])
    logger.debug("Current temperatures of all devices:")
    for device, temp in temps:
        logger.debug(f"    {device:<20}: {format_temp(temp)}")

    max_temp = max([x[1] for x in temps])
    max_devices = [x[0] for x in temps if x[1] >= max_temp]
    max_devices = ", ".join(max_devices)

    logger.debug(f"Maximum temperature {format_temp(max_temp)} found for {max_devices}")
    return max_temp


def adjust_fan():
    current_temp = get_current_temp()
    adjust_speed_based_on_temperature(current_temp)


def main():
    """Main function to control fan speed."""

    logger.info("PWM Fan control service")

    fan_device = get_fan_device()
    if not fan_device:
        logger.error("No PWM fan device found")
        return

    logger.info(f"Fan device: {fan_device}")
    logger.info("Temperature slots:")
    logger.info(
        "    * when temperature reaches the threshold of a slot, the fan state is set to the corresponding fan_state value)"
    )
    logger.info(
        f"    * when temperature falls below LOWER_TEMP_THRESHOLD (i.e. {format_temp(LOWER_TEMP_THRESHOLD)}), state is set to MIN_STATE (i.e. {MIN_STATE})"
    )
    for fan_state, temperature_threshold in get_temperature_slots():
        logger.info(f"    {format_temp(temperature_threshold):4}: {fan_state}")

    if not check_command_exists(NVME_COMMAND):
        logger.warning(
            f"The command {NVME_COMMAND} does not exist. Install using apt/apt-get."
        )

    while True:
        adjust_fan()
        logger.debug(f"sleeping for {SLEEP_TIME} seconds")
        time.sleep(SLEEP_TIME)  # Check temperature after a delay


def test():
    for x in range(30):
        current_temp = LOWER_TEMP_THRESHOLD - 5 + (x * 1.0)
        adjust_speed_based_on_temperature(current_temp)


if __name__ == "__main__":
    logger.info("Starting fan controller service")
    try:
        # test()
        main()
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
