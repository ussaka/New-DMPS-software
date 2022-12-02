"""
This module provides functionality for National Instruments data acquisition devices (6211 and 6215)
"""

import logging

import nidaqmx
from nidaqmx.constants import AcquisitionType
from nidaqmx.stream_writers import CounterWriter

import config


class NiDaq:
    """
    This class is used for reading and writing data to/from NI DAQ. It is tested to work with NI6211
    """

    def __init__(self, conf: config.Config) -> None:
        self.__conf = conf
        self.__nidaq_conf = self.__conf.get_configuration("NI_DAQ")  # Get configuration dict
        self.__scaling_conf = self.__conf.get_configuration("NI_DAQ_Scaling")  # Get scaling dict

        self.__ai_task = self.__create_ai_task()  # Analog input task
        self.__ao_task = self.__create_ao_task()  # Analog output task

        # Get line numbers and create tasks for the valves
        # TODO: This could be done with only one task containing virtual tasks(?)
        conc_line = self.__nidaq_conf.get("conc_line_chan")
        bypass_line = self.__nidaq_conf.get("bypass_line_chan")
        self.conc_valve_task = self.__create_do_task(conc_line)  # Task to control total concentration valve
        self.bypass_valve_task = self.__create_do_task(bypass_line)  # Task to control sample flow bypass valve

        self.__counter_task = self.__create_counter_task()
        self.__pulse_task = self.__create_pulse_task()

        logging.info("Created NiDaq object")

    def __create_ai_task(self) -> nidaqmx.Task:
        """
        Create analog input task to read analog input voltages

        Remember to close this task after it is not used anymore!
        """

        # Get the variables
        device_id = self.__nidaq_conf.get("device_id")
        ai_min = self.__nidaq_conf.get("ai_min")
        ai_max = self.__nidaq_conf.get("ai_max")
        min_v = float(self.__nidaq_conf.get("ai_min_v"))
        max_v = float(self.__nidaq_conf.get("ai_max_v"))

        ai_task = nidaqmx.Task(new_task_name="ai_task")  # Create the task
        ai_str = f"Dev{device_id}/ai{ai_min}:{ai_max}"

        try:
            # Set channels that are measured and set min and max voltages that are read
            ai_task.ai_channels.add_ai_voltage_chan(ai_str, min_val=min_v, max_val=max_v)
            logging.info("Created ai task")
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Can't create ai task. Check device id and ai channel settings from the ini file")
            ai_task.close()

        return ai_task

    def __create_ao_task(self) -> nidaqmx.Task:
        """
        Create analog output task to write analog output voltage

        Remember to close this task after it is not used anymore!
        """

        # Get the variables
        device_id = self.__nidaq_conf.get("device_id")
        hvo_chan = self.__scaling_conf.get("hvo_chan")

        ao_task = nidaqmx.Task(new_task_name="ao_task")  # Create the task
        ao_str = f"Dev{device_id}/ao{hvo_chan}"

        try:
            ao_task.ao_channels.add_ao_voltage_chan(ao_str)
            logging.info("Created ao task")
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Can't create ao task. Check device_id and hv_output_chan values from the ini file")
            ao_task.close()

        return ao_task

    def __create_do_task(self, line: str) -> nidaqmx.Task:
        """
        Create do task with given line channel to handle digital output

        Remember to close this task after it is not used anymore!
        """

        # Get the variables
        device_id = self.__nidaq_conf.get("device_id")
        port_chan = self.__nidaq_conf.get("port_chan")

        do_task = nidaqmx.Task(new_task_name=f"do_task_line_{line}")  # Create the task
        do_str = f"Dev{device_id}/port{port_chan}/line{line}"
        try:
            do_task.do_channels.add_do_chan(do_str)
            logging.info(f"Created do_task_line_{line} task")
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Can't create do task. Check do settings from the ini file")
            do_task.close()

        return do_task

    def __create_counter_task(self) -> nidaqmx.Task:
        """
        Create counter task to count (CPC's) pulses

        Remember to close this task after it is not used anymore!
        """

        # Get the variables
        device_id = self.__nidaq_conf.get("device_id")
        counter_chan = self.__nidaq_conf.get("cpc_counter_chan")
        cpc_pulses_chan = self.__nidaq_conf.get("cpc_pulses_chan")

        # Create counter task
        counter_task = nidaqmx.Task(new_task_name="counter_task")
        counter_str = f"Dev{device_id}/ctr{counter_chan}"
        try:
            counter_task.ci_channels.add_ci_count_edges_chan(counter_str)
            # Select what (virtual?)channel to count
            # Use this if the default is wrong
            # TODO: This could be improved
            counter_task.ci_channels[0].ci_count_edges_term = f"/Dev{device_id}/PFI{cpc_pulses_chan}"
            logging.info("Created counter task")

        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Can't create counter task. Check counter settings from the ini file")
            counter_task.close()

        try:
            counter_task.start()
            logging.info("Started counter task")
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Counter task failed to start!")

        return counter_task

    def __create_pulse_task(self) -> nidaqmx.Task:
        """
        Create task that can generate pulses that control the blower with pid. Return's pulse task object

        Remember to close this task after it is not used anymore!
        """

        # Get the variables
        device_id = self.__nidaq_conf.get("device_id")
        blower_pulse_chan = self.__nidaq_conf.get("blower_pulse_chan")

        # Create the task
        pulse_task = nidaqmx.Task(new_task_name="pulse_task")
        pulse_str = f"Dev{device_id}/ctr{blower_pulse_chan}"
        try:
            pulse_task.co_channels.add_co_pulse_chan_time(pulse_str)
            # Generate infinite amount of pulses
            pulse_task.timing.cfg_implicit_timing(sample_mode=AcquisitionType.CONTINUOUS)
            logging.info("Created pulse task")
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Device id or counter channel settings are probably wrong")
            pulse_task.close()

        try:
            pulse_task.start()
            self.cw_writer = CounterWriter(pulse_task.out_stream, True)
            logging.info("Started pulse task")
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Pulse task failed to start!")

        return pulse_task

    def close_tasks(self) -> None:
        """
        Close all tasks
        """

        # TODO: Catch warning message if tasks were already closed
        self.__ai_task.close()
        self.__ao_task.close()
        self.bypass_valve_task.close()
        self.conc_valve_task.close()
        self.__counter_task.close()
        self.__pulse_task.close()
        logging.info("Closed all NIDAQ tasks")

    def rst_ctr_task(self) -> None:
        """
        Reset counter task counter
        """

        try:
            self.__counter_task.stop()
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Counter task failed to stop!")
        try:
            self.__counter_task.start()
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Counter task failed to stop!")

        logging.info("Counter task reset successfully")

    def read_ctr_task(self) -> float:
        """
        Read counter task counter

        Return None if read failed
        """

        counts = None
        try:
            counts = self.__counter_task.read()
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Counter task failed to read!")

        logging.info(f"Counter task read: {counts}")
        return counts

    def measure_ai(self) -> list:
        """
        Reads analog input signals (voltages) from the DAQ
        """

        try:
            ai_voltages = self.__ai_task.read()  # Voltages are ordered so that voltages[0] is ai0's voltage
            return ai_voltages
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Failed to read analog input voltages")

    def set_ao(self, ao_voltage: float) -> None:
        """
        Write to the analog output. Output value given as parameter in volts
        """

        try:
            # Voltage needs to be scaled to ~-10-10V (+-10V = NI DAQ max output(?))
            ao_voltage = self.scale_value("hvo", ao_voltage)
            self.__ao_task.write(ao_voltage)  # Set the voltage
            logging.info("Voltage set to the analog output channel")
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Failed to write analog output voltage")

    def scale_value(self, name: str, volt: float) -> float:
        """
        Converts value from an undesired unit(voltage) to a desired unit(E.g. L/min)
        Parameter key must be sensor's "name" from the ini file. E.g. rh

        Return the scaled value
        """

        section = "NI_DAQ:Scaling"
        try:
            # y = m*x + b
            x = volt
            x1 = float(self.__conf.read(section, f"{name}_v_min"))
            x2 = float(self.__conf.read(section, f"{name}_v_max"))
            y1 = float(self.__conf.read(section, f"{name}_value_min"))
            y2 = float(self.__conf.read(section, f"{name}_value_max"))
            m = (y1 - y2) / (x1 - x2)
            b = (x1 * y2 - x2 * y1) / (x1 - x2)

            scaled_value = m * x + b

        except ValueError as e:
            logging.error(e)
            logging.debug(f"Failed to scale {name} value")
            scaled_value = None

        return scaled_value

    def set_do(self, do_task: nidaqmx.Task, state: bool) -> None:
        """
        TODO: Make static?
        Set the given digital output task to the given state (True/False)
        """
        try:
            do_task.write(state)
            logging.info(f"Changed {do_task.name} state to {state}")
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug(f"Failed to write {do_task} state")

    def update_settings(self) -> None:
        """
        Update settings conf dicts from the ini file and restart tasks with the new values
        """

        # Update confs
        self.__conf.update_configuration(self.__nidaq_conf, "NI_DAQ")
        self.__conf.update_configuration(self.__scaling_conf, "NI_DAQ:Scaling")

        # Update tasks
        self.close_tasks()
        try:
            self.__ai_task = self.__create_ai_task()  # Analog input task
            self.__ao_task = self.__create_ao_task()  # Analog output task

            # Get line numbers and create tasks for the valves
            conc_line = self.__nidaq_conf.get("conc_line_chan")
            bypass_line = self.__nidaq_conf.get("bypass_line_chan")
            self.conc_valve_task = self.__create_do_task(conc_line)  # Task to control total concentration valve
            self.bypass_valve_task = self.__create_do_task(bypass_line)  # Task to control sample flow bypass valve

            self.__counter_task = self.__create_counter_task()
            self.__pulse_task = self.__create_pulse_task()
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug("Failed to update NIDAQ tasks")

        logging.info("Updated NIDAQ configuration")
