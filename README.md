# pwm-fan-cm3588
Control the 5V PWM fan on a [CM3588 NAS](https://www.friendlyelec.com/index.php?route=product/product&path=60&product_id=299).

Developed and tested on Armbian only.

Might work on other RK3588 SBC also (like Orange PI 5+).

I have not documented it fully, but TBH, the script is short enough to be read and understood.

### Features:
1. Runs as background service
2. Changes fan speed as per the temperature (configurable).

## Steps to get it running as background service.
1. Clone the repository
2. The script has dependency on python systemd module (to send log messages to system journal). I installed it using `apt-get install python3-systemd`
3. Copy the file fan_control.py to /usr/local/bin/fan_control.py
4. Copy the file fan_control.service /etc/systemd/system/fan_control.service
5. Run the command `systemctl daemon-reload`
6. Enable the service by running `systemctl enable --now fan_control.service`

Now you can see the logs by running `journalctl -u fan_control`
You can also configure the various parameters in the scriot itself by editing /usr/local/bin/fan_control.py (like temperature ranges which controls various fan speeds).

## Steps to uninstall.
1.  Disable the service by running `systemctl disable --now fan_control.service`
2.  Delete /etc/systemd/system/fan_control.service
3.  Delete /usr/local/bin/fan_control.py
4.  Run the command `systemctl daemon-reload`
