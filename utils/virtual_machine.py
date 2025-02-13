import subprocess
import time
import sys
 
class VirtualMachine:
    def __init__(self, vm_name, os_user, os_password, ip_address):
        self.name = vm_name
        self.os_user = os_user
        self.os_password = os_password
        self.ip_address = ip_address

    def start(self, timeout=20):
        """Start the VM using VirtualBox."""
        try:
            # Run the VBoxManage command to start the VM
            subprocess.run(["VBoxManage", "startvm", self.name, "--type", "headless"], check=True)
            time.sleep(timeout)  # Wait for VM to boot; adjust timing as needed
        except subprocess.CalledProcessError as e:
            # Check the error output for the locked session issue
            if "VBOX_E_INVALID_OBJECT_STATE" in str(e):
                print(f"Error: The machine '{self.name}' is already locked by another session. Exiting...")
            else:
                # Handle other subprocess errors
                print(f"Error starting VM '{self.name}': {e}")
        except Exception as e:
            # Handle any other unexpected errors
            print(f"An unexpected error occurred: {e}")

    def login(self):
        """Log in to the VM if it's Windows, using VBoxManage guest control."""
        print("Logging in to Windows...")
        try:
            
            subprocess.run([
                "VBoxManage", "guestcontrol", self.name, "run",
                "--exe", "cmd.exe",
                "--username", self.os_user,
                "--password", self.os_password,
                "--", "cmd.exe", "/c", "echo Logged in"
            ])
        except Exception as e:
            print(f"Something went wrong when logging in: {e}")


    def add_usb_filter(self, filter_name, usb_vendor_id, usb_product_id):
        """Add a USB filter by name, ensuring it does not already exist."""
        print(f"Checking if USB filter '{filter_name}' exists...")

        try:
            # Get VM info and split it into lines
            vm_info = subprocess.check_output(
                ["VBoxManage", "showvminfo", self.name], text=True
            ).splitlines()

            # Iterate over VM info to find USB filters
            for i, line in enumerate(vm_info):
                # Normalize spaces and check for the filter name
                line_clean = " ".join(line.split())
                if line_clean.startswith(f"Name: {filter_name}"):
                    
                    print(f"USB filter '{filter_name}' already exists. Skipping addition.")
                    return  # Exit the function early as the filter already exists

            # If no matching filter is found, add a new one
            print(f"Adding USB filter '{filter_name}'...")
            subprocess.run(
                [
                    "VBoxManage", "usbfilter", "add", "0",
                    "--target", self.name,
                    "--name", filter_name,
                    "--vendorid", usb_vendor_id,
                    "--productid", usb_product_id
                ],
                check=True
            )
            print(f"USB filter '{filter_name}' added successfully.")

        except subprocess.CalledProcessError as e:
            print(f"Error checking or adding USB filter: {e}")





    def remove_usb_filter(self, filter_name):
        """Remove a USB filter by name."""
        print(f"Removing USB filter '{filter_name}'...")
        
        try:
            # Retrieve VM info and search for USB filters
            vm_info = subprocess.check_output(["VBoxManage", "showvminfo", self.name], text=True)
            filters = vm_info.splitlines()
            
            # Find the filter index for the specified filter name
            filter_index = None
            for line in filters:
                if f"Name: {filter_name}" in line:
                    # Extract the index number from the preceding line or specific part of the line
                    filter_index = line.split()[0].split(":")[-1].strip()
                    break

            if filter_index is not None:
                # Run the remove command with the located index
                subprocess.run(["VBoxManage", "usbfilter", "remove", filter_index, "--target", self.name], check=True)
                print(f"USB filter '{filter_name}' removed.")
            else:
                print(f"USB filter '{filter_name}' not found in VM '{self.name}'.")
        
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")


    def ssh_command(self, command, quiet=False):
        """Execute a command on the VM over SSH."""
        try:
            if not quiet:
                print(f"Executing SSH command: {command}")
            result = subprocess.check_output([
                "sshpass", "-p", self.os_password, "ssh",
                f"{self.os_user}@{self.ip_address}", command
            ], text=True)
            if not quiet:
                print(f"Command output:\n{result}")
            return result
        except subprocess.CalledProcessError as e:
            print(f"Error executing SSH command: {e}")
            return None


    def _flash_ecu_vbox(self, ecu, autoit_exe_path="C:\\hix-auto-flash\\src\\Main.exe", flags=None):
        if flags is None:
            flags = []

        try:
            command = [
                "VBoxManage", "guestcontrol", self.name, "run",
                "--exe", autoit_exe_path,
                "--username", self.os_user,
                "--password", self.os_password,
                "--", "--ecu", f"{ecu}"
            ]

            for flag, value in flags:
                command.append(flag)
                if value is not None:
                    command.append(value)

            # Run the command and stream output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True       
            )

            for line in iter(process.stdout.readline, ''):
                print(line, end='')

            process.wait()

            exit_code = process.returncode
            for line in process.stderr:
                if "Exit code:" in line:
                    try:
                        exit_code = int(line.strip().split(":")[1].strip())
                    except (ValueError, IndexError):
                        print(f"Warning: Unable to parse exit code from line: {line}")

            return exit_code if exit_code is not None else -1

        except Exception as e:
            print(f"Error during {ecu} flashing process: {e}")
            return -1
        

    def flash_hia_vbox(self, flags=None):
        """
        Run the HIA flashing process via VBoxManage guestcontrol with optional flags.

        :param flags: A list of flags to pass to the executable.
        """
        print("Starting HIA flashing process...")
        return self._flash_ecu_vbox(ecu="hia", flags=flags)


    def flash_hib_vbox(self, flags=None):
        """
        Run the HIB flashing process via VBoxManage guestcontrol with optional flags.

        :param flags: A list of flags to pass to the executable.
        """
        print("Starting HIA flashing process...")
        return self._flash_ecu_vbox(ecu="hib", flags=flags)


    
    def get_latest_log(self):
        """Retrieve the latest log file from a given log directory on the VM over SSH."""
        log_dir_path = r"C:\hix-auto-flash\src\logs"  # Use raw string for Windows paths

        # Command to list files sorted by last modified date
        log_files_output = self.ssh_command(f"cmd /c \"dir {log_dir_path}\\*.txt /b /o-d\"", quiet=True)
        if not log_files_output or "File Not Found" in log_files_output:
            print(f"No log files found in '{log_dir_path}' on VM.")
            return None

        log_files = log_files_output.strip().splitlines()
        if not log_files:
            print(f"No log files found in '{log_dir_path}' on VM.")
            return None

        # The first file in the sorted list is the latest
        latest_log_file = log_files[0]

        # Read the contents of the latest log file
        log_content = self.ssh_command(f"cmd /c \"type {log_dir_path}\\{latest_log_file}\"", quiet=True)
        if log_content:
            print(f"Latest log from '{log_dir_path}' on VM:\n{log_content}")
        else:
            print(f"Could not read log file '{latest_log_file}' from '{log_dir_path}'.")
        return log_content

    def poweroff(self):
        """Power off the VM."""
        print(f"Powering off VM '{self.name}'...")
        subprocess.run(["VBoxManage", "controlvm", self.name, "poweroff", "--type", "headless"])


    def is_vm_running(self):
        """Check if the VM is already running."""
        try:
            # Query the VM's information
            result = subprocess.run(
                ["VBoxManage", "showvminfo", self.name, "--machinereadable"],
                capture_output=True, text=True, check=True
            )
            # Parse the state from the output
            for line in result.stdout.splitlines():
                if line.startswith("VMState="):
                    vm_state = line.split("=")[1].strip('"')
                    return vm_state == "running"
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error checking VM state: {e}")
            return False
