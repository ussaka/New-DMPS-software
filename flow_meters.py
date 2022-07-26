# This file is intended to provide functionality for TSI 4000 (and 5000) series flow meters
# TODO: Create FlowMeter5000 class

import typing  # Used for providing tuple type hint
import serial
import logging


class FlowMeter4000:
    """
    This class is used for reading data from TSI flow meter 4000 series

    The constructor(__init__) automatically opens the serial connection, remember to close it!
    """

    def __init__(self, ini_updater: object) -> None:  # TODO: Improve typehints
        # Initialize
        self.ser_connection = serial.Serial()  # Serial connection object
        self.ini_updater = ini_updater  # Object for reading and updating ini file

        # Set serial object settings
        self.update_serial_settings()
        # Create multiplier and offset instance variables
        self.spans_and_offsets()

        logging.info("Created FlowMeter4000 object")

    def update_serial_settings(self) -> None:
        """Updates serial port settings from the ini file (and creates the instance variables)"""

        # Close the connection
        if self.ser_connection.isOpen():
            self.ser_connection.close()

        # Update serial settings with values from the ini file
        serial_port_section = "Flow_Meter:Serial_port"
        try:
            # Str
            self.ser_connection.port = self.ini_updater[serial_port_section]["port"].value
            self.ser_connection.parity = self.ini_updater[serial_port_section]["parity"].value
            # Str -> int
            self.ser_connection.baudrate = int(
                self.ini_updater[serial_port_section]["baudrate"].value)
            self.ser_connection.bytesize = int(
                self.ini_updater[serial_port_section]["bytesize"].value)
            self.ser_connection.stopbits = int(
                self.ini_updater[serial_port_section]["stopbits"].value)
            self.ser_connection.timeout = int(
                self.ini_updater[serial_port_section]["timeout"].value)
            self.ser_connection.xonxoff = int(
                self.ini_updater[serial_port_section]["xonxoff"].value)
            self.ser_connection.rtscts = int(
                self.ini_updater[serial_port_section]["rtscts"].value)
        except ValueError as e:
            logging.error(e)
            logging.debug(
                "Flow meter's serial port settings are incorrect!")

        # Try to open the serial port
        # This test passes if the port exists but is not the right one!
        try:
            self.ser_connection.open()
            logging.info(
                "Opened serial connection to the flow meter. Remember to close this connection after it is no longer used!")
        except serial.SerialException as e:
            logging.error(e)  # Log any errors to the log file
            logging.debug(
                "Flow meter's serial port settings are probably set wrong")

        logging.info(
            "Updated FlowMeter4000 object's serial settings (port, etc.)")

    def spans_and_offsets(self) -> None:
        """Updates spans and offsets for the ftp values from the ini file (first time used creates the instance variables)"""

        scaling_section = "Flow_Meter:Scaling"

        # Value from ini needs to be converted to float
        self.f_multiplier = float(
            self.ini_updater[scaling_section]["f_multiplier"].value)
        self.f_offset = float(
            self.ini_updater[scaling_section]["f_offset"].value)

        self.t_multiplier = float(
            self.ini_updater[scaling_section]["t_multiplier"].value)
        self.t_offset = float(
            self.ini_updater[scaling_section]["t_offset"].value)

        self.p_multiplier = float(
            self.ini_updater[scaling_section]["p_multiplier"].value)
        self.p_offset = float(
            self.ini_updater[scaling_section]["p_offset"].value)

        logging.info(
            "Updated FlowMeter4000 object's multiplier and offset values")

    def read_ftp(self) -> typing.Tuple[float, float, float]:
        """Read flow [L/min], temperature [°C] and pressure [kPa] from the flow meter and return them"""

        if self.ser_connection.isOpen():
            encoding = "UTF-8"  # TODO: Maybe it would be better to use ASCII?
            new_line = "\n".encode(encoding)  # Str to utf-8

            # Request one sample of flow rate, temperature and pressure
            str_out = "DAFTP0001\r".encode(encoding)  # Str to utf-8
            self.ser_connection.write(str_out)  # Send the command

            # Read OK or ERR from the TSI
            # BUG: If the serial settings are wrong program can get stuck on this step
            str_in = self.ser_connection.read_until(new_line)
            str_in = str_in.decode(encoding)  # ASCII(bytes) to str
            str_in = str_in.strip()  # Remove whitespace

            # Check that the command worked successfully, handle things if not
            if str_in != "OK":
                logging.error(
                    "Error! Flow meter's measurements can not be read!")
                # Log the error code if the flow meter gave one
                if (len(str_in) != 0):
                    logging.debug(str_in)  # Log error code, if it is available
                logging.debug("Is the flow meter's port set correctly?")
                flow, temp, pressure = None, None, None

            elif str_in == "OK":
                # Read flow(L/min), temp(°C) and pressure(kPa)
                str_in = self.ser_connection.read_until(new_line)
                str_in = str_in.decode(encoding)  # ASCII(bytes) to str
                str_in = str_in.strip()  # Remove whitespace
                # Split str_in by comma to a list
                str_splitted = str_in.split(",")

                # It can happen that the flow meter doesn't measure all the values
                if len(str_splitted) == 3:
                    flow = float(str_splitted[0]) * \
                        self.f_multiplier + self.f_offset
                    temp = float(str_splitted[1]) * \
                        self.t_multiplier + self.t_offset
                    pressure = float(str_splitted[2]) * \
                        self.p_multiplier + self.p_offset
                else:
                    flow, temp, pressure = None, None, None

            return flow, temp, pressure

        else:
            logging.debug("Flow meter's serial port is not open!")
            flow, temp, pressure = None, None, None
            return flow, temp, pressure
