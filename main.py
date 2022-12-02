"""
Used to start the DMPS program.

The idea for using main file is the ability to change what classes are used to create objects.
This file could be easily modified(hopefully) to make the program work with different dmps, smps, etc. configurations.
E.g. Create flow_meter object with FlowMeter5000 class instead of FlowMeter4000 class.
"""

import logging
import queue
from multiprocessing import Lock

import config
import detectors
import flow_meters
import ni_daqs
from gui import main_window
from threads import pid_ftp_thread, automatic_measurement, daq_thread, detector_thead

# Set logging settings
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s",
                    datefmt="%d.%m.%Y %H:%M:%S", filename="debug/debug.log", filemode="w")

# Manages access to the config file and holds the config data
conf = config.Config()

# Create flow meter object
flow_meter_4000 = flow_meters.FlowMeter4000(conf)

# Create NI DAQ object
daq = ni_daqs.NiDaq(conf)

# Create CPC object
cpc_3750 = detectors.CpcLegacy(conf)

# Pid_ftp_thread outputs flow meter's ftp values to the queue. Dmps_measure_thread uses the queue to gets those values.
# The Queue only holds one sample. Pid_ftp_thread will overwrite the sample if it is consumed.
flow_meter_ftp_queue = queue.Queue(maxsize=1)

# AI voltages, constantly measured by daq thread
daq_ai_queue = queue.Queue(maxsize=1)

rd_queue = queue.Queue(maxsize=1)

# These queues are used to get data from automatic_measurement_thread to main_window.py
hv_voltage_queue = queue.Queue()
conc_queue = queue.Queue()

# When lock is acquired any other thread that tries to acquire lock waits until first thread to acquire it releases it.
# Used for E.g. Prevent trying to read flow meter's ftp value and changing its serial settings at the same time.
flow_meter_lock = Lock()  # Flow meter access lock
daq_lock = Lock()
detector_lock = Lock()

# Create pid thread to control the blower
blower_thread = pid_ftp_thread.BlowerPidThread(conf, daq, flow_meter_4000, flow_meter_ftp_queue, flow_meter_lock,
                                               daq_lock, 5)

# Create daq thread to measure AI voltages
daq_thread = daq_thread.DaqThread(daq, daq_ai_queue, daq_lock)

cpc_thread = detector_thead.DetectorThead(cpc_3750, rd_queue, detector_lock)

# Create dmps automatic measurement thread
dmps_measure_thread = automatic_measurement.AutomaticMeasurementThread(conf, daq, flow_meter_4000, cpc_3750,
                                                                       blower_thread, flow_meter_ftp_queue,
                                                                       hv_voltage_queue, conc_queue, daq_ai_queue,
                                                                       detector_lock, daq_lock)

# Create the GUI main window
gui = main_window.MainWindow(conf, daq, flow_meter_4000, cpc_3750, blower_thread, dmps_measure_thread,
                             flow_meter_ftp_queue, hv_voltage_queue, conc_queue, daq_ai_queue, rd_queue,
                             flow_meter_lock, daq_lock, detector_lock)

# Execute the program
if __name__ == "__main__":  # Means that code is executed only if this file is run directly and not imported
    logging.info("Program started")

    blower_thread.start()  # Start the blower thread
    daq_thread.start()  # Start the daq thread
    cpc_thread.start()
    dmps_measure_thread.start()  # Start the automatic measurement thread(doesn't start measuring automatically)
    gui.mainloop()  # Start TKinter loop for the gui

    # After GUI window is closed stop all the threads
    blower_thread.stop = True
    blower_thread.join()  # Wait for thread to terminate
    daq_thread.stop = True
    daq_thread.join()
    cpc_thread.stop = True
    cpc_thread.join()
    dmps_measure_thread.stop = True
    dmps_measure_thread.join()

    # Ensure that all tasks are closed
    daq.close_tasks()

    # Ensure that all serial connections are closed
    cpc_3750.close_ser_connection()
    flow_meter_4000.close_ser_connection()

    logging.info("Closed the GUI")
