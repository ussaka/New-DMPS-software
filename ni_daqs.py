# This file provides functionality for National Instruments data acquisition devices (6211 and 6215)

import nidaqmx
from nidaqmx.constants import AcquisitionType
from nidaqmx.stream_writers import CounterWriter
import logging


class NiDaq:
    """This class is used for reading and writing data to NI DAQ. It is tested to work with NI6211"""

    def __init__(self, ini_updater: object) -> None:  # TODO: Improve typehints
        self.ini_updater = ini_updater  # Used to access the ini file

        self.update_daq_settings()  # Create the instance variables

        # Create ai task
        # ai_min_name must be ai[number] string and ai_max_number must be only a number string
        self.ai_task = self.create_ai_task(
            self.ai_min, self.ai_max, -10.0, 10.0)
        # Create ao task
        self.ao_task = self.create_ao_task()

        # Create conc line task
        self.conc_valve_task = self.create_do_task(self.conc_chan)
        # Create bypass line task
        self.bypass_valve_task = self.create_do_task(self.bypass_chan)

        # Create counter task
        self.counter_task = self.create_counter_task()
        self.counter_task.start()

        # Create pulse task
        self.pulse_task = self.create_pulse_task()
        self.pulse_task.start()
        # Create Object that can tell pulse_task what kind of pulses to generate
        self.counter_writer = CounterWriter(self.pulse_task.out_stream, True)

        logging.info("Created NiDaq object")

    def update_daq_settings(self) -> None:
        """Read ini file and create/update daq instance variables"""

        ini_section = "NI_DAQ"

        # Read settings from the config.ini
        self.device_id = self.ini_updater[ini_section]["device_id"].value
        # Min ai channel
        self.ai_min = self.ini_updater[ini_section]["ai_min"].value
        # Max ai channel
        self.ai_max = self.ini_updater[ini_section]["ai_max"].value
        # High voltage output
        self.hvo_chan = self.ini_updater[ini_section]["hv_output_chan"].value
        # Pulse generator channel for the blower
        self.blower_pulse_chan = self.ini_updater[ini_section]["blower_pulse_chan"].value
        # Pulse edge counter channel for the Cpc
        self.cpc_pulse_chan = self.ini_updater[ini_section]["cpc_counter_chan"].value
        # Input for counter counting cpc pulses
        self.cpc_signal_chan = self.ini_updater[ini_section]["cpc_signal"].value
        # Digital I/O channel
        self.port_chan = self.ini_updater[ini_section]["port_chan"].value
        # Total concentration valve
        self.conc_chan = self.ini_updater[ini_section]["conc_line"].value
        # Bypass valve
        self.bypass_chan = self.ini_updater[ini_section]["bypass_line"].value

    def update_tasks_settings(self) -> None:
        """Close existing tasks and recreate them with new settings"""

        # Close the existing tasks
        self.ai_task.close()
        self.ao_task.close()
        self.conc_valve_task.close()
        self.bypass_valve_task.close()
        self.counter_task.close()
        self.pulse_task.close()

        # Recreate tasks with the new settings
        # Create ai task
        # ai_min_name must be ai[number] string and ai_max_number must be only a number string
        self.ai_task = self.create_ai_task(
            self.ai_min, self.ai_max, -10.0, 10.0)
        # Create ao task
        self.ao_task = self.create_ao_task()

        # Create conc line task
        self.conc_valve_task = self.create_do_task(self.conc_chan)
        # Create bypass line task
        self.bypass_valve_task = self.create_do_task(self.bypass_chan)

        # Create counter task
        self.counter_task = self.create_counter_task()
        self.counter_task.start()

        # Create pulse task
        self.pulse_task = self.create_pulse_task()
        self.pulse_task.start()
        # Create Object that can tell pulse_task what kind of pulses to generate
        self.counter_writer = CounterWriter(self.pulse_task.out_stream, True)

    def create_ai_task(self, ai_min_name: str, ai_max_number: str, min_v: float, max_v: float) -> nidaqmx.Task:
        """
        Create ai task to read analog input voltages

        Remember to close this task after it is not used anymore!
        """

        # Analog input task
        ai_task = nidaqmx.Task(new_task_name="ai_task")  # Create the task
        ai_str = f"{self.device_id}/{ai_min_name}:{ai_max_number}"
        try:
            # Set channels that are measured and set min and max voltages that are read
            ai_task.ai_channels.add_ai_voltage_chan(
                ai_str, min_val=min_v, max_val=max_v)
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug(
                "Device id or ai channel settings are probably wrong")
            ai_task.close()

        logging.info("Created ai task")
        return ai_task

    def create_ao_task(self) -> nidaqmx.Task:
        """
        Create ao task to read analog output voltage. Uses self.hvo_chan as channel name

        Remember to close this task after it is not used anymore!
        """

        # Analog output task
        ao_task = nidaqmx.Task(new_task_name="ao_task")
        ao_str = f"{self.device_id}/{self.hvo_chan}"
        try:
            ao_task.ao_channels.add_ao_voltage_chan(ao_str)
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug(
                "Device id or ao channel settings are probably wrong")
            ao_task.close()

        logging.info("Created ao task")
        return ao_task

    def create_do_task(self, line) -> nidaqmx.Task:
        """
        Create do task to read and write digital out

        Remember to close this task after it is not used anymore!
        """

        do_task = nidaqmx.Task(
            new_task_name=f"do_task_{line}")  # Create the task
        do_str = f"{self.device_id}/{self.port_chan}/{line}"
        try:
            do_task.do_channels.add_do_chan(do_str)
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug(
                "Device id or DO channel settings are probably wrong")
            do_task.close()

        logging.info(f"Created do task with {line}")
        return do_task

    def create_counter_task(self) -> nidaqmx.Task:
        """
        Create counter task to count cpc's pulses

        Remember to close this task after it is not used anymore!
        """

        # Create counter task
        counter_task = nidaqmx.Task(new_task_name="counter_task")
        counter_str = f"{self.device_id}/{self.cpc_pulse_chan}"
        try:
            counter_task.ci_channels.add_ci_count_edges_chan(counter_str)

            # Select what (virtual?)channel to count
            # Use this if the default is wrong
            counter_task.ci_channels[0].ci_count_edges_term = f"/{self.device_id}/{self.cpc_signal_chan}"

        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug(
                "Device id or counter channel settings are probably wrong")
            counter_task.close()

        logging.info("Created counter task")
        return counter_task

    def create_pulse_task(self) -> nidaqmx.Task:
        """
        Create task that can generate pulses that control the blower with pid. Return's pulse task object

        Remember to close this task after it is not used anymore!
        """

        # Create the task
        pulse_task = nidaqmx.Task(new_task_name="pulse_task")
        pulse_str = f"{self.device_id}/{self.blower_pulse_chan}"
        try:
            pulse_task.co_channels.add_co_pulse_chan_time(pulse_str)
            # Generate infinite amount of pulses
            pulse_task.timing.cfg_implicit_timing(
                sample_mode=AcquisitionType.CONTINUOUS)
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug(
                "Device id or counter channel settings are probably wrong")
            pulse_task.close()

        logging.info("Created pulse task")
        return pulse_task

    def measure_ai(self) -> None:  # TODO: Change to save voltages list to a queue
        """Reads analog input signals (voltages) from the DAQ"""

        try:
            voltages = self.ai_task.read()  # Get AI voltages
        except nidaqmx.DaqError as e:
            logging.error(e)
            logging.debug(
                "Ai task was probably closed too soon")

        # Variable sensors contains all keys of the NI_DAQ:Sensors section
        sensors = self.ini_updater.items("NI_DAQ:Sensors")

        # Update the ini file with the measured voltages
        # TODO: This loop is ineffective and too complicated(?). E.g. After p_chan is found the loop still continues with p_voltage, p_value_min, etc...
        # sensor contains (key name, key) tuple
        for sensor in sensors:
            # +1 because otherwise range is ai_max - 1
            for i in range(int(self.ai_max) + 1):
                # Check if the channel name matches
                # Use .value to get key's value
                if sensor[1].value == f"ai{i}":
                    # Get sensors "name" E.g. rh
                    splitted_str = sensor[0].split("_")
                    # Name of the key that data will be saved on
                    sensor_str = f"{splitted_str[0]}_voltage"
                    # Voltages are ordered so that voltages[0] is ai0's voltage
                    voltage = voltages[i]
                    self.ini_updater["NI_DAQ:Sensors"][sensor_str] = voltage
                    break  # After value is updated there is no reason to try to find correct channel for this sensor anymore

        self.ini_updater.update_file()  # Save voltages to the config.ini
        logging.info("Read successfully all the DAQ analog input channels")

    def set_ao(self, voltage: float) -> None:
        """Writes to the AO. Output value given as parameter in volts"""

        # Update the ini with hv out value
        self.ini_updater["NI_DAQ:Sensors"]["hvo_voltage"].value = voltage
        self.ini_updater.update_file()

        # Voltage need to be scaled to ~-10-10V (+-10V = NI DAQ max output(?))
        voltage = self.scale_value("hvo")

        self.ao_task.write(voltage)  # Set the voltage

        logging.info("Wrote voltage to the analog output channel")

    def set_do(self, do_task: nidaqmx.Task, state: bool) -> bool:  # TODO: Return None?
        """
        Set given task to the given state (True/False)

        You can check the line's current status with self.[digital out task].read()
        Return what was valve's state before calling this method
        """

        do_state_before = do_task.read()  # Read state before the change
        do_task.write(state)

        logging.info(f"Changed {do_task} state to {do_state_before}")
        return do_state_before

    def scale_value(self, name: str) -> float:
        """
        Converts value from an undesired unit(voltage) to a desired unit(E.g. L/min). 

        Parameter must be sensor's "name" from the ini file. E.g. rh.

        Return scaled value
        """

        self.ini_updater.read("config.ini")  # Update the ini file

        # y = m*x + b
        x = float(self.ini_updater["NI_DAQ:Sensors"][f"{name}_voltage"].value)
        x1 = float(self.ini_updater["NI_DAQ:Sensors"][f"{name}_v_min"].value)
        x2 = float(self.ini_updater["NI_DAQ:Sensors"][f"{name}_v_max"].value)
        y1 = float(self.ini_updater["NI_DAQ:Sensors"]
                   [f"{name}_value_min"].value)
        y2 = float(self.ini_updater["NI_DAQ:Sensors"]
                   [f"{name}_value_max"].value)
        m = (y1-y2) / (x1-x2)
        b = (x1*y2 - x2*y1) / (x1-x2)

        scaled_value = m*x + b

        return scaled_value
