# This file contains class for dmps automatic measurement thread
# This file also could contain other classes for other type of measurement modes

from threading import Thread
import typing  # Used for providing tuple type hint
import numpy
from time import sleep
from time import time
import logging
from datetime import datetime
from pytz import timezone


class AutomaticMeasurementThread(Thread):
    """Thread uses dmps's devices to automatically measure particle concentration on specified particle sizes"""

    def __init__(self, ini_updater: object, daq: object, flow_meter: object, detector: object, blower_pid_thread: Thread, flow_meter_queue: object) -> None:  # TODO: Improve type hints
        Thread.__init__(self)  # Inherit Thread constructor
        self.name = "Automatic measurement thread"  # Change thread's name

        # Initialize
        self.ini_updater = ini_updater
        self.daq = daq
        self.flow_meter = flow_meter
        self.detector = detector
        self.blower_pid_thread = blower_pid_thread
        self.queue = flow_meter_queue

        self.run_measure = None  # Used to stop the run(measurement) loop
        self.gas_temp_0 = 293.0  # Unit is K, used in calc_x methods

        # Create lists of particle diameters, used in measurements
        # It is possible to generate more lists by adding parameters ->
        # to the ini file and generating here a new list and assigning it to a instance variable
        # E.g. Add content to the ini file(copy how it was done in Dma section) and add below line: ->
        # self.medium_particle_diameters = self.gen_particle_diameters_list("medium")
        self.small_particle_diameters = self.gen_particle_diameters_list(
            "small")
        self.large_particle_diameters = self.gen_particle_diameters_list(
            "large")

        logging.info("Created AutomaticMeasurementThread object")

    def gen_particle_diameters_list(self, particle_size: str) -> list:
        """
        Return list of particle diameters with desired interval between diameters

        You must give parameter from the ini file(E.g. small or large) depending on what kind of list you want
        """

        self.ini_updater.read("config.ini")  # Read settings from the ini file

        p_d_min = float(
            self.ini_updater["Dma"][f"{particle_size}_p_diameter_min"].value)
        p_d_max = float(
            self.ini_updater["Dma"][f"{particle_size}_p_diameter_max"].value)
        p_d_list_size = int(
            self.ini_updater["Dma"][f"number_of_{particle_size}_p"].value)

        # Use log and then **10 to get list of diameters at correct interval
        particle_diameter_list = numpy.linspace(
            numpy.log10(p_d_min), numpy.log10(p_d_max), p_d_list_size)
        particle_diameter_list = numpy.power(10, particle_diameter_list)

        logging.info(f"Generated {particle_size} particle diameters list")

        return particle_diameter_list

    def calc_dyn_gas_visc(self, gas_temp: float) -> float:
        """Returns dynamic gas viscosity at gas_temp_0 and 1013.25 hPa"""

        n0 = 1.83245e-5  # Unit is kg/ms
        gas_temp = gas_temp + 273.15  # Convert °C to K

        # \ doesn't do anything(well it does something...), it just allows to split long line to multiple short ones
        # / Is a division sign
        dynamic_gas_visc = n0 * \
            ((gas_temp/self.gas_temp_0)**(3.0/2.0)) * \
            ((self.gas_temp_0+110.4) / (gas_temp+110.4))

        return dynamic_gas_visc

    def calc_p_mean_free_path(self, gas_pressure: float, gas_temp: float) -> float:
        """Returns particle's mean free path at gas_temp_0 and 1013.25 hPa"""

        mean_free_path_0 = 67.3e-9  # Unit is m
        gas_pressure_0 = 101325.0
        gas_pressure = gas_pressure * 1000.0  # kPa to Pa
        gas_temp = gas_temp + 273.15  # °C to K

        particle_mean_free_path = mean_free_path_0 * ((gas_temp/self.gas_temp_0)**2.0) * (
            gas_pressure_0/gas_pressure) * ((self.gas_temp_0+110.4) / (gas_temp+110.4))

        return particle_mean_free_path

    def gen_cunningham_corrected_list(self, particle_mean_free_path: float, particle_diameters_list: list) -> list:
        """Generates list of particle diameters with cunningham correction"""

        particle_cunningham_correction_list = 1.0 + numpy.divide(2.0*particle_mean_free_path, particle_diameters_list) * (
            1.165+0.483 * numpy.exp(-0.997 * numpy.divide(particle_diameters_list, 2.0*particle_mean_free_path)))

        return particle_cunningham_correction_list

    def gen_p_mobility_list(self, particle_cunningham_correction: list, dynamic_gas_visc: float, particle_diameters_list: list) -> list:
        """Return list of particle motion values"""

        particle_mobility_list = numpy.divide(numpy.multiply(
            1.602E-19, particle_cunningham_correction), numpy.multiply(3.0*numpy.pi*dynamic_gas_visc, particle_diameters_list))

        return particle_mobility_list

    def gen_dma_voltages_list(self, particle_mobility: list, dma_sheath_flow: float) -> list:
        """
        Returns list of dma voltages corresponding to desired particle diameters

        Needs particle mobility list and dma sheath flow (l/min) as parameters
        """
        # Read values from the ini file
        length = float(self.ini_updater["Dma"]["length"].value)
        electrode_inner_d = float(
            self.ini_updater["Dma"]["inner_electrode_radius"].value)
        electrode_outer_d = float(
            self.ini_updater["Dma"]["outer_electrode_radius"].value)

        # Convert to cm**3/s
        dma_sheath_flow = dma_sheath_flow/1000.0/60.0

        dma_voltages_list = numpy.multiply(numpy.divide(
            dma_sheath_flow/2.0/numpy.pi/length, particle_mobility), numpy.log(electrode_outer_d/electrode_inner_d))

        return dma_voltages_list

    def get_time(self, time_zone: str, time_format: str) -> typing.Tuple[str, str]:
        """Get utc and local time. Return them formatted"""

        # Current time in UTC
        utc_time = datetime.now(timezone("UTC"))
        # Convert to the time zone
        local_time = utc_time.astimezone(timezone(time_zone))

        # Format the times
        utc_str = utc_time.strftime(time_format)
        local_str = local_time.strftime(time_format)

        return utc_str, local_str

    def run(self):
        """When the thread is started measure cpc concentration with various methods until self.stop is set to False"""

        logging.info(f"Started the {self.name}")

        # Wait times
        pulse_count_time = 5.0  # Time to count cpc's pulses
        # Waiting time after one measurement cycle -> wait time between solenoid valve state changes (sec)
        cycle_wait_time = 5.0

        between_voltages_wait = 7.0  # Time waited after voltage change

        loop_index = 0  # Used to determine what parameters should be used for this measurement cycle

        # Check every 5s is the self.stop set to True, False or None
        # If it is True run the measurement loop
        # Else if it's False end the thread
        while self.run_measure != False:
            sleep(cycle_wait_time)  # Waiting time after one measurement cycle
            while self.run_measure == True:
                # Set the solenoid valve's state for this cycle

                # Small particles
                if loop_index == 0:
                    self.daq.set_do(self.daq.conc_valve_task,
                                    False)  # Dma concentration
                    self.daq.set_do(self.daq.bypass_valve_task,
                                    False)  # High flow
                    dma_sheath_flow = 20.0  # Used in dma voltage calculations. Unit is L/min

                    self.blower_pid_thread.pid.auto_mode = False  # Pause updating pid control
                    self.blower_pid_thread.pid.setpoint = 20.0  # Set PID target flow
                    self.blower_pid_thread.pid.auto_mode = True  # Continue updating pid control
                    p_d_list = self.small_particle_diameters

                    loop_index += 1

                # Large particles
                elif loop_index == 1:
                    self.daq.set_do(self.daq.conc_valve_task,
                                    False)  # Dma concentration
                    self.daq.set_do(self.daq.bypass_valve_task,
                                    True)  # Low flow
                    dma_sheath_flow = 5.0  # Used in dma voltage calculations. Unit is L/min

                    self.blower_pid_thread.pid.auto_mode = False  # Pause updating pid control
                    self.blower_pid_thread.pid.setpoint = 5.0  # Set PID target flow
                    self.blower_pid_thread.pid.auto_mode = True  # Continue updating pid control
                    p_d_list = self.large_particle_diameters

                    loop_index += 1

                # Total concentration
                # TODO: Add other cpc measurements
                elif loop_index == 2:  # TODO: No need to loop dma voltages
                    sleep(5.0)
                    self.daq.set_do(self.daq.conc_valve_task,
                                    True)  # Total conc
                    self.daq.set_do(self.daq.bypass_valve_task,
                                    True)  # Low flow, does not really matter(?)

                    rd = self.detector.read_rd()  # Get average total concentration (1s)
                    # TODO: Add all three methods of measuring concentration
                    print()
                    print(f"Total concentration: {rd}")
                    print()
                    loop_index = 0
                    sleep(5.0)
                    continue

                # Get current utc and local time
                time_utc, time_local = self.get_time(
                    "Europe/Helsinki", "%Y-%m-%d %H:%M:%S %Z%z")
                file_time_utc, file_time_local = self.get_time(
                    "Europe/Helsinki", "%Y%m%d")

                # Create a new data file for each day
                file_name = f"DMPS-4_{file_time_local}.scan"
                file = open(f"data/{file_name}", "a")

                # Read flow, temp and pressure from the queue
                # The queue is updated by blower pid thread
                flow_meter_flow, flow_meter_temp, flow_meter_pressure = self.queue.get()  # Read the queue

                # Do the calculations in order to get list of dma voltages
                particle_mean_free_path = self.calc_p_mean_free_path(
                    flow_meter_pressure, flow_meter_temp)

                cunningham_correction_list = self.gen_cunningham_corrected_list(
                    particle_mean_free_path, p_d_list)

                dynamic_gas_viscosity = self.calc_dyn_gas_visc(flow_meter_temp)

                particle_mobility_list = self.gen_p_mobility_list(
                    cunningham_correction_list, dynamic_gas_viscosity, p_d_list)

                dma_voltages_list = self.gen_dma_voltages_list(
                    particle_mobility_list, dma_sheath_flow)

                # Get daq flow
                self.daq.measure_ai()
                daq_flow = self.daq.scale_value("f")

                # Write to the file
                if loop_index == 0:
                    file.write(
                        f"{time_local}    {flow_meter_temp + 273.15:.3f} {flow_meter_pressure:.3f} {daq_flow:.3f} {flow_meter_flow:.3f}    ")
                    for p_size in self.small_particle_diameters:
                        file.write(f"{p_size * 1e9} ")
                    file.write("\n")

                elif loop_index == 1:
                    file.write(
                        f"{time_local}    {flow_meter_temp + 273.15:.3f} {flow_meter_pressure:.3f} {daq_flow:.3f} {flow_meter_flow:.3f}    ")
                    for p_size in self.large_particle_diameters:
                        file.write(f"{p_size * 1e9} ")
                    file.write("\n")

                # Record start time
                start_time = time()  # TODO: More precise counter?, use this for something?

                file.write(
                    f"{time_local}    {flow_meter_temp + 273.15:.3f} {flow_meter_pressure:.3f} {daq_flow:.3f} {flow_meter_flow:.3f}    ")

                # Loop through voltages
                for voltage in dma_voltages_list:
                    self.daq.set_ao(voltage)  # Set HV voltage
                    # Wait time between voltage changes
                    sleep(between_voltages_wait)

                    # Read flow, temp and pressure from the queue
                    # The queue is updated by blower pid thread
                    flow_meter_flow, flow_meter_temp, flow_meter_pressure = self.queue.get()  # Read the queue

                    # Start counting the cpc's pulses
                    conc_d = self.detector.read_d()  # Reset cpc's counter
                    self.daq.counter_task.stop()  # Reset daq's counter
                    self.daq.counter_task.start()
                    # TODO: More precise counter?
                    pulse_count_start_time = time()  # Record zero point for pulse count time

                    # Count the cpc's pulses for some time
                    sleep(pulse_count_time)

                    # Read counts recorded by the Cpc, return counts per second
                    conc_d = self.detector.read_d()
                    # Read Cpc's counts measured by the daq
                    daq_counts = self.daq.counter_task.read()

                    # Calculate how long pulses were counted by the daq
                    time_pulses_counted = time() - pulse_count_start_time  # TODO: More precise counter?

                    # Read analog input HV voltage from daq
                    self.daq.measure_ai()
                    self.ini_updater.read("config.ini")
                    hv_in = float(
                        self.ini_updater["NI_DAQ:Sensors"]["hvi_voltage"].value)

                    # Calculate concentration in different ways
                    cpc_conc = float(daq_counts) / \
                        self.detector.flow / time_pulses_counted

                    rd = self.detector.read_rd()  # Get average total concentration (1s)
                    cpc_conc_s = rd / self.detector.flow_c

                    cpc_conc_d = conc_d / self.detector.flow_d

                    # Write to the file
                    file.write(
                        f"{hv_in} {voltage}    {cpc_conc:.3f} {cpc_conc_d:.3f} {cpc_conc_s:.3f} ")

                # Set the hv voltage to zero
                self.daq.set_ao(0.0)
                file.write("\n")
                file.close()

        # Close all serial connections and daq tasks
        self.daq.set_ao(0.0)
        self.daq.counter_task.close()
        self.daq.pulse_task.close()
        self.daq.ai_task.close()
        self.daq.ao_task.close()
        self.conc_valve_task.close()
        self.bypass_valve_task.close()
        self.daq.pulse_task.close()
        self.daq.counter_task.close()
        self.detector.ser_connection.close()
        logging.info(f"Ended the {self.name}")
