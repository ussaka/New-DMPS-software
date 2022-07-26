# This file provides separate thread for running pid control on the blower

import typing  # Used for providing tuple type hint
import logging
from threading import Thread
from simple_pid import PID
import nidaqmx


class BlowerPidThread(Thread):
    """
    Thread for measuring values from the flow meter and updating pid values

    Measures current flow, temp and pressure from the flow meter and controls blower with pid to reach the target flow
    """

    # TODO: Improve type hints
    def __init__(self, ini_updater: object, daq: object, flow_meter: object, ftp_queue: object, lock: object) -> None:
        Thread.__init__(self)  # Inherit Thread constructor

        self.ini_updater = ini_updater  # Used to read/write the ini file
        self.daq = daq
        self.flow_meter = flow_meter
        # This queue is used to put values read from the flow meter to the queue
        self.ftp_queue = ftp_queue
        # Used to wait while flow meter's serial settings are changed in the maintenance mode
        self.lock = lock
        self.stop = False  # If set to True this thread's run loop stops

        # Read settings from the ini file
        target_flow, frequency, sample_time, p, i, d = self.read_pid_settings()

        self.target_flow = target_flow  # PID setpoint
        self.frequency = frequency  # Hz
        self.sample_time = sample_time  # PID update interval
        self.p = p
        self.i = i
        self.d = d

        self.pid = PID(self.p, self.i, self.d,
                       setpoint=self.target_flow, sample_time=self.sample_time)  # Create PID object

        logging.info("Created BlowerPidThread")

    def read_pid_settings(self) -> typing.Tuple[float, float, float, float, float, float]:
        """Read PID values from the ini file and return them"""

        items = self.ini_updater.items("Pid")

        # items[x][0] contains name of the saved value in the ini file.
        # items[x][1] contains thingies with name and value of the item in the ini file # TODO: Improve this comment
        # TODO: Change this to not rely on the order of keys in the ini list in order to assign correct value to correct variable
        target_flow = float(items[0][1].value)
        frequency = float(items[1][1].value)
        sample_time = float(items[2][1].value)
        p = float(items[3][1].value)
        i = float(items[4][1].value)
        d = float(items[5][1].value)

        logging.info("Read PID settings from the ini file")

        return target_flow, frequency, sample_time, p, i, d

    def run(self):
        """When thread is running measure flow from the flow meter, update pid control and control blower with pid"""

        logging.info("Started blower's PID control thread")

        # Run until self.stop is set to False
        while self.stop != True:
            # This lock ensures that flow meter's data is not tried to read at the same time that flow meter's serial settings are changed
            self.lock.acquire()
            ftp = self.flow_meter.read_ftp()  # Measure flow, temperature and pressure
            self.lock.release()

            # Put flow to the queue to be shared with other threads
            if self.ftp_queue.full():  # If queue of max size 1 is full consume value and update queue with a new one
                self.ftp_queue.get_nowait()
                self.ftp_queue.put_nowait(ftp)
            elif self.ftp_queue.empty():  # If queue is full put new flow value there
                self.ftp_queue.put_nowait(ftp)

            flow = ftp[0]  # Get flow from the ftp

            # Check that the flow can be read
            if flow == None:
                self.pid.auto_mode = False  # Do not try to update the control value
                control = 0.0
            elif flow != None:
                # Compute new output from the PID according to the systems current flow
                self.pid.auto_mode = True
                control = self.pid(flow)
                # At some point the control value could be too great or small and NI DAQ counter writer can not handle that
                # So we change control to the value that the daq can handle
                # TODO: Get rid of the magic numbers. Find better way to handle this
                if control > 0.95:
                    control = 0.95
                    logging.debug("Pid control value is over 0.95!")
                elif control < 0.05:
                    control = 0.05
                    logging.debug("Pid control value is under 0.05!")

            # Write pulse according to pid control and frequency
            # Timeout is set to default 10 -> 10s time to write the pulse
            try:
                self.daq.counter_writer.write_one_sample_pulse_frequency(
                    self.frequency, control)
            except nidaqmx.DaqError as e:
                logging.error(e)
                logging.debug("Tried to use counter writer too often!")

        self.flow_meter.ser_connection.close()
        logging.info("Ended blower's PID control thread")
