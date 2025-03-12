import os
import subprocess

from logging import Logger
from logger.logger_config import super_message
from dotenv import load_dotenv

load_dotenv()

#DHUH_ARGS = "dhuh_update --uds-transport serial --artifacts-path "
#DHUM_ARGS = "moose_update --qdl --fw "
#SCRIPT_PATH = os.getenv("SCRIPT_PATH")

#DOCKER_ARGS = ["--multiuser"]
#DOCKER_IMAGE = os.getenv("DOCKER_IMAGE")



def start_docker_from_script(script_path: str, script_args: str, logger: Logger):
    """
    Start a Docker container using a shell script with live output.

    Args:
        script_path (str): The path to the shell script.
        script_args (list, optional): List of arguments to pass to the script.

    Returns:
        str: The ID of the started container if successful.
    """
    
    command = [script_path] + [script_args]
    
    logger.debug("Running command: " + " ".join(command))
    
    try:
        logger.debug("Starting Docker container...")
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        for line in process.stdout:
            logger.info(line.strip())

        process.wait()  # Wait for the process to finish
        if process.returncode != 0:
            logger.error(f"Error while starting Docker: {process.stderr.read()}")
            return None
        
        super_message("Done!")
        return process.returncode

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None


def flash_dhuh(script_path: str, args: str, software_filepath: str, logger: Logger):
    command = args + "--artifacts-path " + software_filepath.strip()
    return_code = start_docker_from_script(script_path, command, logger)
    print("Return code: ", return_code)

def flash_dhum(script_path: str, args: str, software_filepath: str, commit: bool, logger: Logger):
    command = args + "--fw " + software_filepath.strip()
    if commit:
        command += " --edge-node-ip 169.254.4.10"
    return_code = start_docker_from_script(script_path, command, logger)
    print("Return code: ", return_code)
