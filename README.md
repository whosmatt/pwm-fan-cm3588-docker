# pwn-fan-cm3588-docker
Dockerized version of the application below.  
Intended to be used and configured via docker-compose.  
NVME monitoring is not available in this fork but can be implemented.  

A multi-arch docker image is automatically built and pushed to docker hub as `whosmatt/pwm-fan-cm3588`

## Example docker-compose file

```yaml
services:
   pwm-fan:
      image: whosmatt/pwm-fan-cm3588:latest
      container_name: pwm-fan-cm3588
      volumes:
         - /sys/class/thermal:/sys/class/thermal
      restart: unless-stopped
      environment:
         # All variables are optional, these are the defaults
         DEBUG: "0"
         SLEEP_TIME: "15"
         MIN_STATE: "1"
         LOWER_TEMP_THRESHOLD: "45.0"
         UPPER_TEMP_THRESHOLD: "65.0"
         MIN_DELTA: "0.01"
         NVME_DEVICES: "/dev/nvme?"
         NVME_COMMAND: "nvme"
         THERMAL_DIR: "/sys/class/thermal"
         DEVICE_TYPE_PWM_FAN: "pwm-fan"
         THERMAL_ZONE_NAME: "thermal_zone"
         DEVICE_NAME_COOLING: "cooling_device"
         FILE_NAME_CUR_STATE: "cur_state"
```

**Notes:**
- Mounting the entire `/sys/class/thermal` directory gives the container access to all thermal devices, which is usually sufficient for fan control and avoids the need for `privileged: true`.


# pwm-fan-cm3588
Control the 5V PWM fan on a [CM3588 NAS](https://www.friendlyelec.com/index.php?route=product/product&path=60&product_id=299).

Developed and tested on Armbian only (output of ```lsb_release -a``` shown below. Kernel: 6.12.1-edge-rockchip-rk3588).
```
Distributor ID: Debian
Description:    Armbian 25.2.3 bookworm
Release:        12
Codename:       bookworm
```



Might work on other RK3588 SBC also (like Orange PI 5+).

### Disclaimer
Usage of this software is purely at your own risk. I am just sharing what I developed for myself and use at home.

### Features:
1. Runs as background service
2. Changes fan speed as per the temperature (configurable).

## Test before you install as background service.
1. Run `./test.py` and it should run without any errors. It should show some messages like following (example taken from my machine)
   ```
   2025-04-10 23:19:59,742 - INFO - Fan device: /sys/class/thermal/cooling_device4
   2025-04-10 23:19:59,743 - INFO - Maximum state allowed: 5
   2025-04-10 23:19:59,743 - INFO - Current state is set to: 1
   ```
2. Try setting some speed for the fan where 0 mean off, and any value above 0 upto "Maximum state" sets different speeds.
   For example `./test.py --desired-state 5` will set it to maximum speed on my machine. Running `./test.py --desired-state 0` switches off the fan on my machine.
3. If all goes well, test a bit more as following instructions.

## Test even more before you install as background service.
1. In one terminal, run the script `./fan_control.py`. This runs the script in foreground and debug logging enabled. The logs are pretty detailed. Leave it running.
2. In another terminal, simulate stress on the CPU using `stress --cpu 8 --timeout 120` command. This will put CPU in 100% load for 120 seconds.
3. In the first terminal, notice the logs and also the fan speeding up when temperature rises and slowing down again when the command finishes and CPU cools down.
4. If all goes well, kill the script by pressing ctrl-c and proceed to install it as background service.

## Steps to get it running as background service.
1. The script has dependency on python systemd module (to send log messages to system journal). I installed it using `apt-get install python3-systemd`
2. Copy the file `fan_control.py` to `/usr/local/bin/fan_control.py`
3. Copy the file `fan_control.service` to `/etc/systemd/system/fan_control.service`
4. Run the command `systemctl daemon-reload`
5. Enable the service by running `systemctl enable --now fan_control.service`

Now you can see the logs by running `journalctl -u pwm-fan-cm3588`
You can also configure the various parameters in the script itself by editing /usr/local/bin/fan_control.py (like temperature ranges which controls various fan speeds).

## Steps to uninstall.
1.  Disable the service by running `systemctl disable --now fan_control.service`
2.  Delete `/etc/systemd/system/fan_control.service`
3.  Delete `/usr/local/bin/fan_control.py`
4.  Run the command `systemctl daemon-reload`

## My setup
My NAS is running in the case created using the great work by [https://github.com/Nighthater/CM3588-NAS-Case](https://github.com/Nighthater/CM3588-NAS-Case).

I am using a Noctua 80mm fan.

![New Case - Assembled](https://github.com/user-attachments/assets/ff35cb40-59f0-4c74-8cb2-99f19f7d2271)
