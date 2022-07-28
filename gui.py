# This file provides graphical user interface for the program
# Each class implement different part of the gui
# E.g. MenuBar implements functionality to all top menu related things

# Reason for doing imports this way is that several classes are defined in both modules
# E.g. tk.Button() vs tkk.Button()
import tkinter as tk
from tkinter import ttk, messagebox

import logging

from matplotlib import markers
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import numpy as np


class MainWindow(tk.Tk):
    """Creates main program window"""

    # TODO: Improve type hints
    def __init__(self, ini_updater: object, daq: object, flow_meter: object, detector: object, blower_pid_thread, automatic_measurement_thread, flow_meter_queue: object, voltage_queue: object, conc_queue: object, lock) -> None:
        logging.info("Starting to create GUI")

        super().__init__()  # Inherit Tk class

        # Configure main window
        self.title("DMPS")
        self.geometry("800x600")
        # Disables tear-off menu bar items option
        self.option_add("*tearOff", tk.FALSE)
        # Make the main window resizable
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Create main frame
        # Container for the all other contents of the UI
        mainframe = ttk.Frame(self)
        mainframe.rowconfigure(0, weight=1)
        mainframe.columnconfigure(0, weight=1)
        # Grid command places the element and make's it visible
        mainframe.grid(row=0, column=0, sticky="wn")

        # Create menu bar
        menubar = MenuBar(mainframe, ini_updater,
                          flow_meter, daq, detector, blower_pid_thread, lock)
        self.config(menu=menubar)  # Set main window's menubar
        logging.info("Menu bar created")

        # Container for the tabs
        notebook = ttk.Notebook(mainframe)

        # Create tabs
        maintenance_tab = MaintenanceTab(
            self, ini_updater, flow_meter, daq, detector, blower_pid_thread, flow_meter_queue, notebook)
        logging.info("Maintenance tab created")
        measurement_tab = MeasurementTab(
            self, automatic_measurement_thread, voltage_queue, conc_queue)
        logging.info("Measurement tab created")

        # Add tabs to the notebook (container)
        notebook.add(maintenance_tab, text="Maintenance")
        notebook.add(measurement_tab, text="Automatic measurement")

        # Update notebook to show the tabs
        notebook.grid(row=0, column=0, padx=5, pady=5)

        logging.info("Finished creating the GUI")


