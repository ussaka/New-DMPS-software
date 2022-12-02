import logging
import queue
import tkinter as tk
from multiprocessing import Lock
from tkinter import ttk, messagebox

import nidaqmx

import config
import detectors
import flow_meters
import ni_daqs
from gui.general_functions import create_labels, create_entries
from threads import pid_ftp_thread


class MaintenanceTab(ttk.Frame):
    """
    Used to configure and display data from the dmps
    """

    def __init__(self, container, conf: config.Config, flow_meter: flow_meters, daq: ni_daqs, detector: detectors,
                 blower_pid_thread: pid_ftp_thread, flow_meter_queue: queue.Queue, daq_queue: queue.Queue,
                 rd_queue: queue.Queue, notebook: ttk.Notebook, flow_meter_lock: Lock, daq_lock: Lock) -> None:
        super().__init__(container)  # Inherit Frame class

        # Initialize
        self.__conf = conf
        self.__flow_meter = flow_meter
        self.__daq = daq
        self.__detector = detector
        self.__blower_pid_thread = blower_pid_thread
        self.__fw_queue = flow_meter_queue
        self.__daq_queue = daq_queue
        self.__rd_queue = rd_queue
        self.__notebook = notebook
        self.__fw_lock = flow_meter_lock
        self.__daq_lock = daq_lock
        self.__daq_conf = self.__conf.get_configuration("NI_DAQ")
        self.__daq_scaling = self.__conf.get_configuration("NI_DAQ_Scaling")
        self.__fw_scaling_conf = self.__conf.get_configuration("Flow_Meter_Scaling")
        self.__pid_conf = self.__conf.get_configuration("Pid")

        # Allow rows and columns to change size
        for i in range(1):
            self.rowconfigure(i, weight=1)
        for i in range(1):
            self.columnconfigure(i, weight=1)

        # Flow meter frame
        flow_meter_frame = ttk.LabelFrame(self, text="Flow meter")
        flow_meter_frame.grid(row=0, column=0, padx=5, pady=5)
        # Add content to the flow meter frame
        self.__flow_meter_box(flow_meter_frame)

        # Blower PID frame
        blower_frame = ttk.LabelFrame(self, text="Blower PID")
        blower_frame.grid(row=1, column=0, padx=0, pady=0)
        # Add content to the flow meter frame
        self.__blower_box(blower_frame)

        # NI DAQ frame
        daq_frame = ttk.LabelFrame(self, text="DAQ")
        daq_frame.grid(row=0, column=1, padx=5, pady=5)
        # Add content to the daq frame
        self.__daq_box(daq_frame)

        # Cpc frame
        cpc_frame = ttk.LabelFrame(self, text="CPC")
        cpc_frame.grid(row=1, column=1, padx=5, pady=5)
        # Add content to the cpc frame
        self.__cpc_box(cpc_frame)

    def __flow_meter_box(self, container: ttk.LabelFrame) -> None:
        """
        Adds content for the flow meter frame
        """

        # Create flow meter data name labels
        data_names = ["Flow:", "Temperature:", "Pressure:"]
        create_labels(container, data_names, 0, 0, "w", 2)

        # Create flow meter data value labels
        ftp_value_labels = ["None", "None", "None"]
        ftp_labels = create_labels(container, ftp_value_labels, 1, 0, "w", 2)

        # Create multiplier and offset name labels
        ttk.Label(container, text="Multiplier:").grid(row=0, column=1)
        ttk.Label(container, text="Offset:").grid(row=0, column=2)

        # Divide flow_meter_conf to multiplier and offset lists
        multipliers = {"f_multiplier": self.__fw_scaling_conf.get("f_multiplier"),
                       "t_multiplier": self.__fw_scaling_conf.get("t_multiplier"),
                       "p_multiplier": self.__fw_scaling_conf.get("p_multiplier")}

        offsets = {"f_offset": self.__fw_scaling_conf.get("f_offset"),
                   "t_offset": self.__fw_scaling_conf.get("t_offset"),
                   "p_offset": self.__fw_scaling_conf.get("p_offset")}

        # Create multiplier and offset entries
        multiplier_entries = create_entries(container, multipliers, 1, 1, "we", 2)
        offset_entries = create_entries(container, offsets, 1, 2, "we", 2)

        # Combine multiplier and offset dicts
        multiplier_and_offset_entries = dict(offset_entries)
        multiplier_and_offset_entries.update(multiplier_entries)

        # Create measure button
        measure_ftp_btn = ttk.Button(
            container, text="Start measurement",
            command=lambda: self.__ftp_measure_start(ftp_labels, measure_ftp_btn))
        measure_ftp_btn.grid(row=6, column=0, sticky="w", pady=5, padx=5)

        # Create multipliers/offsets save button
        save_button = ttk.Button(
            container, text="Save", command=lambda: self.__save_mult_offset_click(multiplier_and_offset_entries))
        save_button.grid(row=6, column=2, sticky="e",
                         pady=5, padx=5, ipadx=1, ipady=1)

    def __ftp_measure_start(self, ftp_labels: list, measure_ftp_btn: ttk.Button) -> None:
        """
        Start reading flow, temp and pressure from the flow meter ftp queue and update GUI to display the measurements

        Change button command to stop the measurement if button is clicked again
        """

        # Handle the event that the queue is empty(should not happen on normal circumstances)
        if self.__fw_queue.empty():
            flow, temp, pressure = None, None, None
        else:
            flow, temp, pressure = self.__fw_queue.get()  # Read the queue

        # Update the labels
        ftp_labels[0].config(text=f"{flow} L/min")
        ftp_labels[1].config(text=f"{temp} °C")
        ftp_labels[2].config(text=f"{pressure} kPa")

        # Call this method every 0.5s
        # after_id is used to stop calling this method
        ftp_after_id = self.after(
            500, lambda: self.__ftp_measure_start(ftp_labels, measure_ftp_btn))

        # Change what happens if the button is clicked again
        measure_ftp_btn.configure(text="Stop measurement", command=lambda: self.__ftp_measure_stop(
            ftp_labels, measure_ftp_btn, ftp_after_id))

        # Stop the measurement if the maintenance tab is not active tab
        if self.__notebook.index(self.__notebook.select()) != 0:
            self.__ftp_measure_stop(ftp_labels, measure_ftp_btn, ftp_after_id)

    def __ftp_measure_stop(self, ftp_labels: list, measure_ftp_btn: ttk.Button, ftp_after_id):
        """
        Stop measuring the flow meter's values

        Change the button's command to start the measurement if button is clicked again
        """

        measure_ftp_btn.configure(
            text="Start measurement", command=lambda: self.__ftp_measure_start(ftp_labels, measure_ftp_btn))

        # End the call loop
        self.after_cancel(ftp_after_id)

    def __save_mult_offset_click(self, entries: dict) -> None:
        """
        Save flow meter's multipliers and offsets to the ini file and update the flow meter object
        """

        self.__fw_lock.acquire()
        for name in entries:
            # Update value in the ini file
            self.__conf.write("Flow_Meter:Scaling", entries[name], entries[name].get())
        self.__conf.update_configuration(self.__fw_scaling_conf, "Flow_Meter:Scaling")  # Update the conf dict
        self.__fw_lock.release()

        messagebox.showinfo(message="Saved!")  # Display message

        logging.info("Saved values from multiplier/offset entries to the ini file")

    def __blower_box(self, container) -> None:
        """
        Add all the widgets for the blower pid frame
        """

        # Create blower pid data name labels
        data_labels = ["Frequency:", "Sample time:", "P:", "I:", "D:"]
        create_labels(container, data_labels, 0, 0, "w", 1)

        # Create entries for the data labels
        pid_entries = create_entries(container, self.__pid_conf, 0, 1, "we", 1)

        # Create save button
        save_button = ttk.Button(container, text="Save pid settings",
                                 command=lambda: self.__save_pid_settings(pid_entries))
        save_button.grid(row=6, column=1, sticky="e", pady=5, padx=5, ipadx=1, ipady=1)

    def __save_pid_settings(self, entries: dict) -> None:
        """
        Saves pid settings to the ini file and update pid object in pid_ftp_thread
        """

        for name in entries:
            # Update value in the ini file
            self.__conf.write("Pid", entries[name], entries[name].get())

        # Get values from the entries
        target_flow = float(entries["target_flow"].get())
        frequency = float(entries["frequency"].get())
        sample_time = float(entries["sample_time"].get())
        p = float(entries["p"].get())
        i = float(entries["i"].get())
        d = float(entries["d"].get())

        self.__blower_pid_thread.update_pid_settings(target_flow, sample_time, p, i, d, frequency)

    def __daq_box(self, container: ttk.LabelFrame) -> None:
        """
        Adds all the widgets for the daq frame
        """

        # Data labels
        data_labels = ["Flow:", "Temperature:", "Pressure:", "RH:", "HV in:", "HV out:", "Total concentration valve:",
                       "Flow bypass valve:"]
        create_labels(container, data_labels, 0, 0, "w", 1)

        # Value labels
        daq_value_labels = ["None", "None", "None", "None", "None", "None"]
        daq_value_labels_list = create_labels(container, daq_value_labels, 0, 1, "w", 1)

        # Solenoid valve labels
        solenoid_labels = ["None", "None"]
        solenoid_labels_list = create_labels(container, solenoid_labels, 6, 1, "w", 1)

        # HV out unit label
        ttk.Label(container, text="V").grid(row=5, column=2, sticky="e")

        # High voltage out entry
        hvo = tk.Entry(container, width=10)
        hvo.grid(row=5, column=1, sticky="w", padx=5, pady=5)

        # Set hvo button
        hvo_button = ttk.Button(container, text="Set HV out", command=lambda: self.__set_hv_out(hvo))
        hvo_button.grid(row=5, column=3, sticky="w", padx=5, pady=5)

        # Solenoid valve buttons
        conc_valve_btn = ttk.Button(container, text="On/Off",
                                    command=lambda: self.__valve_on_off(self.__daq.conc_valve_task,
                                                                        solenoid_labels_list, "conc_valve"))
        conc_valve_btn.grid(row=6, column=3, sticky="w", padx=5, pady=5)

        bypass_valve_btn = ttk.Button(container, text="On/off",
                                      command=lambda: self.__valve_on_off(self.__daq.bypass_valve_task,
                                                                          solenoid_labels_list, "bypass_valve"))
        bypass_valve_btn.grid(row=7, column=3, sticky="w", padx=5, pady=5)

        # Measure button
        daq_measure_btn = ttk.Button(container, text="Start measurement",
                                     command=lambda: self.__update_daq_labels_start(daq_value_labels_list,
                                                                                    daq_measure_btn))
        daq_measure_btn.grid(row=9, column=0, sticky="w", padx=5, pady=5)

    def __set_hv_out(self, hvo: ttk.Entry) -> None:
        """
        Set HV to output value given in HV output entry field, updates ini file with the new value
        """

        logging.info("Clicked daq's set hv out button")
        hvo_value = hvo.get()  # Get hvo value from the entry field

        # Convert hvo to float and send it to the daq (set_ao scales it)
        self.__daq.set_ao(float(hvo_value))
        messagebox.showinfo(message="Saved!")

    def __valve_on_off(self, do_task: nidaqmx.Task, labels: list, valve_str: str) -> None:
        """
        Button click changes valve state on/off
        Button's text is updated accordingly depending on the valve's state
        """

        logging.info(f"Clicked {do_task} on/off button")

        # Get boolean depending on the valve's state before changing it
        state_before = do_task.read(1)[0]  # Read state before the change

        # Change valve's state to opposite value that it currently is
        self.__daq_lock.acquire()
        if state_before:
            self.__daq.set_do(do_task, False)
            state_now = False
        else:
            self.__daq.set_do(do_task, True)
            state_now = True
        self.__daq_lock.release()

        # If valve state is True set a button's text accordingly and vice versa
        if valve_str == "conc_valve":  # Total concentration valve
            if state_now:
                labels[0].config(text="Total concentration")
            else:
                labels[0].config(text="Dma concentration")
        if valve_str == "bypass_valve":
            if state_now:
                labels[1].config(text="Low Flow")
            else:
                labels[1].config(text="High flow")

    def __update_daq_labels_start(self, daq_labels: list, daq_measure_btn: ttk.Button) -> None:
        """
        Reads analog inputs from the daq and updates GUI to display the values
        """

        # Handle the event that the queue is empty(should not happen on normal circumstances)
        if self.__daq_queue.empty():
            volts = [0, 0, 0, 0, 0, 0]
        else:
            volts = self.__daq_queue.get()  # Read the queue

        self.__daq_lock.acquire()
        # Scale measured voltages to proper units
        # scale_value gets voltages from the ini file
        flow = self.__daq.scale_value("f", volts[int(self.__daq_scaling["f_chan"])])
        p = self.__daq.scale_value("p", volts[int(self.__daq_scaling["p_chan"])])
        t = self.__daq.scale_value("t", volts[int(self.__daq_scaling["t_chan"])])
        rh = self.__daq.scale_value("rh", volts[int(self.__daq_scaling["rh_chan"])])
        hvi = self.__daq.scale_value("hvi", volts[int(self.__daq_scaling["hvi_chan"])])
        self.__daq_lock.release()

        # Update the labels
        values = [flow, t, p, rh, hvi]
        units = ["L/min", "°C", "Pa", "%", "V"]
        for i in range(len(values)):
            daq_labels[i].config(text=f"{round(values[i], 2)} {units[i]}")

        # Call this method every 0.5s
        # after_id is used to stop calling this method
        daq_after_id = self.after(500, lambda: self.__update_daq_labels_start(daq_labels, daq_measure_btn))

        # Change what happens if the button is clicked again
        daq_measure_btn.configure(text="Stop measurement",
                                  command=lambda: self.__update_daq_labels_stop(daq_measure_btn, daq_after_id,
                                                                                daq_labels))

        # Stop the measurement if the maintenance tab is not active tab
        if self.__notebook.index(self.__notebook.select()) != 0:
            self.__update_daq_labels_stop(daq_measure_btn, daq_after_id, daq_labels)

    def __update_daq_labels_stop(self, daq_measure_btn: ttk.Button, daq_after_id, daq_labels: list) -> None:
        """
        Stop measuring the daq's values

        Change the button's command to start the measurement if button is clicked again
        """

        daq_measure_btn.configure(text="Start measurement",
                                  command=lambda: self.__update_daq_labels_start(daq_labels, daq_measure_btn))

        # End the call loop
        self.after_cancel(daq_after_id)

    def __cpc_box(self, container) -> None:
        """
        Adds all the widgets for the cpc frame
        """

        # Create conc label
        conc_label = ttk.Label(container, text="1s average concentration:")
        conc_label.grid(row=0, column=0, sticky="we", padx=5, pady=5)

        # Create conc data label
        conc_data_label = ttk.Label(container, text="None")
        conc_data_label.grid(row=1, column=0, sticky="we", padx=5, pady=5)

        # Measure button
        cpc_measure_btn = ttk.Button(container, text="Start measurement",
                                     command=lambda: self.cpc_measure_start(conc_data_label, cpc_measure_btn))
        cpc_measure_btn.grid(row=9, column=0, sticky="w", padx=5, pady=5)

    def cpc_measure_start(self, cpc_label: ttk.Label, cpc_btn: ttk.Button) -> None:
        """
        Start measuring avg concentration from the cpc every 0.5s
        """

        # Handle the event that the queue is empty(should not happen on normal circumstances)
        if self.__rd_queue.empty():
            conc = None
        else:
            conc = self.__rd_queue.get()  # Read the queue

        if conc is not None:
            cpc_label.config(text=f"{round(conc, 2)} p/cm^3")
        else:
            cpc_label.config(text="None")

        # Call this method every 0.5s
        # after_id is used to stop calling this method
        cpc_after_id = self.after(500, lambda: self.cpc_measure_start(cpc_label, cpc_btn))

        # Change what happens if the button is clicked again
        cpc_btn.configure(text="Stop measurement",
                          command=lambda: self.cpc_measure_stop(cpc_btn, cpc_after_id, cpc_label))

        # Stop the measurement if the maintenance tab is not active tab
        if self.__notebook.index(self.__notebook.select()) != 0:
            self.cpc_measure_stop(cpc_btn, cpc_after_id, cpc_label)

    def cpc_measure_stop(self, cpc_btn: ttk.Button, cpc_after_id, cpc_label: ttk.Label) -> None:
        """
        Stop measuring the concentration

        Change the button's command to start the measurement if button is clicked again
        """

        cpc_btn.configure(text="Start measurement", command=lambda: self.cpc_measure_start(cpc_label, cpc_btn))

        # End the call loop
        self.after_cancel(cpc_after_id)
