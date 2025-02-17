import logging
import subprocess
# Define a new log level for success
SUCCESS_LEVEL = 25  # You can use any number between 1-50
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


# Custom success logging function
def success(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL):
        self._log(SUCCESS_LEVEL, message, args, **kwargs)


# Add the success method to the logging module
logging.Logger.success = success


# Custom logging handler to apply color
class ColorizingStreamHandler(logging.StreamHandler):
    def emit(self, record):
        log_message = self.format(record)

        # ANSI escape code for green text (only for SUCCESS level)
        if record.levelname == "SUCCESS":
            log_message = f"\033[32m{log_message}\033[0m"  # Green for SUCCESS
        elif record.levelname == "ERROR":
            log_message = f"\033[31m{log_message}\033[0m"  # Red for ERROR
        elif record.levelname == "WARNING":
            log_message = f"\033[33m{log_message}\033[0m"  # Yellow for WARNING
        elif record.levelname == "INFO":
            # log_message = f"\033[34m{log_message}\033[0m"  # Blue for INFO
            pass
        # Apply other color formats here if needed (e.g., for INFO, ERROR)

        # Ensure output is correctly displayed
        try:
            self.stream.write(log_message + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


# Create a logger
logger = logging.getLogger("SWEN-TOOLS")
logger.setLevel(logging.DEBUG)  # Set the desired logging level

# Create a console handler with colorizing
console_handler = ColorizingStreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter("[%(asctime)s] - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(console_handler)

def super_message(message):
    command = f"figlet -f slant {message} | lolcat -d 2"
    subprocess.run(command, shell=True)