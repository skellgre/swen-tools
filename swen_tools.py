import argparse
from utils.playbook import Playbook, PlaybookNode
import os
from colorama import Fore, Style


def display_banner():
    try:
        banner_cmd = "figlet -f slant SWEN-TOOLS | boxes -d unicornthink | lolcat -a -d 1"
        os.system(banner_cmd)
    except Exception as e:
        print(Fore.RED + f"Error displaying banner: {e}" + Style.RESET_ALL)

def interactive_mode():
    """Runs the interactive mode of SWEN-TOOLS."""
    try:
        display_banner()
        print(Fore.GREEN + "Welcome to SWEN-TOOLS interactive mode!" + Style.RESET_ALL)

        def test_action():
            print("This is a test action")

        # Create a playbook tree with customizable colors and box styles
        root = PlaybookNode("Main Menu")
        option_a = PlaybookNode("Option A")
        option_b = PlaybookNode("Option B")
        option_c = PlaybookNode("Option C")

        sub_b1 = PlaybookNode("Sub Option B1")
        sub_b2 = PlaybookNode("Sub Option B2", action=test_action)
        option_b.add_child(sub_b1)
        option_b.add_child(sub_b2)

        root.add_child(option_a)
        root.add_child(option_b)
        root.add_child(option_c)

        playbook = Playbook(root)
        current_node = playbook.root
        clear_text_at_start = False

        while True:
            if clear_text_at_start:
                os.system("cls" if os.name == "nt" else "clear")

            # Display the breadcrumb as a box
            current_node.display()

            # Display child options
            if current_node.children:
                print(Fore.YELLOW + "\nOptions:" + Style.RESET_ALL)
                for idx, child in enumerate(current_node.children, start=1):
                    print(f"{Fore.CYAN}[{idx}] {child.name}{Style.RESET_ALL}")
            else:
                print(Fore.RED + "\nNo further options available." + Style.RESET_ALL)

            # Get user input
            choice = input(Fore.YELLOW + "\nChoose an option (or type 'back', 'quit'): " + Style.RESET_ALL).strip().lower()

            if choice == "quit":
                print(Fore.GREEN + "Exiting SWEN-TOOLS. Goodbye!" + Style.RESET_ALL)
                break
            elif choice == "back":
                if current_node.parent:
                    current_node = current_node.parent
                else:
                    print(Fore.RED + "You are already at the main menu." + Style.RESET_ALL)
            elif choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(current_node.children):
                    current_node = current_node.children[index]
                else:
                    print(Fore.RED + "Invalid choice. Please select a valid option." + Style.RESET_ALL)
            else:
                print(Fore.RED + "Please enter a valid number or command." + Style.RESET_ALL)
            clear_text_at_start = True
    except KeyboardInterrupt:
        print(Fore.RED + "\nExiting SWEN-TOOLS due to keyboard interruption. Goodbye!" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"An unexpected error occurred: {e}" + Style.RESET_ALL)
    finally:
        print(Fore.GREEN + "Thank you for using SWEN-TOOLS!" + Style.RESET_ALL)


def main():
    parser = argparse.ArgumentParser(description="SWEN-TOOLS Command-Line Interface")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run SWEN-TOOLS in interactive mode")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    else:
        print(Fore.YELLOW + "SWEN-TOOLS is running in non-interactive mode. No actions defined yet." + Style.RESET_ALL)


if __name__ == "__main__":
    main()