class MenuBar(tk.Menu):
    """Top menu (menubar) for the program"""

    # TODO: Improve type hints
    def __init__(self, container: ttk.Frame, ini_updater: object, flow_meter: object, daq: object, detector: object, blower_pid_thread: object, lock: object) -> None:
        # Inherit Menu class
        # We also need to give mainframe (container) for the tk.Menu constructor
        super().__init__(container)

        # Initialize
        self.container = container
        self.ini_updater = ini_updater
        self.flow_meter = flow_meter
        self.daq = daq
        self.detector = detector
        self.blower_pid_thread = blower_pid_thread
        self.lock = lock

        # Settings
        settings_menu = tk.Menu(self)
        # Add settings label
        self.add_cascade(menu=settings_menu, label="Settings")

        settings_menu.add_command(
            label="Flow Meter", command=self.flow_meter_window)  # Add flow meter submenu
        settings_menu.add_command(
            label="Cpc", command=self.cpc_window)  # Add cpc submenu
        settings_menu.add_command(
            label="Daq", command=self.daq_window)  # Add daq submenu

    def flow_meter_window(self) -> None:
        """Popup window with flow meter serial port settings"""

        logging.info("Opened flow meter settings window")

        # Create the window and configure it
        window = tk.Toplevel(self.container)
        window.title("Flow meter")
        window.geometry("230x280")
        # Make the window resizable
        window.columnconfigure(0, weight=1)

        # Create labels
        labels = ["Port:", "Baud rate:", "Byte size:", "Parity:",
                  "Stopbits:", "Time out:", "SW flow control:", "HW flow control:"]
        create_labels(window, labels, 0, 0, "w", 1)

        # This list includes all the keys from the section in the ini file
        flow_meter_items = self.ini_updater.items("Flow_Meter:Serial_port")
        # Create entries
        entries_dict = create_entries(
            window, flow_meter_items, 0, 0, "e", 1)

        # Create save button
        save_button = ttk.Button(
            window, text="Save", command=lambda: self.flow_meter_save_btn_clk(entries_dict, window))
        save_button.grid(sticky="we", padx=50, pady=5)

    def flow_meter_save_btn_clk(self, flow_meter_serial_entries: dict, window: tk.Toplevel) -> None:
        """
        Save flow meter serial port settings from the entry fields to the ini file

        Update flow meter object to use updated serial port settings from the ini file
        """

        # Save to the ini file
        save_entries(flow_meter_serial_entries,
                     self.ini_updater, "Flow_Meter:Serial_port")

        window.destroy()  # Close the settings window

        # Use the lock to ensure that blower pid thread is not trying to read ftp data at the same time that the serial settings are changed
        self.lock.acquire()
        # Update serial settings from the ini file
        self.flow_meter.update_serial_settings()
        self.lock.release()

    def cpc_window(self) -> None:
        """Popup window with cpc's serial port settings"""

        logging.info("Opened cpc settings window")

        # Create the window and configure it
        window = tk.Toplevel(self.container)
        window.title("Cpc")
        window.geometry("230x280")
        # Make the window resizable
        window.columnconfigure(0, weight=1)

        # Create labels
        labels = ["Port:", "Baud rate:", "Byte size:", "Parity:",
                  "Stopbits:", "Time out:", "SW flow control:", "HW flow control:"]
        create_labels(window, labels, 0, 0, "w", 1)

        # This list includes all the keys from the section in the ini file
        cpc_items = self.ini_updater.items("Cpc:Serial_port")
        # Create entries
        entries_dict = create_entries(
            window, cpc_items, 0, 0, "e", 1)

        # Create save button
        # Cpc class loads saved values from the ini file before trying to read concentration
        save_button = ttk.Button(
            window, text="Save", command=lambda: self.cpc_save_btn_clk(entries_dict, window))
        save_button.grid(sticky="we", padx=50, pady=5)

    def cpc_save_btn_clk(self, cpc_entries: dict, window: tk.Toplevel) -> None:
        """
        Save cpc settings from the entry fields to the ini file

        Update cpc object to use updated settings from the ini file
        """

        # Save to the ini file
        save_entries(cpc_entries, self.ini_updater, "Cpc:Serial_port")

        window.destroy()  # Close the settings window

        # Update settings from the ini file
        self.detector.update_instance_variables()

    def daq_window(self) -> None:
        """Popup window with daq settings"""

        logging.info("Opened daq settings window")

        # Create the window and configure it
        window = tk.Toplevel(self.container)
        window.title("Daq")
        window.geometry("230x330")
        # Make the window resizable
        window.columnconfigure(0, weight=1)

        # Create labels
        labels = ["Device ID:", "AI min channel name(E.g. ai0):", "AI max channel number(E.g. 4):", "HV output channel:",
                  "Blower pulse channel:", "Cpc counter channel:", "Cpc signal channel", "Port channel:", "Total concentration valve line:", "Sample flow bypass valve line:"]
        create_labels(window, labels, 0, 0, "w", 1)

        # This list includes all the keys from the section in the ini file
        daq_items = self.ini_updater.items("NI_DAQ")
        # Create entries
        entries_dict = create_entries(
            window, daq_items, 0, 0, "e", 1)

        # Create save button
        save_button = ttk.Button(
            window, text="Save", command=lambda: self.daq_save_btn_clk(entries_dict, window))
        save_button.grid(sticky="we", padx=50, pady=5)

    def daq_save_btn_clk(self, daq_entries: dict, window: tk.Toplevel) -> None:
        """
        Save daq settings from the entry fields to the ini file

        Update daq object to use updated settings from the ini file
        """

        # Save to the ini file
        save_entries(daq_entries, self.ini_updater, "NI_DAQ")

        window.destroy()  # Close the settings window

        # Update settings from the ini file
        self.daq.update_daq_settings()
        # Update the tasks with new settings
        self.daq.update_tasks_settings()


