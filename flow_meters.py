# TODO: Create FlowMeter5000 class
"""
Classes for TSI 4000 (and 5000) series flow meters
"""

import logging
import typing  # Used for providing tuple type hint

import serial

import config


class FlowMeter4000:
    """
    This class is used for reading data from TSI flow meter 4000 series
    The constructor automatically opens the serial connection, remember to close it!
    """

    def __init__(self, conf: config.Config) -> None:
        self.__ser_connection = serial.Serial()  # Serial connection object
        self.__conf = conf
        self.__ser_conf = self.__conf.get_configuration("Flow_Meter")  # Dict containing serial settings
        self.__scaling_conf = self.__conf.get_configuration("Flow_Meter_Scaling")

        self.__set_serial_settings()  # Set serial settings and open the connection
        logging.info("Created FlowMeter4000 object")

    def __set_serial_settings(self) -> None:
        """
        Set serial port connection settings and open the connection
        """

        # Ensure that connection is closed before changing settings
        self.close_ser_connection()

        # Set serial settings with values from the configuration dict
        try:
            # String values
            self.__ser_connection.port = self.__ser_conf.get("port")
            self.__ser_connection.parity = self.__ser_conf.get("parity")
            # String -> int
            self.__ser_connection.baudrate = int(self.__ser_conf.get("baudrate"))
            self.__ser_connection.bytesize = int(self.__ser_conf.get("bytesize"))
            self.__ser_connection.stopbits = int(self.__ser_conf.get("stopbits"))
            self.__ser_connection.timeout = int(self.__ser_conf.get("timeout"))
            self.__ser_connection.xonxoff = int(self.__ser_conf.get("xonxoff"))
            self.__ser_connection.rtscts = int(self.__ser_conf.get("rtscts"))
        except ValueError as e:
            logging.error(e)
            logging.debug("Flow meter's serial port settings are wrong")

        # Try to open the serial port
        # This test passes if the port exists but is not the right one!
        try:
            self.__ser_connection.open()
            logging.info("Set serial settings and opened connection to the flow meter")
        except serial.SerialException as e:
            logging.error(e)
            logging.debug("Flow meter's serial port settings are probably set wrong")

    def close_ser_connection(self) -> None:
        """
        If serial connection is open close it
        """

        if self.__ser_connection.isOpen():
            self.__ser_connection.close()
            logging.info("Closed the flow meter's serial connection")

    def update_settings(self) -> None:
        """
        Update serial settings
        """

        # Update the conf dict
        self.__conf.update_configuration(self.__ser_conf, "Flow_Meter:Serial_port")
        self.__set_serial_settings()  # Restart ser connection with the new settings

    def read_ftp(self) -> typing.Tuple[float, float, float]:
        """
        Read flow [L/min], temperature [°C] and pressure [kPa] from the flow meter and return them
        """

        flow, temp, pressure = None, None, None  # Initialize variables

        if self.__ser_connection.isOpen():
            encoding = "UTF-8"
            new_line = "\n".encode(encoding)  # Str to utf-8

            # Request one sample of flow rate, temperature and pressure
            str_out = "DAFTP0001\r".encode(encoding)  # Str to utf-8
            self.__ser_connection.write(str_out)  # Send the command

            # Read OK or ERR from the TSI
            # TODO: If the serial settings are wrong program can get stuck on this step
            str_in = self.__ser_connection.read_until(new_line)
            str_in = str_in.decode(encoding)  # ASCII(bytes) to str
            str_in = str_in.strip()  # Remove whitespace

            # Check that the command worked successfully, handle things if not
            if str_in != "OK":
                logging.error("Flow meter's measurements can not be read!")
                # Log the error code if the flow meter gave one
                if len(str_in) != 0:
                    logging.debug(str_in)
                logging.debug("The flow meter's serial port settings are probably set wrong")

            elif str_in == "OK":
                # Read flow(L/min), temp(°C) and pressure(kPa)
                str_in = self.__ser_connection.read_until(new_line)
                str_in = str_in.decode(encoding)  # ASCII(bytes) to str
                str_in = str_in.strip()  # Remove whitespace
                str_split = str_in.split(",")  # Split str_in by comma to a list

                # Ensure that flow meter measures all the three values
                if len(str_split) == 3:
                    flow = float(str_split[0]) * float(self.__scaling_conf.get("f_multiplier")) + float(
                        self.__scaling_conf.get("f_offset"))
                    temp = float(str_split[1]) * float(self.__scaling_conf.get("t_multiplier")) + float(
                        self.__scaling_conf.get("t_offset"))
                    pressure = float(str_split[2]) * float(self.__scaling_conf.get("p_multiplier")) + float(
                        self.__scaling_conf.get("p_offset"))
        else:
            logging.debug("Flow meter's serial port is not open!")

        return flow, temp, pressure
