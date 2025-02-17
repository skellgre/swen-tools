import serial
import time
from utils.minicom import *
from logger.logger_config import super_message
from datetime import datetime
import subprocess
import sys
from dotenv import load_dotenv
import os

load_dotenv()


# Serial configuration
SERIAL_CONFIG = {
    "baudrate": 115200,
    "bytesize": serial.EIGHTBITS,
    "parity": serial.PARITY_NONE,
    "stopbits": serial.STOPBITS_ONE,
    "timeout": 1,
    "rtscts": False,
    "xonxoff": False,
}

class PortNotFoundError(Exception):
    pass

class CommandFailedError(Exception):
    pass

class FlashScriptError(Exception):
    pass

HPA_FLASH_FILEPATH = os.getenv("HPA_FLASH_FILEPATH")
FLASH_ARGS = "c-sample"
ACTIVATE_RECOVERY_MODE_COMMANDS = ["tegrarecovery x1 on", "tegrareset x1"]
DEACTIVATE_RECOVERY_MODE_COMMANDS = ["tegrarecovery x1 off", "tegrareset x1"]
PROMT = "GoForHIA>"
SUDO_PASSWORD = os.getenv("SUDO_PASSWORD")


def run_flash_script(script_path, args, logger: Logger):
    """
    Runs the external flash script and streams output live.

    Args:
        script_path (str): The full path to the script to execute.
        args (list): A list of arguments to pass to the script.
    """
    logger.info("Running flash script...")
    super_message("Flashing HPA...")
    process = None
    try:
        command = ["sudo", "-S", script_path, args]
        print(command)

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Provide the password and stream output live
        process.stdin.write(f"{SUDO_PASSWORD}\n")
        process.stdin.flush()


        for line in iter(process.stdout.readline, ""):
            logger.info(line.strip())

        for error_line in iter(process.stderr.readline, ""):
            logger.error(error_line.strip())

        process.wait()
        if process.returncode != 0:
            raise FlashScriptError("Flash script execution failed.")

        logger.info("Flash script completed successfully.")
    except Exception as e:
        logger.error(f"Flash script failed with error: {e}")
        raise FlashScriptError("Flash script execution failed.") from e
    finally:
        if process and process.stdin:
            process.stdin.close()
        if process and process.stdout:
            process.stdout.close()
        if process and process.stderr:
            process.stderr.close()

def bootburn_hpa(logger: Logger):
    """Main procedure to automate the flashing process."""
    try:

        strategy = CharacterByCharacterSerialCommand()
        executor = SerialCommandExecutor(strategy)

        

        #port = f"/dev/ttyUSB{port}"
        #with serial.Serial(port, **SERIAL_CONFIG) as ser:
        #    executor.execute(ser, b"test", logger, "Error unknown command: t")
        
        #ser.close()

        port = search_correct_ttyUSB_port(6, executor, "GoForHIA>", 0.5, logger)

        with serial.Serial(port, **SERIAL_CONFIG) as ser:

            # activate_result = execute_commands_on_ttyUSB_port(active_port, ACTIVATE_RECOVERY_MODE_COMMANDS)
            executor.execute(ser, b"tegrarecovery x1 on", b"Command Executed", 2, logger)
            executor.execute(ser, b"tegrareset x1", b"Command Executed", 2, logger)
            # print(activate_result)

            run_flash_script(HPA_FLASH_FILEPATH, FLASH_ARGS, logger)
            executor.execute(ser, b"tegrarecovery x1 off", b"Command Executed", 2, logger)
            executor.execute(ser, b"tegrareset x1", b"Command Executed", 2, logger)


        logger.info("HPA bootburn completed successfully!")
    except PortNotFoundError:
        pass
    except CommandFailedError:
        pass
    except FlashScriptError:
        pass
    except KeyboardInterrupt:
        logger.info("Script interrupted by user. Exiting.")
        sys.exit(1)
    finally:
        pass