class MaintenanceTab(ttk.Frame):
    """Maintenance tab, used for manually test a dmps"""

    def __init__(self, container, ini_updater, flow_meter, daq, detector, blower_pid_thread, flow_meter_queue, notebook) -> None:  # TODO: Typehints
        super().__init__(container)  # Inherit Frame class

        # Initialize
        self.ini_updater = ini_updater
        self.flow_meter = flow_meter
        self.daq = daq
        self.detector = detector
        self.blower_pid_thread = blower_pid_thread
        self.queue = flow_meter_queue
        self.notebook = notebook

        # Allow rows and columns to change size
        for i in range(1):
            self.rowconfigure(i, weight=1)
        for i in range(1):
            self.columnconfigure(i, weight=1)

        # Flow meter frame
        flow_meter_frame = ttk.LabelFrame(self, text="Flow meter")
        flow_meter_frame.grid(row=0, column=0, padx=5, pady=5)
        # Add content to the flow meter frame
        self.flow_meter_box(flow_meter_frame)

        # Blower PID frame
        blower_frame = ttk.LabelFrame(self, text="Blower PID")
        blower_frame.grid(row=1, column=0, padx=0, pady=0)
        # Add content to the flow meter frame
        self.blower_box(blower_frame)

        # NI DAQ frame
        daq_frame = ttk.LabelFrame(self, text="DAQ")
        daq_frame.grid(row=0, column=1, padx=5, pady=5)
        # Add content to the daq frame
        self.daq_box(daq_frame)

        # Cpc frame
        cpc_frame = ttk.LabelFrame(self, text="CPC")
        cpc_frame.grid(row=1, column=1, padx=5, pady=5)
        # Add content to the cpc frame
        self.cpc_box(cpc_frame)

    def flow_meter_box(self, container: ttk.LabelFrame) -> None:
        """Adds all the widgets for the flow meter frame"""

        # Create flow meter data labels
        data_labels = ["Flow:", "Temperature:", "Pressure:"]
        create_labels(container, data_labels, 0, 0, "w", 2)

        # Create flow meter value labels
        ftp_labels = ["None", "None", "None"]
        ftp_labels_list = create_labels(
            container, ftp_labels, 1, 0, "w", 2)

        # Create multiplier and offset labels
        ttk.Label(container, text="Multiplier:").grid(row=0, column=1)
        ttk.Label(container, text="Offset:").grid(row=0, column=2)

        # Scaling items list includes item's from the ini file in the given section
        scaling_items = self.ini_updater.items("Flow_Meter:Scaling")

        # Divide scaling_items to multiplier and offset lists
        multipliers = []
        offsets = []
        for i in range(len(scaling_items)):
            if i % 2 == 0:  # Even = multiplier in the scaling_items list
                multipliers.append(scaling_items[i])
            elif i % 2 != 0:  # Odd = offset in the scaling_items list
                offsets.append(scaling_items[i])

        # Create multiplier and offset entries
        # Multipliers and offsets were separated from the scaling_items because ->
        # we can't place them in desired spot in the GUI with the create_entries function otherwise
        multiplier_entries = create_entries(
            container, multipliers, 1, 1, "we", 2)
        offset_entries = create_entries(container, offsets, 1, 2, "we", 2)

        # Combine offset and span dicts
        multiplier_and_offset_entries = dict(offset_entries)
        multiplier_and_offset_entries.update(multiplier_entries)

        # Create measure button
        measure_ftp_btn = ttk.Button(
            container, text="Start measurement", command=lambda: self.ftp_measure_start(ftp_labels_list, measure_ftp_btn))
        measure_ftp_btn.grid(row=6, column=0, sticky="w", pady=5, padx=5)

        # Create multipliers/offsets save button
        save_button = ttk.Button(
            container, text="Save", command=lambda: self.save_button_click(multiplier_and_offset_entries))
        save_button.grid(row=6, column=2, sticky="e",
                         pady=5, padx=5, ipadx=1, ipady=1)

    def ftp_measure_start(self, ftp_labels: list, measure_ftp_btn: ttk.Button) -> None:
        """
        Start reading flow, temp and pressure from the flow meter ftp queue and update GUI to display the measurements

        Change button command to stop the measurement if button is clicked again
        """

        # Handle the event that the queue is empty(should not happen on normal circumstances)
        if self.queue.empty():
            flow, temp, pressure = None, None, None
        else:
            flow, temp, pressure = self.queue.get()  # Read the queue

        # Update the labels
        # TODO: This could be improved?
        ftp_labels[0].config(text=f"{flow} L/min")
        ftp_labels[1].config(text=f"{temp} °C")
        ftp_labels[2].config(text=f"{pressure} kPa")

        # Call this method every 0.5s
        # after_id is used to stop calling this method
        ftp_after_id = self.after(
            500, lambda: self.ftp_measure_start(ftp_labels, measure_ftp_btn))

        # Change what happens if the button is clicked again
        measure_ftp_btn.configure(text="Stop measurement", command=lambda: self.ftp_measure_stop(
            ftp_labels, measure_ftp_btn, ftp_after_id))

        # Stop the measurement if the maintenance tab is not active tab
        if self.notebook.index(self.notebook.select()) != 0:
            self.ftp_measure_stop(ftp_labels, measure_ftp_btn, ftp_after_id)

    # TODO: Improve typehints
    def ftp_measure_stop(self, ftp_labels: list, measure_ftp_btn: ttk.Button, ftp_after_id):
        """
        Stop measuring the flow meter's values

        Change the button's command to start the measurement if button is clicked again
        """

        measure_ftp_btn.configure(
            text="Start measurement", command=lambda: self.ftp_measure_start(ftp_labels, measure_ftp_btn))

        # End the call loop
        self.after_cancel(ftp_after_id)

    def save_button_click(self, entries: dict) -> None:
        """Save flow meter's multipliers and offsets to ini and update the flow meter object"""

        # Save to the ini file
        save_entries(entries, self.ini_updater, "Flow_Meter:Scaling")

        # Update the flow meter object's settings
        self.flow_meter.spans_and_offsets()

        logging.info("Clicked save multipliers/offsets button")

    def blower_box(self, container) -> None:
        """Adds all the widgets for the blower pid frame"""

        # Create blower pid data labels
        data_labels = ["Target flow:", "Frequency:",
                       "Sample time:", "P:", "I:", "D:"]
        create_labels(container, data_labels, 0, 0, "w", 1)

        # Pid settings list includes item's from the ini file in the given section
        pid_settings = self.ini_updater.items("Pid")

        # Create entries for data labels
        pid_entries = create_entries(container, pid_settings, 0, 1, "we", 1)

        # Create save button
        save_button = ttk.Button(
            container, text="Save pid settings", command=lambda: self.save_pid_settings(pid_entries))
        save_button.grid(row=6, column=1, sticky="e",
                         pady=5, padx=5, ipadx=1, ipady=1)

    def save_pid_settings(self, entries: dict) -> None:
        """Saves pid settings to the ini file and update pid object"""

        # Update the ini file
        save_entries(entries, self.ini_updater, "Pid")

        # Get values from the entries
        target_flow = float(entries["target_flow"].get())
        frequency = float(entries["frequency"].get())
        sample_time = float(entries["sample_time"].get())
        p = float(entries["p"].get())
        i = float(entries["i"].get())
        d = float(entries["d"].get())

        # Update the PID object
        self.blower_pid_thread.pid.auto_mode = False  # Pause updating pid control
        self.blower_pid_thread.pid.setpoint = target_flow
        self.blower_pid_thread.frequency = frequency
        self.blower_pid_thread.pid.sample_time = sample_time
        self.blower_pid_thread.pid.tunings = (p, i, d)
        self.blower_pid_thread.pid.auto_mode = True  # Continue updating pid control

    def daq_box(self, container: ttk.LabelFrame) -> None:
        """Adds all the widgets for the daq frame"""

        # Data labels
        data_labels = ["Flow:", "Temperature:",
                       "Pressure:", "RH:", "HV in:", "HV out:", "Flow bypass valve:", "Total concentration valve:"]
        create_labels(container, data_labels, 0, 0, "w", 1)

        # Value labels
        daq_value_labels = ["None", "None", "None", "None", "None", "None"]
        daq_value_labels_list = create_labels(
            container, daq_value_labels, 0, 1, "w", 1)

        # Solenoid valve labels
        solenoid_labels = ["None", "None"]
        solenoid_labels_list = create_labels(
            container, solenoid_labels, 6, 1, "w", 1)

        # HV out unit label
        ttk.Label(container, text="V").grid(row=5, column=2, sticky="e")

        # High voltage out entry
        hvo = tk.Entry(container, width=10)
        # Add default value from the ini file
        hvo.insert(
            tk.END, self.ini_updater["NI_DAQ:Sensors"]["hvo_voltage"].value)
        hvo.grid(row=5, column=1, sticky=("w"), padx=5, pady=5)

        # Set hvo button
        hvo_button = ttk.Button(
            container, text="Set HV out", command=lambda: self.set_hv_out(hvo))
        hvo_button.grid(row=5, column=3, sticky="w", padx=5, pady=5)

        # Solenoid valve buttons
        conc_valve_btn = ttk.Button(
            container, text="On/Off", command=lambda: self.valve_on_off(self.daq.conc_valve_task, solenoid_labels_list, "conc_valve"))
        conc_valve_btn.grid(row=6, column=3, sticky="w", padx=5, pady=5)

        bypass_valve_btn = ttk.Button(
            container, text="On/off", command=lambda: self.valve_on_off(self.daq.bypass_valve_task, solenoid_labels_list, "bypass_valve"))
        bypass_valve_btn.grid(row=7, column=3, sticky="w", padx=5, pady=5)

        # Measure button
        daq_measure_btn = ttk.Button(
            container, text="Start measurement", command=lambda: self.update_daq_labels_start(daq_value_labels_list, daq_measure_btn))
        daq_measure_btn.grid(row=9, column=0, sticky="w", padx=5, pady=5)

    def set_hv_out(self, hvo: ttk.Entry) -> None:
        """Set HV to output value given in HV output entry field, updates ini file with the new value"""

        logging.info("Clicked daq's set hv out button")
        hvo_value = hvo.get()  # Get hvo value from the entry field

        # Convert hvo to float and send it to the daq (set_ao scales it)
        self.daq.set_ao(float(hvo_value))
        # Update the ini file with the new hvo value
        self.ini_updater["NI_DAQ:Sensors"]["hvo_voltage"].value = hvo_value

        messagebox.showinfo(message="Saved!")

    def valve_on_off(self, do_task: object, labels: list, valve_str: str) -> None:  # TODO: Typehints
        """Button click changes valve state on or off, button's text is updated accordingly depending on the valve's state"""

        logging.info(f"Clicked {do_task} on/off button")

        # Get boolean depending on the valve's state before changing it
        state_before = do_task.read()  # Read state before the change

        # Change valve's state to opposite value that it currently is
        if state_before:
            self.daq.set_do(do_task, False)
            state_now = False
        else:
            self.daq.set_do(do_task, True)
            state_now = True

        # If valve state is True set a button's text accordingly and vice versa
        if valve_str == "conc_valve":  # Total concentration valve
            if state_now:
                labels[0].config(text="Low flow")
            else:
                labels[0].config(text="High flow")
        if valve_str == "bypass_valve":
            if state_now:
                labels[1].config(text="Total concentration")
            else:
                labels[1].config(text="Dma concentration")

    def update_daq_labels_start(self, daq_labels: list, daq_measure_btn: ttk.Button) -> None:
        """Reads analog inputs from the daq and updates GUI to display the values"""

        self.daq.measure_ai()  # Measure

        # Scale measured voltages to proper units
        # scale_value gets voltages from the ini file
        flow = self.daq.scale_value("f")
        p = self.daq.scale_value("p")
        t = self.daq.scale_value("t")
        rh = self.daq.scale_value("rh")
        hvi = self.daq.scale_value("hvi")

        # Update the labels
        values = [flow, t, p, rh, hvi]
        units = ["L/min", "°C", "Pa", "%", "V"]
        for i in range(len(values)):
            daq_labels[i].config(text=f"{round(values[i], 2)} {units[i]}")

        # Call this method every 1s
        # after_id is used to stop calling this method
        daq_after_id = self.after(
            1000, lambda: self.update_daq_labels_start(daq_labels, daq_measure_btn))

        # Change what happens if the button is clicked again
        daq_measure_btn.configure(
            text="Stop measurement", command=lambda: self.update_daq_labels_stop(daq_measure_btn, daq_after_id, daq_labels))

        # Stop the measurement if the maintenance tab is not active tab
        if self.notebook.index(self.notebook.select()) != 0:
            self.update_daq_labels_stop(
                daq_measure_btn, daq_after_id, daq_labels)

    # TODO: Improve typehints
    def update_daq_labels_stop(self, daq_measure_btn: ttk.Button, daq_after_id, daq_labels: list) -> None:
        """
        Stop measuring the daq's values

        Change the button's command to start the measurement if button is clicked again
        """

        daq_measure_btn.configure(
            text="Start measurement", command=lambda: self.update_daq_labels_start(daq_labels, daq_measure_btn))

        # End the call loop
        self.after_cancel(daq_after_id)

    def cpc_box(self, container) -> None:
        """Adds all the widgets for the cpc frame"""

        # Create conc label
        conc_label = ttk.Label(container, text="1s average concentration:")
        conc_label.grid(row=0, column=0, sticky="we", padx=5, pady=5)

        # Create conc data label
        conc_data_label = ttk.Label(container, text="None")
        conc_data_label.grid(row=1, column=0, sticky="we", padx=5, pady=5)

        # Measure button
        cpc_measure_btn = ttk.Button(
            container, text="Start measurement", command=lambda: self.cpc_measure_start(conc_data_label, cpc_measure_btn))
        cpc_measure_btn.grid(row=9, column=0, sticky="w", padx=5, pady=5)

    def cpc_measure_start(self, cpc_label: ttk.Label, cpc_btn: ttk.Button) -> None:
        """Start measuring avg concentration from the cpc every 1s"""

        conc = self.detector.read_rd()

        if conc != None:
            cpc_label.config(text=f"{round(conc, 2)} p/cm^3")
        else:
            cpc_label.config(text="None")

        # Call this method every 1s
        # after_id is used to stop calling this method
        cpc_after_id = self.after(
            1000, lambda: self.cpc_measure_start(cpc_label, cpc_btn))

        # Change what happens if the button is clicked again
        cpc_btn.configure(
            text="Stop measurement", command=lambda: self.cpc_measure_stop(cpc_btn, cpc_after_id, cpc_label))

        # Stop the measurement if the maintenance tab is not active tab
        if self.notebook.index(self.notebook.select()) != 0:
            self.cpc_measure_stop(cpc_btn, cpc_after_id, cpc_label)

    # TODO: Typehints
    def cpc_measure_stop(self, cpc_btn: ttk.Button, cpc_after_id, cpc_label: ttk.Label) -> None:
        """
        Stop measuring the concentration

        Change the button's command to start the measurement if button is clicked again
        """

        cpc_btn.configure(
            text="Start measurement", command=lambda: self.cpc_measure_start(cpc_label, cpc_btn))

        # End the call loop
        self.after_cancel(cpc_after_id)


