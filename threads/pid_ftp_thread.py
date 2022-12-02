"""
This file provides separate thread for running pid control on the blower
"""

import logging
import queue
import typing  # Used for providing tuple type hint
from multiprocessing import Lock
from threading import Thread

import nidaqmx
from simple_pid import PID

import config
import flow_meters
import ni_daqs


class BlowerPidThread(Thread):
    """
    Measures flow, temp and pressure from the flow meter and controls blower with pid to reach the target flow
    """

    def __init__(self, conf: config.Config, daq: ni_daqs.NiDaq, flow_meter: flow_meters.FlowMeter4000,
                 ftp_queue: queue.Queue, flow_meter_lock: Lock, daq_lock: Lock, target_flow: float = 5) -> None:
        Thread.__init__(self)  # Call Thread constructor

        self.__pid_conf = conf.get_configuration("Pid")
        self.__daq = daq
        self.__flow_meter = flow_meter
        self.__ftp_queue = ftp_queue  # Put values read from the flow meter to this queue
        self.__fw_lock = flow_meter_lock  # Used for waiting while serial settings are changed in the maintenance mode
        self.__daq_lock = daq_lock
        self.stop = False  # If set to True this thread's run loop stops

        frequency, sample_time, p, i, d = self.__read_pid_settings()  # Read settings from the dict
        self.__frequency = frequency
        self.__pid = PID(p, i, d, setpoint=target_flow, sample_time=sample_time)  # Create PID object
        logging.info("Created BlowerPidThread")

    def __read_pid_settings(self) -> typing.Tuple[float, float, float, float, float]:
        """
        Read PID values from the conf dict and return them
        """

        frequency = float(self.__pid_conf.get("frequency"))
        sample_time = float(self.__pid_conf.get("sample_time"))
        p = float(self.__pid_conf.get("p"))
        i = float(self.__pid_conf.get("i"))
        d = float(self.__pid_conf.get("d"))

        return frequency, sample_time, p, i, d

    def set_target_flow(self, flow: float) -> None:
        """
        Set target flow to the pid
        """

        self.__pid.auto_mode = False  # Pause updating pid control
        self.__pid.setpoint = flow  # Set PID target flow
        self.__pid.auto_mode = True  # Continue updating pid control

    def update_pid_settings(self, target_flow: float, sample_time: float, p: float, i: float,
                            d: float, frequency: float) -> None:
        """
        Update PID settings
        """

        self.__pid.auto_mode = False  # Pause updating pid control
        self.__pid.setpoint = target_flow
        self.__pid.sample_time = sample_time
        self.__pid.tunings = (p, i, d)
        self.__frequency = frequency
        self.__pid.auto_mode = True  # Continue updating pid control

    def run(self):
        """
        Measure flow, temperature and pressure from the flow meter. Only flow is used for controlling the blower.
        Update pid control and control blower with pid.
        """

        logging.info("Started measuring flow meter values and controlling blower with pid")
        control = 0  # Ensure that control is initialized to 0

        # Run until self.stop is set to True
        while not self.stop:
            # Ensures that flow meter's data is not tried to read at the same time that serial settings are changed
            self.__fw_lock.acquire()
            ftp = self.__flow_meter.read_ftp()  # Measure flow, temperature and pressure
            self.__fw_lock.release()

            # Put the ftp values to the queue to be shared with other threads
            if self.__ftp_queue.full():  # If queue of max size 1 is full consume value and update queue with a new one
                self.__ftp_queue.get_nowait()
                self.__ftp_queue.put_nowait(ftp)
            elif self.__ftp_queue.empty():  # If queue is empty put new ftp values there
                self.__ftp_queue.put_nowait(ftp)

            flow = ftp[0]  # Get flow from the ftp

            # Check that the flow can be read
            if flow is None:
                self.__pid.auto_mode = False  # Do not try to update the control value
                control = 0.0
                logging.warning("Flow is None, pid control is  temporarily disabled")
            elif flow is not None:
                # Compute new output from the PID according to the systems current flow
                self.__pid.auto_mode = True
                control = self.__pid(flow)

                # Ensure that NI DAQ counter writer can handle the control value
                if control > 999.995000e-3:
                    control = 999.995000e-3
                    logging.debug("Pid control value is over 0.95!")
                elif control < 5.0e-6:
                    control = 5.0e-6
                    logging.debug("Pid control value is under 0.05!")

            # Write pulse according to pid control and frequency
            # Timeout is set to default 10 -> 10s time to write the pulse
            self.__daq_lock.acquire()
            try:
                self.__daq.cw_writer.write_one_sample_pulse_frequency(
                    self.__frequency, control)
            except nidaqmx.DaqError as e:
                logging.error(e)
                logging.debug("Tried to use counter writer too often!")
            self.__daq_lock.release()

        logging.info("Ended BlowerPidThread")
