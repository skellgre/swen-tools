import serial
import time
from exceptions.exceptions import (
    CommandFailedError,
    FlashScriptError,
    PortNotFoundError,
)
from logging import Logger
from abc import ABC, abstractmethod

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


class SerialCommandStrategy(ABC):
    """Abstract base class for different serial command execution strategies."""

    @abstractmethod
    def execute(
        self,
        ser: serial.Serial,
        command: bytes,
        expected_response: bytes,
        timeout: int,
        logger: Logger,
    ) -> tuple[bool, str]:
        pass


class BasicSerialCommand(SerialCommandStrategy):
    """Simple serial command execution strategy."""

    def execute(
        self,
        ser: serial.Serial,
        command: bytes,
        expected_response: bytes,
        timeout: int,
        logger: Logger,
    ):
        assert ser.is_open
     
        ser.write(command + b"\r")
        ser.flush()
        logger.debug(f"Executed command over serial: '{command}'")

        response = b""
        
        start_time = time.time()
        while time.time() - start_time < timeout:
           # data = ser.read(ser.in_waiting or 1)  # Read available bytes (or 1 byte)
            data = ser.read_all()
            if data:
                response += data
                decoded_response = response.decode("utf-8", errors="replace").strip()
                logger.debug(decoded_response)
                if expected_response in response:
                    logger.debug(f"Expected response received after command: {decoded_response}")
                    return True, decoded_response

            time.sleep(0.1)  # Short delay to prevent CPU overuse

        logger.debug(f"Timeout reached! Expected: {expected_response.decode()}, Received: {response.decode('utf-8', errors='replace').strip()}")
        return False, response.decode("utf-8", errors="replace").strip()


class CharacterByCharacterSerialCommand(SerialCommandStrategy):
    """Executes a command character by character with a delay."""

    def execute(
        self,
        ser: serial.Serial,
        command: bytes,
        expected_response: bytes,
        timeout: int,
        logger: Logger,
    ):
        assert ser.is_open

        for c in command:
            ser.write(bytes([c]))  # Send one character at a time
            time.sleep(0.1)

        ser.write(b"\r")
        ser.flush()
        logger.debug(f"Executed command over serial: '{command}'")

        response = b""

        start_time = time.time()
        while time.time() - start_time < timeout:
           # data = ser.read(ser.in_waiting or 1)  # Read available bytes (or 1 byte)
            data = ser.read_all()
            if data:
                response += data
                decoded_response = response.decode("utf-8", errors="replace").strip()

                if expected_response in response:
                    logger.debug(f"Expected response received after command: {decoded_response}")
                    return True, decoded_response

            time.sleep(0.05)  # Short delay to prevent CPU overuse

        logger.debug(f"Timeout reached! Expected: {expected_response.decode()}, Received: {response.decode('utf-8', errors='replace').strip()}")
        return False, response.decode("utf-8", errors="replace").strip()


class SerialCommandExecutor:
    """Executes serial commands using a given strategy."""

    def __init__(self, strategy: SerialCommandStrategy):
        self.strategy = strategy

    def execute(
        self,
        ser: serial.Serial,
        command: bytes ,
        expected_response: bytes,
        timeout: int,
        logger: Logger,
    ):
        return self.strategy.execute(ser, command, expected_response, timeout, logger)

def __check_ttyUSB_port(ser: serial.Serial, serial_executor: SerialCommandExecutor, prompt: str, timeout: int, logger: Logger):
    try:
        
        success, received_data = serial_executor.execute(ser=ser, command= b"", expected_response=bytes(prompt, "utf-8"), timeout=timeout, logger=logger)

        if success:
            logger.debug(f"Prompt found: {received_data}")
            return True
        else:
            return False

    except serial.SerialException as e:
        logger.error(f"Something unexpected happened while finding port: {e}")
        return False



def search_correct_ttyUSB_port(num_of_ports: int, serial_executor: SerialCommandExecutor, prompts: str | list[str], timeout: int, logger: Logger):

    if isinstance(prompts, str):
        prompts = [prompts]


    for port_num in range(num_of_ports):
        port = f"/dev/ttyUSB{port_num}"
        logger.info(f"Trying port: {port}")
        for prompt in prompts:
            try:
                with serial.Serial(port, **SERIAL_CONFIG) as ser:
                    if __check_ttyUSB_port(ser, serial_executor, prompt, timeout, logger):
                        logger.success(f"Found active port: {port_num}")
                        return port
            except serial.SerialException as e:
                message = f"Something went wrong when trying searching correct ttyUSB port: {e} "
                logger.warning(message)
                raise serial.SerialException(message)
            finally:
                ser.close()
    message = "No active port found."
    logger.warning(message)
    raise PortNotFoundError(message)