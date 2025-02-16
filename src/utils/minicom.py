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
    ) -> str:
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
        start_time = time.time()
        ser.write(command + b"\r")
        ser.flush()
        logger.debug(f"Executed command over serial: '{command}'")

        response = b""

        while time.time() - start_time < timeout:
           # data = ser.read(ser.in_waiting or 1)  # Read available bytes (or 1 byte)
            data = ser.read_all()
            if data:
                response += data
                decoded_response = response.decode("utf-8", errors="replace").strip()

                if expected_response in response:
                    logger.debug(f"Expected response received after command: {decoded_response}")
                    return decoded_response

            time.sleep(0.05)  # Short delay to prevent CPU overuse

        logger.debug(f"Timeout reached! Expected: {expected_response.decode()}, Received: {response.decode('utf-8', errors='replace').strip()}")
        return response.decode("utf-8", errors="replace").strip()


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
        ser.timeout = timeout
        time.sleep(0.1)

        logger.debug(f"Executing command char-by-char: '{command}'")
        for c in command:
            ser.write(bytes([c]))  # Send one character at a time
            time.sleep(0.1)

        ser.write(b"\r")
        ser.flush()

        time.sleep(1)
        response = ser.read_all().decode("utf-8", errors="replace").strip()

        if expected_response not in response:
            logger.debug(f"Unexpected response. Expected: {expected_response}, Actual: {response}")
        else:
            logger.info(f"Command executed successfully: {expected_response}")

        return response


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
        
        received_data = serial_executor.execute(ser=ser, command= b"", expected_response=bytes(prompt, "utf-8"), timeout=timeout, logger=logger)

        if prompt in received_data:
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
    raise PortNotFoundError("No active port found.")

def serial_command(
    ser: serial.Serial, cmd, logger: Logger, expected_response=b"\r", timeout=5
):
    assert ser.is_open
    try:
        current_timeout = timeout
        ser.timeout = timeout
        time.sleep(0.1)
        ser.write(cmd + b"\r")
        ser.flush()
        logger.debug(f"Executed command over serial: '{cmd}'")
        actual_response = (
            ser.read(ser.in_waiting or 1024).decode("utf-8", errors="replace").strip()
        )
        if expected_response != actual_response:
            logger.warning(
                f"Failed to get expected response. Exepected:{expected_response}. Actual:{actual_response}"
            )
        else:
            logger.success(
                f"Got expected reponse from executing command: {expected_response}"
            )

        ser.timeout = current_timeout
        return ser
    except serial.SerialException as e:
        raise CommandFailedError(f"Failed to execute serial command: {e}")

def filter_terminal_output(input: str, filter: str = ""):
    if input is None:
        return None

    filtered_lines = []
    lines = input.splitlines()
    for line in lines:

        if not line.strip():
            continue
        if filter and filter in line.strip():
            continue

        filtered_lines.append(line)
    if len(filtered_lines) == 0:
        return None
    return "\n".join(filtered_lines)

def find_active_ttyUSB_port(
    prompt, max_ports, logger: Logger, enter_checks: int = 3
) -> int:
    """Find the first active port that responds with the given prompt."""

    if isinstance(prompt, str):
        prompt = [prompt]  # Convert single string to a list

    for port_num in range(max_ports):
        port = f"/dev/ttyUSB{port_num}"
        logger.info(f"Trying port: {port}")

        try:
            with serial.Serial(port, **SERIAL_CONFIG) as ser:
                for _ in range(enter_checks):  # Check multiple times per port
                    ser.write(b"\r\r\r")  # Send enter multiple times
                    time.sleep(1)

                    output = ser.read_all().decode("utf-8", errors="replace")
                    logger.debug(f"Received: {output}")

                    if any(
                        p in output for p in prompt
                    ):  # Check if output contains any prompt
                        logger.success(f"Found active port: {port}")
                        return port_num  # Return the correct port number

        except serial.SerialException as e:
            logger.warning(f"Port {port} is not available: {e}")

        time.sleep(0.1)

    raise PortNotFoundError("No active port found.")

def execute_commands_on_ttyUSB_port(
    port_num, commands: list[str], expected_response, error_response, logger: Logger
):
    """
    Execute a list of commands on the given serial port and capture output.

    Args:
        port_num (int): The serial port (e.g., /dev/ttyUSB0).
        commands (list): A list of string commands to send.
        wait_response (int): Time to wait for the device to respond.

    Returns:
        dict: A dictionary with commands as keys and their output as values.
    """

    port = f"/dev/ttyUSB{port_num}"
    logger.info(f"Connecting to {port} for command execution.")
    results = {}

    try:
        with serial.Serial(port, **SERIAL_CONFIG) as ser:

            for cmd in commands:
                logger.info(f"Executing command: {cmd}...")

                # Need to write every command by one character to the buffer
                for c in cmd:
                    ser.write(f"{c}".encode())
                    time.sleep(0.1)

                ser.write(b"\r")
                time.sleep(1)
                output = ser.read_all().decode("utf-8", errors="replace")
                filtered_output = filter_terminal_output(output, "")
                print("output: ", output)
                if (
                    filtered_output in error_response
                    or not expected_response in filtered_output
                ):
                    results[cmd] = filtered_output
                    logger.error(f"Executing command failed: {filtered_output}")
                    ser.close()
                    raise CommandFailedError(output)
                elif expected_response in output:
                    results[cmd] = filtered_output
                    logger.success("Command executed successfully.")

                ser.reset_input_buffer()

            ser.close()

    except serial.SerialException as e:
        logger.error(f"Error communicating with port {port_num}: {e}")
        ser.close()
        raise
    return results
