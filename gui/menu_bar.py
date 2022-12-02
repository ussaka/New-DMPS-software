"""
Provides menu bar for the main window
"""

import logging
import tkinter as tk
from multiprocessing import Lock
from tkinter import ttk

import config
import detectors
import flow_meters
import ni_daqs
from gui.general_functions import create_labels, create_entries, save_entries
from threads import pid_ftp_thread


class MenuBar(tk.Menu):
    """
    Top menu (menu bar) for the program
    """

    def __init__(self, container: ttk.Frame, conf: config.Config, flow_meter: flow_meters.FlowMeter4000,
                 daq: ni_daqs.NiDaq, detector: detectors.CpcLegacy, blower_pid_thread: pid_ftp_thread,
                 flow_meter_lock: Lock, daq_lock: Lock, detector_lock: Lock) -> None:
        super().__init__(container)  # Call tk.Menu constructor

        # Initialize
        self.__container = container
        self.__conf = conf
        self.__flow_meter = flow_meter
        self.__daq = daq
        self.__detector = detector
        self.__blower_pid_thread = blower_pid_thread
        self.__flow_meter_lock = flow_meter_lock
        self.__daq_lock = daq_lock
        self.__detector_lock = detector_lock

        self.__flow_meter_conf = self.__conf.get_configuration("Flow_Meter")
        self.__flow_meter_scaling_conf = self.__conf.get_configuration("Flow_Meter_Scaling")
        self.__cpc_conf = self.__conf.get_configuration("Cpc")
        self.__daq_conf = self.__conf.get_configuration("NI_DAQ")

        # Settings
        settings_menu = tk.Menu(self)
        # Add settings label
        self.add_cascade(menu=settings_menu, label="Settings")

        # Add flow meter submenu
        settings_menu.add_command(label="Flow Meter", command=self.__flow_meter_window)
        # Add cpc submenu
        settings_menu.add_command(label="Cpc", command=self.__cpc_window)
        # Add daq submenu
        settings_menu.add_command(label="Daq", command=self.__daq_window)

    def __create_ser_window(self, title: str, geometry: str, conf: dict) -> (tk.Toplevel, dict):
        """
        Creates a new serial port settings window
        """

        # Create the window and configure it
        window = tk.Toplevel(self.__container)
        window.title(title)
        window.geometry(geometry)
        # Make the window resizable
        window.columnconfigure(0, weight=1)

        # Create the entry fields
        labels = ["Port:", "Baud rate:", "Byte size:", "Parity:", "Stopbits:", "Time out:", "SW flow control:",
                  "HW flow control:"]

        create_labels(window, labels, 0, 0, "w", 1)
        entries = create_entries(window, conf, 0, 0, "e", 1)

        return window, entries

    def __flow_meter_window(self) -> None:
        """
        Popup window with flow meter serial port settings
        """

        logging.info("Opened flow meter settings window")

        window, entries = self.__create_ser_window("Flow meter", "230x280", self.__flow_meter_conf)

        # Create save button
        save_button = ttk.Button(window, text="Save", command=lambda: self.__flow_meter_save_click(window, entries))
        save_button.grid(sticky="we", padx=50, pady=5)

    def __flow_meter_save_click(self, window: tk.Toplevel, entries: dict) -> None:
        """
        Save button click event. Update flow meter configuration with the new values.
        Saves configuration changes to the ini file.
        """

        self.__flow_meter_lock.acquire()  # PID can't be updated while ser settings are changed
        save_entries(entries, self.__conf, "Flow_Meter:Serial_port")  # Save to the ini file
        self.__conf.update_configuration(self.__flow_meter_conf, "Flow_Meter:Serial_port")  # Update the conf dict
        self.__flow_meter.update_settings()  # Update flow meter serial settings
        self.__flow_meter_lock.release()

        window.destroy()  # Close the settings window

    def __cpc_window(self) -> None:
        """
        Popup window with Cpc's serial port settings
        """

        logging.info("Opened cpc settings window")

        window, entries = self.__create_ser_window("Cpc", "230x280", self.__cpc_conf)

        # Create save button
        save_button = ttk.Button(window, text="Save", command=lambda: self.__cpc_save_click(window, entries))
        save_button.grid(sticky="we", padx=50, pady=5)

    def __cpc_save_click(self, window: tk.Toplevel, entries: dict) -> None:
        """
        Save button click event. Update cpc configuration with the new values.
        Saves configuration changes to the ini file.
        """

        save_entries(entries, self.__conf, "Cpc:Serial_port")  # Save to the ini file
        self.__detector_lock.acquire()
        self.__conf.update_configuration(self.__cpc_conf, "Cpc:Serial_port")  # Update the conf dict
        self.__detector.update_settings()  # Update cpc serial settings
        self.__detector_lock.release()
        window.destroy()  # Close the settings window

    def __daq_window(self) -> None:
        """
        Popup window with daq settings
        """

        logging.info("Opened daq settings window")

        # Create the window and configure it
        window = tk.Toplevel(self.__container)
        window.title("Daq")
        window.geometry("230x360")
        # Make the window resizable
        window.columnconfigure(0, weight=1)

        # Create the entry fields
        labels = ["Device id:", "AI min channel:", "AI max channel:", "AI min voltage:", "AI max voltage:",
                  "Blower pulse channel:", "Cpc counter channel:", "Cpc signal channel", "Port channel:",
                  "Total concentration valve line:", "Sample flow bypass valve line:"]

        create_labels(window, labels, 0, 0, "w", 1)
        entries = create_entries(window, self.__daq_conf, 0, 0, "e", 1)

        # Create save button
        save_button = ttk.Button(window, text="Save", command=lambda: self.__daq_save_click(window, entries))
        save_button.grid(sticky="we", padx=50, pady=5)

    def __daq_save_click(self, window: tk.Toplevel, entries: dict) -> None:
        """
        Save button click event. Update daq configuration with the new values.
        Saves configuration changes to the ini file.
        """

        self.__daq_lock.acquire()

        save_entries(entries, self.__conf, "NI_DAQ")  # Save to the ini file
        self.__conf.update_configuration(self.__daq_conf, "NI_DAQ")  # Update the conf dict
        self.__daq.update_settings()  # Update daq with the new values

        self.__daq_lock.release()

        window.destroy()  # Close the settings window
