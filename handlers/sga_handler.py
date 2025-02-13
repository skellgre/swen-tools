from logging import Logger
import serial
import time
from utils.minicom import find_active_ttyUSB_port, execute_commands_on_ttyUSB_port, find_response_in_terminal_output, CommandFailedError


SERIAL_CONFIG = {
    "baudrate": 115200,
    "bytesize": serial.EIGHTBITS,
    "parity": serial.PARITY_NONE,
    "stopbits": serial.STOPBITS_ONE,
    "timeout": 10,
    "rtscts": False,
    "xonxoff": False,
}
def serial_command(ser: serial.Serial, cmd, logger: Logger):
    assert ser.is_open
    time.sleep(0.1)
    ser.write(cmd + b"\r")
    ser.flush()
    logger.debug(f"Executed command over serial: '{cmd}'")

    return ser

def check_sga_pre_state(ser: serial.Serial, logger: Logger) -> str:
    logger.info(f"Checking SGA pre-state...")

    ser.write(b'\r')
    time.sleep(5)

    output = ser.read(ser.in_waiting or 1024).decode('utf-8', errors='replace').strip()
    logger.debug(f"Received: {output}")

    if "login" in output.lower():
        logger.info("Login prompt detected.")
        return "login_required"

    elif "$" in output:
        logger.info("Already logged in (bash shell detected).")
        return "logged_in"

    elif "=>" in output:
        logger.info("Already in SGA environment (special prompt detected).")
        return "uboot"

    else:
        logger.warning("Unknown state detected.")
        return "unknown"

def login_user(ser: serial.Serial, user: str, password, logger: Logger):
    logger.info("Logging in...")
    serial_command(ser, bytes(user, "utf-8"), logger)
    serial_command(ser, bytes(password, "utf-8"), logger)
    
def enter_uboot(ser: serial.Serial, logger: Logger):
    logger.info("Rebooting and entering U-Boot mode...")

    serial_command(ser, b"sudo reboot", logger)
  
    timeout = 10  # Maximum time to wait in seconds
    start_time = time.time()

    logger.info("Sending ESC key to interrupt boot process...")
    
    while time.time() - start_time < timeout:
        ser.write(b"\x1b")  # ESC key
        time.sleep(0.5)  # Adjust timing if needed

        output = ser.read(ser.in_waiting or 1024).decode('utf-8', errors='replace')
        logger.debug(f"Received: {output}")

        if "=>" in output:
            logger.info("U-Boot prompt detected!")
            return True

    logger.error("Failed to enter U-Boot mode, timeout reached.")
    return False


def uboot_flash(ser, logger: Logger):
    """flash SGA"""
    logger.info("Preparing to flash SGA")

    serial_command(ser, b"\rmw 0x2A30000 0;\r", logger)
    serial_command(ser, b"setenv serverip 169.254.4.30", logger)
    serial_command(ser, b"setenv ipaddr 169.254.4.10", logger)
    serial_command(ser, b"tftpboot nvOTAscript.img", logger)
    time.sleep(20) # ToDO
    logger.info("Starting the SGA flashing process")
    serial_command(ser, b"source 0x90000000\r", logger)
    print("flashing (this takes several minutes) ...")

def flash_sga(logger: Logger):
    try:
        port_num = find_active_ttyUSB_port(prompt=["DoIP-VCC", "=>"] , max_ports=6, logger=logger)
        port = f"/dev/ttyUSB{port_num}"
        logger.info(f"Connecting to {port} for command execution.")
        user = "swupdate"
        password = "swupdate"
        

        with serial.Serial(port, **SERIAL_CONFIG) as ser:
            prestate = check_sga_pre_state(ser, logger)
            logged_in = False

            if prestate == "uboot":
                logger.warning("SGA stuck in uboot, resetting...")
                serial_command(ser, b"reset\r", logger)

            if prestate == "login_required":
                login_user(ser, user, password, logger)
                logged_in = True


            if logged_in or prestate =="logged_in":
                enter_uboot(ser, logger)
            else:
                pass # unknown command
                


    except serial.SerialException as e:
        logger.error(f"Error communicating with port {port_num}: {e}")
        raise
    finally:
        ser.close()