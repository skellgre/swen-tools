import os
import subprocess
from logging import Logger
from logger.logger_config import super_message
import serial
import time
from utils.minicom import *

SUDO_PASSWORD = os.getenv("SUDO_PASSWORD")

SERIAL_CONFIG = {
    "baudrate": 115200,
    "bytesize": serial.EIGHTBITS,
    "parity": serial.PARITY_NONE,
    "stopbits": serial.STOPBITS_ONE,
    "timeout": 10,
    "rtscts": False,
    "xonxoff": False,
}


def wait_sga_running(ser, quiet):
    """Waits until the SGA has started up."""
    import time
    from lib.common import function_failure

    log_in_user(ser, quiet)
    logger.info("Waiting for systemd to finish starting services")
    print("waiting for systemd to finish starting services ...") if not quiet else None
    serial_command(
        ser, b"systemctl is-system-running --wait\r", quiet, read_until=b"~$"
    )
    logger.info("Waiting for OBD port tcp/3458 to get open")
    print("checking if port 13400 is open ...") if not quiet else None
    ser.timeout = 2
    deadline = time.time() + 200
    while time.time() < deadline:
        lines = serial_command(
            ser,
            b"grep -o '[0-9]\\+: [0-9A-F]\\+:3458' /proc/net/tcp\r",
            quiet,
            timeout=0,
        ).read_until(b"~$")
        logger.debug(f"Received over serial from the SGA: '{lines}'")
        echo(lines, quiet)
        if bytes(":3458", "ascii") in lines:
            logger.info("OBD port tcp/3458 is now open")
            print("OBD port (13400) is now up") if not quiet else None
            return
    function_failure("ERROR: OBD port (13400) is not up")



def check_sga_pre_state(ser: serial.Serial, serial_executor: SerialCommandStrategy, logger: Logger) -> str:
    logger.info(f"Checking SGA pre-state...")
    
    _, output = serial_executor.execute(ser, b"\x04", b"login", timeout=2, logger=logger)

    if "login" in output.lower():
        logger.debug("Login prompt detected.")
        return "login_required"

    elif "$" in output:
        logger.debug("Already logged in (bash shell detected).")
        return "logged_in"

    elif "=>" in output:
        logger.debug("Already in SGA environment (special prompt detected).")
        return "uboot"

    else:
        logger.warning("Unknown state detected.")
        return "unknown"


def login_user(ser: serial.Serial, serial_executor: SerialCommandStrategy, user: str, password: str, logger: Logger):
    logger.info("Logging in...")
    serial_executor.execute(ser, bytes(user, "utf-8"), b"", 1, logger)
    serial_executor.execute(ser, bytes(password, "utf-8"), b"$", 1, logger)



def enter_uboot(ser: serial.Serial, serial_executor: SerialCommandStrategy, timeout, logger: Logger):
    logger.info("Rebooting and entering U-Boot mode...")

    serial_executor.execute(ser, b"sudo reboot", b"", timeout=0, logger=logger)
    start_time = time.time()
    logger.debug("Sending ESC key to interrupt boot process...")

    while time.time() - start_time < timeout:
        ser.write(b"\x1b")  # ESC key
        time.sleep(0.5)

        output = ser.read(ser.in_waiting or 1024).decode("utf-8", errors="replace")
        logger.debug(f"Received: {output}")

        if "=>" in output:
            logger.info("U-Boot prompt detected!")
            return True

    logger.error("Failed to enter U-Boot mode, timeout reached.")
    return False


def uboot_flash(ser, serial_executor: SerialCommandExecutor, logger: Logger):
    """Flash SGA"""
    logger.info("Preparing to flash SGA")

    serial_executor.execute(ser, b"", b"", 1 ,logger)
    serial_executor.execute(ser, b"mw 0x2A30000 0", b"", 1 ,logger)
    serial_executor.execute(ser, b"setenv serverip 169.254.4.30", b"", 1, logger)
    serial_executor.execute(ser, b"setenv ipaddr 169.254.4.10", b"", 1, logger)
    serial_executor.execute(ser, b"tftpboot nvOTAscript.img", b"done", 20, logger)

    flashing_time = 60 * 8 # 7 minutes
    #time.sleep(20)  # ToDO
    logger.debug("Starting the SGA flashing process")
    super_message("Flashing SGA")
    start_time = time.time()
    success, _ = serial_executor.execute(ser, b"source 0x90000000\r", b"login", flashing_time, logger)
    end_time = time.time()
    if success:
        super_message("Done!")
    else:
        logger.error("Failed to flash SGA")
    return end_time - start_time
    
    

def _find_sga_port(serial_executor: SerialCommandExecutor, logger: Logger):
    return search_correct_ttyUSB_port(6, serial_executor, ["DoIP-VCC", "=>"], 0.5, logger)

def unblock_firewall_for_file_transerffering(password: str, logger: Logger):
    try:
        command = ["sudo", "-S", "iptables", "-A", "INPUT", "-p", "udp", "--dport", "69", "-j", "ACCEPT"]
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        process.stdin.write(f"{password}\n")
        process.stdin.flush()
        logger.info("Successfully unblocked firewall for file transfer.")
    except subprocess.CalledProcessError as e:
        logger.warning(f"Error executing command: {e}")


def flash_sga(logger: Logger):
    try:
        unblock_firewall_for_file_transerffering(SUDO_PASSWORD, logger)
        serial_strategy = BasicSerialCommand()
        serial_executor = SerialCommandExecutor(serial_strategy)

        user = "swupdate"
        password = "swupdate"
        reset_uboot_timeout = 15
        enter_uboot_timeout = 15
        port = _find_sga_port(serial_executor, logger)

        with serial.Serial(port, **SERIAL_CONFIG) as ser:

            prestate = check_sga_pre_state(ser, serial_executor, logger)
            logged_in = False

            if prestate == "uboot":
                logger.warning("SGA stuck in uboot, resetting...")
                serial_executor.execute(ser, b"reset\r", b"login", reset_uboot_timeout, logger)
                login_user(ser, serial_executor, user, password, logger)
                logged_in = True

            if prestate == "login_required":
                login_user(ser, serial_executor, user, password, logger)
                logged_in = True

            if logged_in or prestate == "logged_in":
                if enter_uboot(ser, serial_executor, enter_uboot_timeout, logger):
                    total_time = uboot_flash(ser, serial_executor, logger)
                    formatted_time = time.strftime("%H:%M:%S", time.gmtime(total_time))
                    logger.info("Total time: ", formatted_time)
                    
            else:
                logger.warning("Failed to check SGA prestate")

    except serial.SerialException as e:
        logger.error(f"Error communicating with port {port}: {e}")
    except PortNotFoundError:
        pass

        
