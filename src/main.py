import argparse
import subprocess
import sys
from handlers import dhu_handler, hix_handler, hpa_handler, sga_handler
from utils.playbook import Playbook, PlaybookNode
from logger.logger_config import logger
def print_stylized_text():
    """Print the SWEN-TOOLS header."""
    command = "figlet -f slant SWEN-TOOLS | boxes -d unicornsay | lolcat -d 2"
    subprocess.run(command, shell=True)



def main():
    try:
        print_stylized_text()
        parser = argparse.ArgumentParser(description="SWEN-TOOLS")
        # Add a subparser for task-specific options
        subparsers = parser.add_subparsers(dest="ecu", required=True, help="ECU:s to bootburn")

        # Subparser for DHU
        dhu_parser = subparsers.add_parser("DHU", help="Bootburn DHU")
        dhu_parser.add_argument("--node, -n", required=True, type=str, help="Choose specific node (dhuh, dhum)", choices=["h", "m"])
        dhu_parser.add_argument("--type, -t", required=True, type=str, help="Choose type designation", choices=["polestar", "p", "volvo", "v"])

        # Subparser for Task B
        hix_parser = subparsers.add_parser("HIX", help="Bootburn HIX")
        hix_parser.add_argument("--node, -n", required=True, type=str, help="Choose specific node (hia, hib)", choices=["a", "b"])

        subparsers.add_parser("HPA", help="Bootburn HPA")

        sga_parser = subparsers.add_parser("SGA", aliases = ["sga"], help="Bootburn SGA")
        args = parser.parse_args()

        if args.ecu:
            args.ecu = args.ecu.upper()

        ecu: str = args.ecu



        if ecu == "DHU":
            dhu_handler.flash_dhuh()
        elif ecu == "HIX":
            pass
        elif ecu == "HPA":
            hpa_handler.bootburn_hpa(logger)
        elif ecu == "SGA":
            sga_handler.flash_sga(logger=logger)


    except Exception as e:
        print(f"Failed to bootburn {ecu}: ", e)

if __name__ == "__main__":
    main()
