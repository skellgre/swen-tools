import argparse
import sys
import time
from utils.virtual_machine import VirtualMachine

# Configuration
vm_name = "windows10"
user = "itahil"
password = "ita-hil123"
ip = "192.168.56.101"
flash_script_path = "/path/to/flash_script.sh"



# USB device details
usb_vendor_id = "058B"  # Vendor ID for Miniwiggler
usb_product_id = "0043"  # Product ID for Miniwiggler
usb_filter_name = "Miniwiggler"  # Name for the USB filter


def main():
    parser = argparse.ArgumentParser(
        description="Flash HIA and HIB using VirtualBox."
    )
    
    # Add short options for arguments
    parser.add_argument("-u", "--username", type=str, required=True, help="VM OS username.")
    parser.add_argument("-pw", "--password", type=str, required=True, help="VM OS password.")
    parser.add_argument("-vm", "--vm-name", type=str, default=vm_name, help="Name of the VirtualBox VM.")
    parser.add_argument("-ip", "--ip", type=str, default=ip, help="IP address of the VirtualBox VM.")

    parser.add_argument("-e", "--ecu", required=True, choices=["hia", "hib"], help="Specify the ECU to flash ('hia' or 'hib').")
    parser.add_argument("--environment", "--env", type=str, help="Specify a filepath for a custom environment JSON file.")
    parser.add_argument("-r", "--retries", type=int, default=3, help="Number of retries if flashing fails (default: 3).")
    parser.add_argument("-rd", "--retry-delay", type=int, default=5, help="Delay between retries in seconds (default: 5).")
    parser.add_argument("-sv", "--skip-verification", action="store_true", help="Skips the verification process after flashing.")
    parser.add_argument("--ucb", action="store_true", help="Enable UCB mode.")
    
    
    

    args = parser.parse_args()

    # Initialize VM instance
    vm = VirtualMachine(
        vm_name=args.vm_name,
        os_user=args.username,
        os_password=args.password,
        ip_address=args.ip
    )

    # Prepare flags for the AutoIt script
    autoit_flags = []

    if args.ucb:
        autoit_flags.append(("--ucb", None))
    elif args.skip_verification:
        autoit_flags.append(("--skip_verification", None))
    elif args.environment:
        autoit_flags.append(args.environment)

    # Retry logic
    for attempt in range(1, args.retries + 1):
        try:
            print(f"Starting ECU flashing process (attempt {attempt}/{args.retries})...")
            
            vm.add_usb_filter(usb_filter_name, usb_vendor_id, usb_product_id)

            # Start the VM
            vm.start()
            vm.login()

            # Flash the ECU
            result = vm.flash_hia_vbox(flags=autoit_flags) if args.ecu == "hia" else vm.flash_hib_vbox(flags=autoit_flags)
            if result == 0:
                print(f"{args.ecu} flashing successful.")
                break
            elif result == 1:
                print(f"Error during {args.ecu} flashing. AutoIt exit code: {result}. Check logs for specific error.")
            elif result == 2:
                print(f"Initialization failed. AutoIt exit code: {result}. Check logs for specific error.")
            else:
                print(f"Unexpected exit code {result}.")

        except Exception as e:
            print(f"Error during flashing process: {e}")
            if attempt < args.retries:
                print(f"Retrying in {args.retry_delay} seconds...")
                time.sleep(args.retry_delay)
            else:
                print("All retries failed. Exiting.")
                sys.exit(1)
        finally:
            vm.poweroff()
            print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted. Exiting.")
        sys.exit(0)
