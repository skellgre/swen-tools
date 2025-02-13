import sys
import os
import argparse
import subprocess
from dotenv import load_dotenv

load_dotenv()

DHUM_COMMAND = os.getenv("DHUM_COMMAND")
DHUH_COMMAND = os.getenv("DHUH_COMMAND")
SOFTWARE_PATH = os.getenv("SOFTWARE_PATH")
DHU_VERSION = os.getenv("DHU_VERSION")
SCRIPT_PATH = os.getenv("SCRIPT_PATH")

DOCKER_ARGS = ["--multiuser"]
DOCKER_IMAGE = os.getenv("DOCKER_IMAGE")

import subprocess

def start_docker_with_script(script_path, script_args=None):
    """
    Start a Docker container using a shell script with live output.

    Args:
        script_path (str): The path to the shell script.
        script_args (list, optional): List of arguments to pass to the script.

    Returns:
        str: The ID of the started container if successful.
    """
    if script_args is None:
        script_args = []

    command = [script_path] + DOCKER_ARGS + [script_args]
    print("Command to run:", command)
    
    try:
        print("Starting Docker container...")
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        for line in process.stdout:
            print(line.strip())

        process.wait()  # Wait for the process to finish
        if process.returncode != 0:
            print(f"Error while starting Docker: {process.stderr.read()}")
            return None
        
        return process.returncode

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def flash_dhuh(type_designation: str):
    DHUH_COMMAND = "dhuh_update --uds-transport serial --artifacts-path "

    return_code = start_docker_with_script(SCRIPT_PATH, DHUH_COMMAND)
    print("Return code: ", return_code)

def flash_dhum():
    pass

def main():

    try:
        parser = argparse.ArgumentParser(description="Moose DHU Tool")
        parser.add_argument("--ecu", "-e", type=str, required=True, help="Specify the ECU to process", choices=["m", "dhum", "h", "dhuh"])
        parser.add_argument("--type", "-t", type=str, required=True, help="Type designation", choices=["p", "polestar", "v", "volvo"])
        args = parser.parse_args()

        ecu = args.ecu
        command = ""
        binaries = ""

        if ecu in ["m", "dhum"]:
            command = DHUM_COMMAND
            binaries = "FW.zip"
        elif ecu in ["h", "dhuh"]:
            command = DHUH_COMMAND
            binaries = "artifacts.zip"
        
        type_designation = args.type
        if type_designation in ["p", "polestar"]:
            type_designation = "polestar"
            command += f"{SOFTWARE_PATH}{type_designation}{DHU_VERSION}{binaries}"
        elif type_designation in ["v", "volvo"]:
            type_designation = "volvo"
            command += f"{SOFTWARE_PATH}{type_designation}{DHU_VERSION}{binaries}"

        #print(f"{SCRIPT_PATH} {DOCKER_ARGS[0]} {command}")
        return_code = start_docker_with_script(SCRIPT_PATH, command)
        print("Return code: ", return_code)

    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("Script interrupted by user. Exiting.")
        subprocess.run("docker kill $(docker ps -q)")
        sys.exit(1)

    finally:
       # subprocess.run("docker kill $(docker ps -q)")
       pass

if __name__ == "__main__":
    main()
