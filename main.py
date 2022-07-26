# This file is used to start the DMPS program's GUI

# The idea for using main file is the ability to change what classes are used to create object variables
# The program could be modified easily(hopefully) to work with different dmps, smps, etc configurations
# E.g. create different tsi_flow object variable from flow_meter.FlowMeter5000() class

# TODO: In all files methods, functions and variable visibility should be considered by changing name from x to __x when appropriate

import logging
from multiprocessing import Lock
from configupdater import ConfigUpdater
import queue

import gui
from flow_meters import FlowMeter4000
import ni_daqs
import blower_pid
import automatic_measurement
import detectors


# Create config updater object
# Used for reading and writing to config.ini file
config_updater = ConfigUpdater()

# Set logging settings
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s",
                    datefmt="%d.%m.%Y %H:%M:%S", filename="debug/debug.log", filemode="w")

# Read the ini file
config_updater.read("config.ini")

# Create flow meter object
flow_meter_4000 = FlowMeter4000(config_updater)

# Create NI DAQ object
daq = ni_daqs.NiDaq(config_updater)

# Create CPC object
cpc_3750 = detectors.CpcLegacy(config_updater)

# Queue used by blower_thread to put flow meter ftp values and dmps_measure_thread to get those values
# Th Queue only holds one sample and updates it constantly by consuming(get) it and putting a new one in the queue if no other thread tries to get it
flow_meter_queue = queue.Queue(maxsize=1)

# When lock is acquired any other thread that tries to acquire lock waits until first thread to acquire it releases it
# Used for E.g. prevent trying to read flow meters ftp value and changing it's serial settings at the same time
lock = Lock()

# Create blower pid control thread object
blower_thread = blower_pid.BlowerPidThread(
    config_updater, daq, flow_meter_4000, flow_meter_queue, lock)

# Create dmps automatic measurement thread
dmps_measure_thread = automatic_measurement.AutomaticMeasurementThread(
    config_updater, daq, flow_meter_4000, cpc_3750, blower_thread, flow_meter_queue)

# Create Gui object
gui = gui.MainWindow(config_updater, daq, flow_meter_4000,
                     cpc_3750, blower_thread, dmps_measure_thread, flow_meter_queue, lock)


# This executes the program
if __name__ == "__main__":  # Means that code is executed only if this file is run directly and not imported
    logging.info("Program started")

    blower_thread.start()  # Start blower PID thread
    # Start the automatic measurement thread, thread won't start to loop because self.stop is set to None
    dmps_measure_thread.start()
    gui.mainloop()  # Start TKinter loop for the gui

    blower_thread.stop = True  # After GUI window is closed set blower thread to stop
    blower_thread.join()  # Wait for thread to terminate

    # After GUI window is closed set measurement thread to stop
    dmps_measure_thread.run_measure = False
    dmps_measure_thread.join()  # Wait for thread to terminate

    logging.info("Closed the GUI")
