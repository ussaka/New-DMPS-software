"""
Thread for accessing values from the Cpc
"""

import logging
import queue
from multiprocessing import Lock
from threading import Thread

import detectors


class DetectorThead(Thread):
    """
    Measure AI voltages from the daq and put them to a queue
    """

    def __init__(self, detector: detectors.CpcLegacy, detector_queue: queue.Queue, detector_lock: Lock) -> None:
        Thread.__init__(self)  # Call Thread constructor

        self.__detector = detector
        self.__detector_queue = detector_queue
        self.__detector_lock = detector_lock
        self.stop = False  # If set to True this thread's run loop stops

        logging.info("Created DetectorThread")

    def run(self) -> None:
        """
        Measure RD reading from the cpc and put it to a queue
        """

        logging.info("Started DetectorThread")

        while not self.stop:
            self.__detector_lock.acquire()
            rd = self.__detector.read_rd()
            self.__detector_lock.release()

            if self.__detector_queue.full():  # If queue of max size 1 is full consume and update queue with a new one
                self.__detector_queue.get_nowait()
                self.__detector_queue.put_nowait(rd)
            elif self.__detector_queue.empty():  # If queue is empty put new values there
                self.__detector_queue.put_nowait(rd)

        logging.info("Stopped DetectorThread")
