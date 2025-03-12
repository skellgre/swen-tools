import os
import sys
import time
import subprocess

import serial
from logging import Logger
from dotenv import load_dotenv

from utils.minicom import CharacterByCharacterSerialCommand, SerialCommandExecutor, search_correct_ttyUSB_port
from utils.progress_bar import ProgressBar
from exceptions.exceptions import FlashScriptError, PortNotFoundError, CommandFailedError
from logger.logger_config import super_message
from swut.cli.cli_handler import CliHandler


load_dotenv()
progress_bar = ProgressBar()

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
    process = None
    try:
        command = ["sudo", "-S", script_path, args]
        
       
        start_time = time.time()
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

        super_message("Flashing HPA")
        flashing_time = 3 * 60 + 5
        progress_bar.start(flashing_time)
        for line in iter(process.stdout.readline, ""):
            logger.debug(line.strip())

        for error_line in iter(process.stderr.readline, ""):
            logger.error(error_line.strip())

        process.wait()
        if process.returncode != 0:
            raise FlashScriptError("Flash script execution failed.")

        logger.debug("Flash script completed successfully.")
        end_time = time.time()
        progress_bar.stop()
        return end_time - start_time
    except Exception as e:
        logger.error(f"Flash script failed with error: {e}")
        progress_bar.stop(done=False)
        raise FlashScriptError("Flash script execution failed.") from e
    finally:
        if process and process.stdin:
            process.stdin.close()
        if process and process.stdout:
            process.stdout.close()
        if process and process.stderr:
            process.stderr.close()

def flash_hpa(logger: Logger):
    """Main procedure to automate the flashing process."""
    try:
        cli_handler = CliHandler(interactive_cli_mode=False)
        # exitcode, response = cli_handler.execute_cli_command(flash_local_files_try_1())
        strategy = CharacterByCharacterSerialCommand()
        executor = SerialCommandExecutor(strategy)
        port = search_correct_ttyUSB_port(7, executor, "GoForHIA>", 0.5, logger)

        with serial.Serial(port, **SERIAL_CONFIG) as ser:
            executor.execute(ser, b"tegrarecovery x1 on", b"Command Executed", 5, logger)
            executor.execute(ser, b"tegrareset x1", b"Command Executed", 5, logger)

            total_time = run_flash_script(HPA_FLASH_FILEPATH, FLASH_ARGS, logger)
            
            executor.execute(ser, b"tegrarecovery x1 off", b"Command Executed", 2, logger)
            executor.execute(ser, b"tegrareset x1", b"Command Executed", 2, logger)
 

        logger.debug("HPA bootburn completed successfully.")
        super_message("Done!")
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(total_time))
        logger.info(f"Total time: {formatted_time}")

    except PortNotFoundError:
        pass
    except CommandFailedError:
        pass
    except FlashScriptError:
        with serial.Serial(port, **SERIAL_CONFIG) as ser:
            executor.execute(ser, b"tegrarecovery x1 off", b"Command Executed", 2, logger)
            executor.execute(ser, b"tegrareset x1", b"Command Executed", 2, logger)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user. Exiting.")
        sys.exit(1)
    finally:
        pass