class MeasurementTab(ttk.Frame):
    """Automatic concentration measurement tab"""

    def __init__(self, container, automatic_measurement_thread, voltage_queue, conc_queue) -> None:  # TODO: Improve typehints
        super().__init__(container)  # Inherit Frame class

        # Plot
        plot_fig = Figure(figsize=(7, 4), dpi=100)
        ax = plot_fig.add_subplot()
        ax.set_xlabel("Voltage [V]")
        ax.set_ylabel("Concentration [1/cm^3]")

        canvas = FigureCanvasTkAgg(plot_fig, master=self)  # A tk.DrawingArea.
        canvas.draw()
        x_coord = []
        y_coord = []

        canvas.get_tk_widget().grid(padx=10, pady=10)

        # Measure button
        measurement_btn = ttk.Button(
            self, text="Start", command=lambda: self.automatic_measurement_start(automatic_measurement_thread, measurement_btn, ax, voltage_queue, conc_queue, canvas, x_coord, y_coord))
        measurement_btn.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    # TODO: Typehints
    def automatic_measurement_start(self, automatic_measurement_thread, measure_btn, ax, voltage_queue, conc_queue, canvas, x_coord, y_coord) -> None:
        """Start automatic measurement thread"""

        # Start the thread
        automatic_measurement_thread.run_measure = True

        if automatic_measurement_thread.reset_plot:
            x_coord.clear()
            y_coord.clear
            automatic_measurement_thread.reset_plot = False
        else:
            # Plot
            if voltage_queue.empty() or conc_queue.empty():
                pass
            else:
                x = voltage_queue.get()
                y = conc_queue.get()
                x_coord.append(x)
                y_coord.append(y)
                ax.plot(x_coord, y_coord, marker="o")

            canvas.draw()
            canvas.get_tk_widget().grid(padx=10, pady=10)

        # Call this method every 5s
        # after_id is used to stop calling this method
        plot_after_id = self.after(
            5000, lambda: self.automatic_measurement_start(automatic_measurement_thread, measure_btn, ax, voltage_queue, conc_queue, canvas, x_coord, y_coord))

        # Configure button to stop the measurement if it is clicked again
        measure_btn.configure(text="Stop", command=lambda: self.automatic_measurement_stop(
            automatic_measurement_thread, measure_btn, ax, voltage_queue, conc_queue, canvas, plot_after_id, x_coord, y_coord))

    # TODO: Typehints
    def automatic_measurement_stop(self, automatic_measurement_thread, measure_btn, ax, voltage_queue, conc_queue, canvas, plot_after_id, x_coord, y_coord) -> None:
        """Stop automatic measurement thread"""

        # Stop the thread after current measurement loop is complete
        automatic_measurement_thread.run_measure = None

        # Configure button to stop the measurement if it is clicked again
        measure_btn.configure(text="Start", command=lambda: self.automatic_measurement_start(
            automatic_measurement_thread, measure_btn, ax, voltage_queue, conc_queue, canvas, x_coord, y_coord))

        # End the call loop
        self.after_cancel(plot_after_id)


