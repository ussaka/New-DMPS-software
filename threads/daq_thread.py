"""
Thread for accessing values from the DAQ
"""

import logging
import queue
from multiprocessing import Lock
from threading import Thread

import ni_daqs


class DaqThread(Thread):
    """
    Measure AI voltages from the daq and put them to a queue
    """

    def __init__(self, daq: ni_daqs.NiDaq, daq_ai_queue: queue.Queue, daq_lock: Lock) -> None:
        Thread.__init__(self)  # Call Thread constructor

        self.__daq = daq
        self.__ai_queue = daq_ai_queue
        self.__daq_lock = daq_lock
        self.stop = False  # If set to True this thread's run loop stops

        logging.info("Created DaqThread")

    def run(self) -> None:
        """
        Measure AI voltages from the daq and put them to a queue
        """

        logging.info("Started DaqThread")

        while not self.stop:
            self.__daq_lock.acquire()  # Wait until the daq is not in use
            voltages = self.__daq.measure_ai()
            self.__daq_lock.release()

            if self.__ai_queue.full():  # If queue of max size 1 is full consume value and update queue with a new one
                self.__ai_queue.get_nowait()
                self.__ai_queue.put_nowait(voltages)
            elif self.__ai_queue.empty():  # If queue is empty put new values there
                self.__ai_queue.put_nowait(voltages)

        logging.info("Stopped DaqThread")
