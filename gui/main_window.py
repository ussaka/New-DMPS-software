"""
Provides graphical user interface for the program. Each class implements different part of the gui.
E.g. MenuBar implements functionality to all top menu related things
"""

import logging
import queue
import tkinter as tk
from multiprocessing import Lock
from tkinter import ttk

import config
import detectors
import flow_meters
import ni_daqs
from gui import maintenance_tab, menu_bar, measurement_tab, environment_tab
from threads import pid_ftp_thread, automatic_measurement


class MainWindow(tk.Tk):
    """
    Creates the main program window
    """

    def __init__(self, conf: config.Config, daq: ni_daqs.NiDaq, flow_meter: flow_meters.FlowMeter4000,
                 detector: detectors.CpcLegacy, blower_thread: pid_ftp_thread.BlowerPidThread,
                 automatic_measurement_thread: automatic_measurement.AutomaticMeasurementThread,
                 flow_meter_ftp_queue: queue.Queue, hv_voltage_queue: queue.Queue, conc_queue: queue.Queue,
                 daq_ai_queue: queue.Queue, rd_queue: queue.Queue, flow_meter_lock: Lock, daq_lock: Lock,
                 detector_lock: Lock) -> None:
        logging.info("Starting to create the main gui window")

        super().__init__()  # Call Tk class constructor

        # Configure main window
        self.title("DMPS")
        self.geometry("1024x768")
        # Disables tear-off menu bar items option
        self.option_add("*tearOff", tk.FALSE)
        # Make the main window resizable
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Create the main frame
        mainframe = ttk.Frame(self)  # Container for the all other contents of the UI
        mainframe.rowconfigure(0, weight=1)
        mainframe.columnconfigure(0, weight=1)
        # Grid command places the element and make's it visible
        mainframe.grid(row=0, column=0, sticky="wn")

        # Create menu bar
        menubar = menu_bar.MenuBar(mainframe, conf, flow_meter, daq, detector, blower_thread, flow_meter_lock, daq_lock,
                                   detector_lock)
        self.config(menu=menubar)  # Set main window's menubar
        logging.info("Menu bar created")

        # Container for the tabs
        notebook = ttk.Notebook(mainframe)

        # Maintenance tab
        maint_tab = maintenance_tab.MaintenanceTab(self, conf, flow_meter, daq, detector, blower_thread,
                                                   flow_meter_ftp_queue, daq_ai_queue, rd_queue, notebook,
                                                   flow_meter_lock,
                                                   daq_lock)
        logging.info("Maintenance tab created")

        # Measurement tab
        measure_tab = measurement_tab.MeasurementTab(self, conf, automatic_measurement_thread, hv_voltage_queue,
                                                     conc_queue)
        logging.info("Measurement tab created")

        # Environment tab
        env_tab = environment_tab.EnvironmentTab(self, daq, automatic_measurement_thread, daq_ai_queue, conf, daq_lock)
        logging.info("Environment tab created")

        # Add tabs to the notebook (container)
        notebook.add(maint_tab, text="Maintenance")
        notebook.add(measure_tab, text="Automatic measurement")
        notebook.add(env_tab, text="Environment")

        # Update notebook to show the tabs
        notebook.grid(row=0, column=0, padx=5, pady=5)

        logging.info("Finished creating the GUI")
