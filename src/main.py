import argparse
import subprocess
import os
import yaml
from handlers import dhu_handler, hix_handler, hpa_handler, sga_handler
from logger.logger_config import logger

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(ROOT_DIR, "swen_tools_config.yaml")

def print_stylized_text():
    """Print the SWEN-TOOLS header."""
    command = "figlet -f slant SWEN-TOOLS | boxes -d unicornsay | lolcat -d 2"
    subprocess.run(command, shell=True)


def main():
    try:
        print_stylized_text()

        with open(config_path, "r") as file:
            configuration = yaml.safe_load(file)


        parser = argparse.ArgumentParser(description="SWEN-TOOLS")

        parser.add_argument(
            "--log-level",
            "-ll",
            default="INFO",
            choices=["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"],
            help="Set the logging level (default: INFO)",
        )

        # Add a subparser for task-specific options
        subparsers = parser.add_subparsers(
            dest="ecu", required=True, help="ECU:s to bootburn"
        )

        # Subparser for DHU
        dhuh_parser = subparsers.add_parser("DHUH", aliases= ["dhuh"], help="Bootburn DHUH")
        dhuh_parser.add_argument("--type", "-t", required=True, type=str,help="Choose type designation", choices=["polestar", "p", "volvo", "v"],)
        dhuh_parser.add_argument("--sw_path", type=str, help="Path to software (Optional)")

        dhum_parser = subparsers.add_parser("DHUM", aliases= ["dhum"], help="Bootburn DHUM")
        dhum_parser.add_argument("--type", "-t",required=True, type=str,help="Choose type designation", choices=["polestar", "p", "volvo", "v"],)
        dhum_parser.add_argument("--sw_path", type=str, help="Path to software (Optional)")
        dhum_parser.add_argument("--commit", "-c", type=bool, help="Commit DHUM, default: True")

        # Subparser for Task B
        hix_parser = subparsers.add_parser("HIX", aliases= ["hix"], help="Bootburn HIX")
        hix_parser.add_argument(
            "--node, -n",
            required=True,
            type=str,
            help="Choose specific node (hia, hib)",
            choices=["a", "b"],
        )

        subparsers.add_parser("HPA", help="Bootburn HPA")

        sga_parser = subparsers.add_parser("SGA", aliases=["sga"], help="Bootburn SGA")


        args = parser.parse_args()
        logger.setLevel(level= args.log_level)

        if args.ecu:
            args.ecu = args.ecu.upper()

        ecu: str = args.ecu

        dhu_script_filepath = configuration["handlers"]["dhu_handler"]["script_filepath"]
        type_designation = args.type

        if ecu == "DHUH":
            config_args = ""
            for arg in configuration["handlers"]["dhu_handler"]["arguments"]["dhuh"]:
                config_args += arg + " "

            yaml_data = configuration["handlers"]["dhu_handler"]["software"]["type_designation"]
            sw_filepath = yaml_data[type_designation]["dhuh_sw_filepath"]
            custom_sw_filepath = args.sw_path
            dhu_handler.flash_dhuh(
                script_path=dhu_script_filepath,
                args=config_args,
                software_filepath=custom_sw_filepath if custom_sw_filepath else sw_filepath,
                logger=logger
            )
        elif ecu == "DHUM":
            config_args = ""
            for arg in configuration["handlers"]["dhu_handler"]["arguments"]["dhum"]:
                config_args += arg + " "

            yaml_data = configuration["handlers"]["dhu_handler"]["software"]["type_designation"]
            sw_filepath = yaml_data[type_designation]["dhum_sw_filepath"]
            custom_sw_filepath = args.sw_path
            commit = args.commit
            print("COMMIT", commit)
            dhu_handler.flash_dhum(
                script_path=dhu_script_filepath,
                args=config_args,
                software_filepath=custom_sw_filepath if custom_sw_filepath else sw_filepath, 
                commit=commit if commit else True,
                logger=logger
            )        
        elif ecu == "HIX":
            pass
        elif ecu == "HPA":
            hpa_handler.flash_hpa(logger)
        elif ecu == "SGA":
            sga_handler.flash_sga(logger)

    except KeyboardInterrupt:
        logger.info("swen-tools interrupted by user.")
    except Exception as e:
        logger.error(f"Failed to bootburn {ecu}: ", e)


if __name__ == "__main__":
    main()
