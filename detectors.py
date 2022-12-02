"""
This file is intended to implement classes for various detectors
Currently it only works with CPC detectors that can use legacy commands
"""

import logging

import serial

import config


class CpcLegacy:
    """
    Used to read data from the CPC. Works at least with TSI models 375x/3789. Tested to work with TSI CPC 3750.

    This class uses TSI legacy commands that are used with a serial port connection
    """

    def __init__(self, conf: config.Config) -> None:
        self.__ser_connection = serial.Serial()  # Serial connection object
        self.__conf = conf
        self.__configuration = self.__conf.get_configuration("Cpc")  # Dict containing serial settings

        self.__set_serial_settings()  # Set serial settings and open the connection
        logging.info("Created a CpcLegacy object")

    def close_ser_connection(self) -> None:
        """
        Close the serial connection
        """

        if self.__ser_connection.isOpen():
            self.__ser_connection.close()
            logging.info("Closed the Cpc's serial connection")

    def __set_serial_settings(self) -> None:
        """
        Set serial settings
        """

        self.close_ser_connection()  # Close the serial connection if it is open

        # Set serial settings with values from the configuration dict
        try:
            # String values
            self.__ser_connection.port = self.__configuration.get("port")
            self.__ser_connection.parity = self.__configuration.get("parity")
            # String -> int
            self.__ser_connection.baudrate = int(self.__configuration.get("baudrate"))
            self.__ser_connection.bytesize = int(self.__configuration.get("bytesize"))
            self.__ser_connection.stopbits = int(self.__configuration.get("stopbits"))
            self.__ser_connection.timeout = int(self.__configuration.get("timeout"))
            self.__ser_connection.xonxoff = int(self.__configuration.get("xonxoff"))
            self.__ser_connection.rtscts = int(self.__configuration.get("rtscts"))
        except ValueError as e:
            logging.error(e)
            logging.debug("Cpc's serial port settings are wrong")

        # Try to open the serial port
        # This test passes if the port exists but is not the right one!
        try:
            self.__ser_connection.open()
            logging.info("Set serial settings and opened connection to the cpc")
        except serial.SerialException as e:
            logging.error(e)
            logging.debug("Cpc's serial port settings are probably set wrong")

    def update_settings(self) -> None:
        """
        Update serial settings
        """

        # Update the conf dict
        self.__conf.update_configuration(self.__configuration, "Cpc:Serial_port")
        self.__set_serial_settings()  # Restart ser connection with the new settings

    def read_rd(self) -> float:
        """
        Return 1s average concentration in p/cm^3
        """

        rd = None  # Ensure that rd is defined

        if self.__ser_connection.isOpen():
            encoding = "UTF-8"
            carriage_return = "\r".encode(encoding)  # Str to UTF-8
            str_out = "RD\r".encode(encoding)

            # Request 1s average of the concentration
            self.__ser_connection.write(str_out)
            # Read the line
            conc_line = self.__ser_connection.read_until(
                carriage_return)  # Read until \r is encountered

            # Try to decode the line and handle event if it can't be decoded
            try:
                conc_line = conc_line.decode(encoding)  # UTF-8 to str
                conc_line = conc_line.strip()  # Remove any possible whitespace
            except Exception as e:
                logging.error(e)
                logging.debug(f"Can't decode line: {conc_line}")
                conc_line = None

            # Try to convert line to float and handle event if it can't be converted
            try:
                rd = float(conc_line)  # Convert to float
            except ValueError as e:
                logging.error(e)
                logging.debug("Read_rd method returned invalid value")
                logging.debug("Double check Cpc's serial port settings")
        else:
            logging.debug("Can't read from the cpc because the serial connection is closed")

        return rd

    def read_d(self) -> float:
        """
        Read dead accumulative time (s) and accumulative counts since last time this method was used
        In other words used to get Cpc's counts and time counted since last time this method was used

        After reading two useful lines outputted by this command (time and counts) there is still a bunch of
        junk lines ("0,0") left to be read and that must be handled in order for the dmps program to work

        Return counts per second
        """

        time = None  # Ensure that time is defined
        counts = None  # Ensure that counts is defined
        out = None  # Ensure that out is defined

        if self.__ser_connection.isOpen():
            encoding = "UTF-8"
            carriage_return = "\r".encode(encoding)  # Str to UTF-8
            str_out = "D\r".encode(encoding)

            # Request accumulative time and counts
            self.__ser_connection.write(str_out)

            # Get time
            time_line = self.__ser_connection.read_until(
                carriage_return)  # Read until \r is encountered

            # Try to decode the line and handle event if it can't be decoded
            try:
                time_line = time_line.decode(encoding)  # UTF-8 to str
                time_line = time_line.strip()  # Remove any possible whitespace
            except Exception as e:
                logging.error(e)
                logging.debug(f"Can't decode line: {time_line}")

            # Try to convert line to float and handle event if it can't be converted
            try:
                time = float(time_line)  # Convert to float
            except ValueError as e:
                logging.error(e)
                logging.debug("read_d method read invalid time value")

            # Get counts
            # Returns line with 'counts, 0' I'm not sure what the zero stands for
            counts_line = self.__ser_connection.read_until(
                carriage_return)

            # Try to decode the line and handle event if it can't be decoded
            try:
                counts_line = counts_line.decode(encoding)  # UTF-8 to str
                counts_line = counts_line.strip()  # Remove any possible whitespace
                count_line_split_list = counts_line.split(
                    ",")  # Let's discard that zero in our line
                counts = float(count_line_split_list[0])  # Convert to float
            except Exception as e:
                logging.error(e)
                logging.debug(f"Can't decode line: {counts_line}")

            # Ensure that time and counts are valid values for the division
            try:
                out = counts / time
            except ValueError and TypeError as e:
                logging.error(e)
                logging.debug("read_d method tried to return invalid out value")

            # Read all the remaining junk lines in the buffer
            # I tried to flush the buffer but with flush junk lines were not removed
            # Also read_all command did not solve this problem
            # TODO: Find a better way to handle this
            junk_line = self.__ser_connection.read_until(
                carriage_return)
            while len(junk_line) != 0:
                junk_line = self.__ser_connection.read_until(
                    carriage_return)
        else:
            logging.debug("Can't read from the cpc because the serial connection is closed")

        return out

    def read_rall(self) -> str:
        """
        Read Cpc's concentration, instrument errors, saturator temp, condenser temp, ambient pressure,
        orifice pressure, nozzle pressure, laser current and liquid level

        TODO: When this function was tested it returned more values than the ones listed above

        Return a string with all the values separated by commas
        """

        data = None  # Ensure that data is defined

        if self.__ser_connection.isOpen():
            encoding = "UTF-8"
            carriage_return = "\r".encode(encoding)  # Str to UTF-8
            str_out = "RALL\r".encode(encoding)

            # Request the data
            self.__ser_connection.write(str_out)
            # Read the data
            data = self.__ser_connection.read_until(
                carriage_return)  # Read until \r is encountered

            # Try to decode the line and handle event if it can't be decoded
            try:
                data = data.decode(encoding)  # UTF-8 to str
                data = data.strip()  # Remove any possible whitespace
                logging.info(f"Read data: {data} with rall command")
            except Exception as e:
                logging.error(e)
                logging.debug(f"Can't decode data: {data}")
        else:
            logging.debug("Can't read from the cpc because the serial connection is closed")

        return data
