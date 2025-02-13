from colorama import Fore, Style, init
import sys, os

# Initialize colorama for Windows compatibility
init(autoreset=True)


class PlaybookNode:
    def __init__(self, name, parent=None, action=None, color=Fore.GREEN, box_style="shell"):
        self.name = name
        self.parent = parent
        self.action = action
        self.children = []
        self.color = color
        self.box_style = box_style

    def add_child(self, child_node):
        child_node.parent = self
        self.children.append(child_node)

    def display(self):
        """Display the node's breadcrumb with its customized color and box."""
        breadcrumb = self.path()  # Get the breadcrumb path
        colored_breadcrumb = self.color + breadcrumb + Style.RESET_ALL

        # Boxed display with breadcrumb
        box_cmd = f"echo \"{colored_breadcrumb}\" | boxes -d {self.box_style}"
        os.system(box_cmd)

    def path(self):
        """Return the path to the current node as a breadcrumb."""
        breadcrumb = [self.name]
        parent = self.parent
        while parent:
            breadcrumb.insert(0, parent.name)
            parent = parent.parent
        return " -> ".join(breadcrumb)


class Playbook:
    def __init__(self, root_node, box_style="shell", default_color=Fore.GREEN):
        self.root = root_node
        self.box_style = box_style
        self.default_color = default_color

    def display(self):
        """Display the root of the playbook with customized settings."""
        self.root.display()

    def change_box_style(self, new_box_style):
        """Change the box style for the entire playbook."""
        self.box_style = new_box_style

    def change_color(self, new_color):
        """Change the color for the entire playbook."""
        self.default_color = new_color