# General functions for the classes

def create_labels(container, names: list, row_num: int, col_num: int, pos: str, row_offset: int) -> list:
    """Create labels from given list of names and other parameters. Return list of created label objects"""

    labels_list = []
    for name in names:
        label = ttk.Label(container, text=name)
        label.grid(row=row_num, column=col_num, sticky=pos, padx=5, pady=5)
        row_num += row_offset
        labels_list.append(label)

    return labels_list


def create_entries(container, items: list, row_num: int, col_num: int, pos: str, row_offset: int) -> dict:
    """Create entries from given list of tuples and other parameters. Returns dict of created entries"""

    entries = {}
    for item in items:
        entry = tk.Entry(container, width=7)  # Create entry
        # Insert default value to the entry field
        # item[1] contains thingies with name and value of the item in the ini file
        entry.insert(tk.END, item[1].value)
        # item[0] contains name of the saved value in the ini file. Add to the dict: {name: entry}
        entries[item[0]] = entry
        entry.grid(row=row_num, column=col_num, sticky=pos, padx=5, pady=5)
        row_num += row_offset

    return entries


def save_entries(entries: dict, ini_updater: object, section: str) -> None:  # TODO: Improve type hint
    """Writes values from given entry fields dict (format: {name of the entry: entry} to the ini file"""

    logging.info("Saved values from some entries to the ini file")

    # Entries contains tuples with following format: {entry name, entry}
    for name in entries:
        # Update value in the ini file
        ini_updater[section][name] = entries[name].get()

    ini_updater.update_file()  # Save changes
    ini_updater.read("config.ini")  # Load changes to the ini_updater object

    # TODO: Change dialog just to appear and then fade away
    messagebox.showinfo(message="Saved!")
