"""
Provides environment tab for the main window
"""

import queue
import tkinter as tk
from multiprocessing import Lock
from tkinter import ttk

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg)
from matplotlib.figure import Figure

import config
import ni_daqs
from threads import automatic_measurement


class EnvironmentTab(ttk.Frame):
    """
    Display the environment values in charts
    """

    def __init__(self, container, daq: ni_daqs,
                 automatic_measurement_thread: automatic_measurement.AutomaticMeasurementThread,
                 daq_ai_queue: queue.Queue, conf: config.Config, daq_lock: Lock) -> None:
        super().__init__(container)  # Inherit Frame class

        self.__daq = daq
        self.__daq_scaling_conf = conf.get_configuration("NI_DAQ_Scaling")
        self.__daq_ai_queue = daq_ai_queue
        self.__daq_lock = daq_lock

        self.__plt_fig = Figure(figsize=(8, 5), dpi=100)
        self.__axs = self.__plt_fig.subplots(2, 2)
        self.__plt_fig.subplots_adjust(wspace=0.5, hspace=0.5)

        self.__axs[0, 0].set_title("Temperature")
        self.__axs[0, 0].set_xlabel("Time [s]")
        self.__axs[0, 0].set_ylabel("Temperature [°C]")
        self.__axs[0, 0].grid()

        self.__axs[0, 1].set_title("Relative Humidity")
        self.__axs[0, 1].set_xlabel("Time [s]")
        self.__axs[0, 1].set_ylabel("Relative Humidity [%]")
        self.__axs[0, 1].grid()

        self.__axs[1, 0].set_title("Flow")
        self.__axs[1, 0].set_xlabel("Time [s]")
        self.__axs[1, 0].set_ylabel("Flow [l/min]")
        self.__axs[1, 0].grid()

        self.__axs[1, 1].set_title("Pressure")
        self.__axs[1, 1].set_xlabel("Time [s]")
        self.__axs[1, 1].set_ylabel("Pressure [Pa]")
        self.__axs[1, 1].grid()

        # Draw plot
        canvas = FigureCanvasTkAgg(self.__plt_fig, master=self)  # A tk.DrawingArea
        canvas.draw()
        canvas.get_tk_widget().grid(padx=10, pady=10)

        x_coord = []
        y1_coord = []
        y2_coord = []
        y3_coord = []
        y4_coord = []
        t = 0

        # Measure button
        measurement_btn = ttk.Button(
            self, text="Start",
            command=lambda: self.__automatic_measurement_start(automatic_measurement_thread, measurement_btn, canvas,
                                                               x_coord, y1_coord, y2_coord, y3_coord, y4_coord, t))
        measurement_btn.grid(row=1, column=0, sticky="w", padx=5, pady=5)

        # High voltage out entry
        hvo = tk.Entry(container, width=10)
        hvo.grid(row=1, column=4, sticky="w", padx=5, pady=5)
        hvo2 = tk.Entry(container, width=10)
        hvo2.grid(row=1, column=5, sticky="w", padx=5, pady=5)

    def __automatic_measurement_start(self, automatic_measurement_thread, measure_btn, canvas, x_coord,
                                      y1_coord, y2_coord, y3_coord, y4_coord, t) -> None:
        """
        Start automatic measurement thread
        """

        automatic_measurement_thread.started = True

        t += 0.5
        x_coord.append(t)

        volts = self.__daq_ai_queue.get() # ADD: Check whether the queue is empty or not
        self.__daq_lock.acquire()
        y1_coord.append(self.__daq.scale_value("t", volts[int(self.__daq_scaling_conf.get("t_chan"))]))
        y2_coord.append(self.__daq.scale_value("rh", volts[int(self.__daq_scaling_conf.get("rh_chan"))]))
        y3_coord.append(self.__daq.scale_value("f", volts[int(self.__daq_scaling_conf.get("f_chan"))]))
        y4_coord.append(self.__daq.scale_value("p", volts[int(self.__daq_scaling_conf.get("p_chan"))]))
        self.__daq_lock.release()

        self.__axs[0, 0].plot(x_coord, y1_coord, marker='.')

        self.__axs[0, 1].plot(x_coord, y2_coord, marker='.')
        # self.__axs[0, 1].grid()
        self.__axs[1, 0].plot(x_coord, y3_coord, marker='.')
        # self.__axs[1, 0].grid()
        self.__axs[1, 1].plot(x_coord, y4_coord, marker='.')
        # self.__axs[1, 1].grid()

        # Draw plot
        canvas.draw()
        canvas.get_tk_widget().grid(padx=10, pady=10)

        # Call this method every 1s
        # after_id is used to stop calling this method
        plot_after_id = self.after(1000,
                                   lambda: self.__automatic_measurement_start(automatic_measurement_thread, measure_btn,
                                                                              canvas, x_coord,
                                                                              y1_coord, y2_coord, y3_coord, y4_coord,
                                                                              t))
