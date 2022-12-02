"""
Contains class for dmps automatic measurement thread
This file could also contain other classes for other type of measurement modes

TODO: Refactor repetitive code
"""

import logging
import queue
import typing  # Used for providing tuple type hint
from datetime import datetime
from multiprocessing import Lock
from threading import Thread
from time import sleep
from time import time

import numpy
from pytz import timezone

import config
import detectors
import flow_meters
import ni_daqs
from threads import pid_ftp_thread


class AutomaticMeasurementThread(Thread):
    """
    Thread uses DMPS's devices to automatically measure particle concentration on specified particle sizes
    """

    def __init__(self, conf: config.Config, daq: ni_daqs.NiDaq, flow_meter: flow_meters.FlowMeter4000,
                 detector: detectors.CpcLegacy, blower_pid_thread: pid_ftp_thread.BlowerPidThread,
                 flow_meter_queue: queue.Queue, voltage_queue: queue.Queue, conc_queue: queue.Queue,
                 daq_ai_queue: queue.Queue, detector_lock: Lock, daq_lock: Lock) -> None:
        Thread.__init__(self)  # Call Thread constructor

        # Initialize
        self.__conf = conf
        self.__dma_conf = self.__conf.get_configuration("Dma")
        self.__auto_measurement_conf = self.__conf.get_configuration("Automatic_measurement")
        self.__daq_conf = self.__conf.get_configuration("NI_DAQ")
        self.__daq_scaling_conf = self.__conf.get_configuration("NI_DAQ_Scaling")
        self.__daq = daq
        self.__flow_meter = flow_meter
        self.__detector = detector
        self.__blower_pid_thread = blower_pid_thread
        self.__flow_queue = flow_meter_queue
        self.__volt_queue = voltage_queue
        self.__conc_queue = conc_queue
        self.__daq_ai_queue = daq_ai_queue
        self.__detector_lock = detector_lock
        self.__daq_lock = daq_lock
        self.__gas_temp_0 = 293.0  # Unit is K, used in calc_x methods

        self.stop = False  # Used to stop the thead
        self.reset_plot = False  # TODO: Remove?
        self.started = False

        # Create lists of particle diameters, used in the measurements
        # It is possible to generate more lists by adding parameters to the ini file and
        # config.py and generating here a new list and assigning it to an instance variable

        # E.g. Add content to:
        # - the ini file(copy how it was done in Dma section),
        # - config.py (new conf to __init__ and get_configuration method)
        # - and add below line: self.__medium_particle_diameters = self.gen_particle_diameters_list("medium")
        self.__s_particle_d_list = self.__gen_particle_diameters_list("small")
        self.__l_particle_d_list = self.__gen_particle_diameters_list("large")

        logging.info("Created AutomaticMeasurementThread object")

    def __gen_particle_diameters_list(self, particle_size: str) -> list:
        """
        Return list of particle diameters with desired interval between diameters

        You must give parameter from the ini file(E.g. small or large) depending on what kind of list you want
        """

        p_d_min = float(self.__dma_conf.get(f"{particle_size}_p_d_min"))
        p_d_max = float(self.__dma_conf.get(f"{particle_size}_p_d_max"))
        p_d_list_size = int(self.__dma_conf.get(f"number_of_{particle_size}_p"))

        # Use log and then **10 to get list of diameters at correct interval
        particle_diameter_list = numpy.linspace(numpy.log10(p_d_min), numpy.log10(p_d_max), p_d_list_size)
        particle_diameter_list = numpy.power(10, particle_diameter_list)

        logging.info(f"Generated {particle_size} particle diameters list")

        return particle_diameter_list

    def __calc_p_mean_free_path(self, gas_pressure: float, gas_temp: float) -> float:
        """
        Return particle's mean free path at gas_temp_0 and 1013.25 hPa
        """

        mean_free_path_0 = 67.3e-9  # Unit is m
        gas_pressure_0 = 101325.0
        gas_pressure = gas_pressure * 1000.0  # kPa to Pa
        gas_temp = gas_temp + 273.15  # °C to K

        particle_mean_free_path = mean_free_path_0 * ((gas_temp / self.__gas_temp_0) ** 2.0) * (
                gas_pressure_0 / gas_pressure) * ((self.__gas_temp_0 + 110.4) / (gas_temp + 110.4))

        return particle_mean_free_path

    def __gen_cunningham_corrected_list(self, p_mean_free_path: float, p_d_list: list) -> list:
        """
        TODO: Make static?
        Generates list of particle diameters with cunningham correction
        """

        p_cunn_corr_list = 1.0 + numpy.divide(2.0 * p_mean_free_path, p_d_list) * (
                1.165 + 0.483 * numpy.exp(-0.997 * numpy.divide(p_d_list, 2.0 * p_mean_free_path)))

        return p_cunn_corr_list

    def __calc_dyn_gas_visc(self, gas_temp: float) -> float:
        """
        Return dynamic gas viscosity at gas_temp_0 and 1013.25 hPa
        """

        n0 = 1.83245e-5  # Unit is kg/ms
        gas_temp = gas_temp + 273.15  # Convert °C to K

        dynamic_gas_visc = n0 * ((gas_temp / self.__gas_temp_0) ** (3.0 / 2.0)) * (
                (self.__gas_temp_0 + 110.4) / (gas_temp + 110.4))

        return dynamic_gas_visc

    def __gen_p_mobility_list(self, particle_cunningham_correction: list, dynamic_gas_visc: float,
                              particle_diameters_list: list) -> list:
        """
        TODO: Make static?
        Return list of particle motion values
        """

        particle_mobility_list = numpy.divide(numpy.multiply(1.602E-19, particle_cunningham_correction),
                                              numpy.multiply(3.0 * numpy.pi * dynamic_gas_visc,
                                                             particle_diameters_list))

        return particle_mobility_list

    def __gen_dma_voltages_list(self, dma_sheath_flow: float, flow_meter_pressure: float,
                                flow_meter_temp: float, particle_d_list: list) -> list:
        """
        Return list of dma voltages corresponding to desired particle diameters
        """

        particle_mean_free_path = self.__calc_p_mean_free_path(flow_meter_pressure, flow_meter_temp)
        cunningham_correction_list = self.__gen_cunningham_corrected_list(particle_mean_free_path, particle_d_list)
        dynamic_gas_viscosity = self.__calc_dyn_gas_visc(flow_meter_temp)
        particle_mobility_list = self.__gen_p_mobility_list(cunningham_correction_list, dynamic_gas_viscosity,
                                                            particle_d_list)
        # Convert to cm**3/s
        dma_sheath_flow = dma_sheath_flow / 1000.0 / 60.0

        # Read values from the ini file
        length = float(self.__dma_conf.get("length"))
        in_electrode_r = float(self.__dma_conf.get("in_electrode_r"))
        out_electrode_r = float(self.__dma_conf.get("out_electrode_r"))

        dma_voltages_list = numpy.multiply(
            numpy.divide(dma_sheath_flow / 2.0 / numpy.pi / length, particle_mobility_list),
            numpy.log(out_electrode_r / in_electrode_r))

        return dma_voltages_list

    def __get_time(self, time_zone: str, time_format: str) -> typing.Tuple[str, str]:
        """
        TODO: Make static?
        Get utc and local time
        Return them formatted
        """

        # Current time in UTC
        utc_time = datetime.now(timezone("UTC"))
        # Convert to the time zone
        local_time = utc_time.astimezone(timezone(time_zone))

        # Format the times
        utc_str = utc_time.strftime(time_format)
        local_str = local_time.strftime(time_format)

        return utc_str, local_str

    def __conc_measurement_loop(self, dma_voltages_list: list, file, particle_d_list: list) -> None:
        """
        Loop though list of dma voltages, set the voltages and measure concentration
        """

        # Time waited after voltage change (s)
        between_voltages_wait = float(self.__auto_measurement_conf.get("between_voltages_wait_t"))
        # Time to count cpc's pulses (s)
        pulse_count_time = float(self.__auto_measurement_conf.get("pulse_count_t"))

        # Loop through the voltages
        for index, voltage in enumerate(dma_voltages_list, start=0):
            self.__daq_lock.acquire()
            self.__daq.set_ao(voltage)  # Set HV voltage
            self.__daq_lock.release()

            # Wait the voltage to settle
            sleep(between_voltages_wait)

            # Read flow, temp and pressure from the flow queue
            # The queue is updated by blower pid thread
            flow_meter_flow, flow_meter_temp, flow_meter_pressure = self.__flow_queue.get()

            # Read AI voltages from the daq queue
            ai_voltages = self.__daq_ai_queue.get()  # List index = channel number
            # HV_in
            chan = int(self.__daq_scaling_conf.get("hvi_chan"))  # channel number
            hv_in_v = ai_voltages[chan]
            # Flow
            chan = int(self.__daq_scaling_conf.get("f_chan"))  # channel number
            daq_flow = self.__daq.scale_value("f", ai_voltages[chan])

            # Start counting by cpc and daq
            self.__detector_lock.acquire()
            self.__detector.read_d()  # Reset cpc's counter
            self.__detector_lock.release()

            self.__daq_lock.acquire()
            self.__daq.rst_ctr_task()  # Reset daq's counter
            self.__daq_lock.release()

            pulse_count_start_time = time()  # Record zero point for pulse count time
            sleep(pulse_count_time)  # Count the cpc's pulses for pulse_count_time

            # Read the counts
            self.__detector_lock.acquire()
            cpc_counts = self.__detector.read_d()  # Read counts recorded by the Cpc (counts per second)
            self.__detector_lock.release()

            self.__daq_lock.acquire()
            daq_counts = self.__daq.read_ctr_task()  # Read Cpc's counts measured by the daq
            self.__daq_lock.release()

            # Calculate how long counted
            counts_counted_t = time() - pulse_count_start_time

            # Calculate concentration in different ways
            cpc_conc = daq_counts / float(self.__auto_measurement_conf.get("flow")) / counts_counted_t
            self.__detector_lock.acquire()
            cpc_conc_s = self.__detector.read_rd() / float(self.__auto_measurement_conf.get("flow_c"))
            self.__detector_lock.release()
            cpc_conc_d = cpc_counts / float(self.__auto_measurement_conf.get("flow_d"))

            # Send data to queue to be plotted by GUI
            self.__volt_queue.put_nowait(voltage)
            self.__conc_queue.put_nowait(cpc_conc)

            # Get current utc and local time
            time_utc, time_local = self.__get_time("Europe/Helsinki", "%Y-%m-%d %H:%M:%S %Z%z")

            # Write to the file
            file.write(
                f"{time_local}    {flow_meter_temp:.3f}    {flow_meter_pressure:.3f}    {daq_flow:.3f}    {flow_meter_flow:.3f}    {particle_d_list[index] * 1e9:.3f}    {hv_in_v:.3f}    {voltage:.3f}    {cpc_conc:.3f}    {cpc_conc_d:.3f}    {cpc_conc_s:.3f}")
            file.write("\n")
            # Print TODO: Send to the gui
            print(
                f"{time_local}    {flow_meter_temp:.3f}    {flow_meter_pressure:.3f}    {daq_flow:.3f}    {flow_meter_flow:.3f}    {particle_d_list[index] * 1e9:.3f}    {hv_in_v:.3f}    {voltage:.3f}    {cpc_conc:.3f}    {cpc_conc_d:.3f}    {cpc_conc_s:.3f}")

            # If true, the thread must be stopped so exit the loop
            if self.stop:
                break

    def run(self):
        """
        When the thread is started measure cpc concentration with various methods until self.stop is set to False
        """

        logging.info(f"Started the automatic measurement thread")
        # Waiting time after one measurement loop (s)
        cycle_wait_time = float(self.__auto_measurement_conf.get("cycle_wait_t"))

        # Ensure that run method is in infinite loop until self.stop is set to True (and self.started is True)
        while not self.started and not self.stop:
            sleep(1)

        while not self.stop and self.started:
            # Create a new data file for each day
            file_time_utc, file_time_local = self.__get_time("Europe/Helsinki", "%Y%m%d")
            file = open(f"data/DMPS-4_{file_time_local}.scan", "a")

            ###########################
            # Measure small particles #
            ###########################
            dma_sheath_flow = 20.0  # Used in dma voltage list calculations. Unit is L/min
            self.__daq_lock.acquire()
            self.__daq.set_do(self.__daq.conc_valve_task, False)  # Dma concentration
            self.__daq.set_do(self.__daq.bypass_valve_task, False)  # High flow
            self.__daq_lock.release()

            self.__blower_pid_thread.set_target_flow(dma_sheath_flow)

            tsi_flow, tsi_temp, tsi_pressure = self.__flow_queue.get()  # Updated by blower pid thread
            dma_voltages = self.__gen_dma_voltages_list(dma_sheath_flow, tsi_pressure, tsi_temp,
                                                        self.__s_particle_d_list)

            # Print header
            print(
                "Time                             Temp      P          Daq_f    Tsi_f     P_size   HV_in   HV_out     "
                "conc    conc_d    conc_s")

            # Set voltages and measure concentration
            self.__conc_measurement_loop(dma_voltages, file, self.__s_particle_d_list)

            # Set HV to zero
            self.__daq_lock.acquire()
            self.__daq.set_ao(0.0)
            self.__daq_lock.release()

            # file.write("\n")
            sleep(cycle_wait_time)  # Waiting time after one particle list measurement loop (s)
            self.reset_plot = True  # TODO: OK?

            ###########################
            # Measure large particles #
            ###########################
            dma_sheath_flow = 5.0  # Used in dma voltage list calculations. Unit is L/min
            self.__daq_lock.acquire()
            self.__daq.set_do(self.__daq.conc_valve_task, False)  # Dma concentration
            self.__daq.set_do(self.__daq.bypass_valve_task, True)  # Low flow
            self.__daq_lock.release()

            self.__blower_pid_thread.set_target_flow(dma_sheath_flow)

            tsi_flow, tsi_temp, tsi_pressure = self.__flow_queue.get()  # updated by blower pid thread
            dma_voltages = self.__gen_dma_voltages_list(dma_sheath_flow, tsi_pressure, tsi_temp,
                                                        self.__l_particle_d_list)

            # Print header
            print(
                "Time                             Temp      P          Daq_f    Tsi_f     P_size   HV_in   HV_out     "
                "conc    conc_d    conc_s")

            # Set voltages and measure conc. Print and write to the file
            self.__conc_measurement_loop(dma_voltages, file, self.__l_particle_d_list)

            # Set HV to zero
            self.__daq_lock.acquire()
            self.__daq.set_ao(0.0)
            self.__daq_lock.release()

            # file.write("\n")
            sleep(cycle_wait_time)  # Waiting time after one measurement loop (s)
            self.reset_plot = True  # TODO: OK?

            ###############################
            # Measure Total concentration #
            ###############################
            pulse_count_time = float(
                self.__auto_measurement_conf.get("pulse_count_t"))  # Time to count cpc's pulses (s)

            self.__daq_lock.acquire()
            self.__daq.set_do(self.__daq.conc_valve_task, True)  # Total conc
            self.__daq.set_do(self.__daq.bypass_valve_task, True)  # Low flow, does not really matter(?)
            self.__daq_lock.release()

            # Start counting by cpc and daq
            self.__detector_lock.acquire()
            self.__detector.read_d()  # Reset cpc's counter
            self.__detector_lock.release()

            self.__daq_lock.acquire()
            self.__daq.rst_ctr_task()  # Reset daq's counter
            self.__daq_lock.release()

            pulse_count_start_time = time()  # Record zero point for pulse count time
            sleep(pulse_count_time)  # Count the cpc's pulses for pulse_count_time

            # Read the counts
            self.__detector_lock.acquire()
            cpc_counts = self.__detector.read_d()  # Read counts recorded by the Cpc (counts per second)
            self.__detector_lock.release()

            self.__daq_lock.acquire()
            daq_counts = self.__daq.read_ctr_task()  # Read Cpc's counts measured by the daq
            self.__daq_lock.release()

            # Calculate how long counted
            counts_counted_t = time() - pulse_count_start_time

            # Calculate concentration in different ways
            cpc_conc = daq_counts / float(self.__auto_measurement_conf.get("flow")) / counts_counted_t
            self.__detector_lock.acquire()
            cpc_conc_s = self.__detector.read_rd() / float(self.__auto_measurement_conf.get("flow_c"))
            self.__detector_lock.release()
            cpc_conc_d = cpc_counts / float(self.__auto_measurement_conf.get("flow_d"))

            self.reset_plot = True  # TODO: OK?

            file.close()

        self.__daq.set_ao(0.0)
        logging.info(f"Ended the Automatic measurement thread")
