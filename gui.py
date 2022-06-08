# TODO: Menu bar add content and functionality
# TODO: Implement do_nothing method
# TODO: Figure how to resize mainframe with the window size

# Reason for doing imports this way is that several classes are defined in both modules
# E.g. tk.Button() vs tkk.Button()
import tkinter as tk
from tkinter import ttk


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()  # Inherit Tk class

        # Configure main window
        self.title("DMPS GUI")
        self.geometry("720x550")
        # Disables tear-off menu bar items option
        self.option_add("*tearOff", tk.FALSE)

        # Main frame
        self.mainframe = ttk.Frame(self)  # Conteiner for widgets of the UI
        self.mainframe.grid()

        # Create menu bar
        self.top_menu()

        # Tabs
        self.notebook = ttk.Notebook(self.mainframe)  # Container for tabs

        self.maintenance_tab = MaintenanceTab(
            self.notebook)  # Create maintenance object
        self.notebook.add(self.maintenance_tab, text="Maintenance")

        self.notebook.grid(row=0, column=0, padx=5, pady=5)

    def top_menu(self) -> None:
        menubar = tk.Menu(self)  # Create menubar
        self.config(menu=menubar)  # Set main window menubar

        # File
        menu_file = tk.Menu(menubar)
        menubar.add_cascade(menu=menu_file, label="File")
        menu_file.add_command(label="New", command=self.do_nothing)

    def do_nothing(self) -> None:
        print("Hello there")


class MaintenanceTab(ttk.Frame):
    def __init__(self, container) -> None:
        super().__init__(container)  # Inherit Frame class


# This code is for testing purposes only and
# is only executed if this module is run as main
if __name__ == "__main__":
    app = MainWindow()  # Create gui object
    app.mainloop()  # Start TKinter loop for the gui
