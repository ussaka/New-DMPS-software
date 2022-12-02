import queue
from tkinter import ttk

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg)
from matplotlib.figure import Figure

import config
from threads import automatic_measurement


class MeasurementTab(ttk.Frame):
    """
    Tab where you can start automatic measurement and plot the results
    """

    def __init__(self, container, conf: config.Config,
                 automatic_measurement_thread: automatic_measurement.AutomaticMeasurementThread,
                 voltage_queue: queue.Queue,
                 conc_queue: queue.Queue) -> None:
        super().__init__(container)  # Inherit Frame class

        self.__measurement_conf = conf.get_configuration("Automatic_measurement")
        self.__x_coord = []
        self.__y_coord = []
        self.__plt_fig = Figure(figsize=(7, 4), dpi=100)
        self.__ax = self.__plt_fig.add_subplot()
        self.__ax.grid()
        self.__ax.set_xlabel("Voltage [V]")
        self.__ax.set_ylabel("Concentration [1/cm^3]")

        # Draw plot
        canvas = FigureCanvasTkAgg(self.__plt_fig, master=self)  # A tk.DrawingArea
        canvas.draw()
        canvas.get_tk_widget().grid(padx=10, pady=10)

        # Measure button
        measurement_btn = ttk.Button(
            self, text="Start",
            command=lambda: self.__automatic_measurement_start(automatic_measurement_thread, measurement_btn,
                                                               voltage_queue, conc_queue, canvas))
        measurement_btn.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    def __automatic_measurement_start(self,
                                      automatic_measurement_thread: automatic_measurement.AutomaticMeasurementThread,
                                      measure_btn: ttk.Button, voltage_queue: queue.Queue, conc_queue: queue.Queue,
                                      canvas: FigureCanvasTkAgg) -> None:
        """
        Start automatic measurement thread and plot the results
        """

        automatic_measurement_thread.started = True  # Start the thread

        if automatic_measurement_thread.reset_plot:  # Clear the plot between particle sizes measurements
            self.__x_coord.clear()
            self.__y_coord.clear()
            self.__ax.cla()  # Clear the plot
            self.__ax.grid()
            self.__ax.set_xlabel("Voltage [V]")
            self.__ax.set_ylabel("Concentration [1/cm^3]")
            automatic_measurement_thread.reset_plot = False
        else:
            if voltage_queue.empty() or conc_queue.empty():
                pass
            else:
                # Plot the results
                self.__x_coord.append(voltage_queue.get())
                self.__y_coord.append(conc_queue.get())
                self.__ax.plot(self.__x_coord, self.__y_coord, marker="o")
            # Draw
            canvas.draw()
            canvas.get_tk_widget().grid(padx=10, pady=10)

        # Call this method every between_voltages_wait_t [s]
        wait_t = float(self.__measurement_conf["between_voltages_wait_t"]) * 1000  # Convert to ms
        # after_id is used to stop calling this method
        plot_after_id = self.after(
            int(wait_t), lambda: self.__automatic_measurement_start(automatic_measurement_thread, measure_btn, voltage_queue,
                                                               conc_queue, canvas))

        # Configure button to stop the measurement if it is clicked again
        measure_btn.configure(text="Stop", command=lambda: self.automatic_measurement_stop(
            automatic_measurement_thread, measure_btn, voltage_queue, conc_queue, canvas, plot_after_id))

    def automatic_measurement_stop(self, automatic_measurement_thread: automatic_measurement.AutomaticMeasurementThread,
                                   measure_btn: ttk.Button, voltage_queue: queue.Queue, conc_queue: queue.Queue,
                                   canvas: FigureCanvasTkAgg, plot_after_id) -> None:
        """
        Stop automatic measurement thread and stop plotting the results
        """

        # Stop the thread after current measurement loop is complete
        automatic_measurement_thread.stop = True
        automatic_measurement_thread.started = False

        # Configure button to stop the measurement if it is clicked again
        measure_btn.configure(text="Start", command=lambda: self.__automatic_measurement_start(
            automatic_measurement_thread, measure_btn, voltage_queue, conc_queue, canvas))

        # End the call loop
        self.after_cancel(plot_after_id)
