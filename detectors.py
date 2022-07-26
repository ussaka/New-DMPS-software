# This file is intended to implement functionality(classes) for various detectors
# Currently it only works with a CPC detectors with legacy commands

import serial
import logging


class CpcLegacy:
    """
    Used to read data from the CPC. Works at least with TSI models 375x/3789. Tested to work with TSI CPC 3750

    This class uses TSI legacy commands that are used with a serial port connection.
    """

    def __init__(self, ini_updater: object) -> None:  # TODO: Improve type hints
        self.ini_updater = ini_updater
        self.ser_connection = serial.Serial()  # Serial connection object

        self.update_instance_variables()  # Create the instance variables

        logging.info("Created a CpcLegacy object")

    def update_instance_variables(self) -> None:
        """Update serial settings. Update/create the instance variables. Get values from the ini file."""

        # Close the connection
        if self.ser_connection.isOpen():
            self.ser_connection.close()

        # Update serial settings with values from the ini file
        section = "Cpc:Serial_port"
        try:
            # Str
            self.ser_connection.port = self.ini_updater[section]["port"].value
            self.ser_connection.parity = self.ini_updater[section]["parity"].value
            # Str -> Int
            self.ser_connection.baudrate = int(
                self.ini_updater[section]["baudrate"].value)
            self.ser_connection.bytesize = int(
                self.ini_updater[section]["bytesize"].value)
            self.ser_connection.stopbits = int(
                self.ini_updater[section]["stopbits"].value)
            self.ser_connection.timeout = int(
                self.ini_updater[section]["timeout"].value)
            self.ser_connection.xonxoff = int(
                self.ini_updater[section]["xonxoff"].value)
            self.ser_connection.rtscts = int(
                self.ini_updater[section]["rtscts"].value)
        except ValueError as e:
            logging.error(e)
            logging.debug(
                "Cpc's serial port settings are incorrect!")

        section = "Cpc:Concentration"
        self.flow = float(self.ini_updater[section]["flow"].value)
        self.flow_d = float(self.ini_updater[section]["flow_d"].value)
        self.flow_c = float(self.ini_updater[section]["flow_c"].value)

        # Try to open the serial port
        # This test passes if the port exists but is not the right one!
        try:
            self.ser_connection.open()
            logging.info(
                "Opened serial connection to the cpc. Remember to close this connection after it is no longer used!")
        except serial.SerialException as e:
            logging.error(e)  # Log any errors to the log file
            logging.debug(
                "Cpc's serial port settings are probably set wrong")

        logging.info(
            "Updated CpcLegacy object's serial settings and instance variables values from the ini file")

    def read_rd(self) -> float:
        """
        Read the concentration. Return 1s average concentration in p/cm**3

        Serial port needs to be open for this command to work
        """

        if self.ser_connection.isOpen():
            encoding = "UTF-8"  # Maybe it would be better to use ASCII?
            carriage_return = "\r".encode(encoding)  # Str to UTF-8
            str_out = "RD\r".encode(encoding)

            # Request 1s average of the concentration
            self.ser_connection.write(str_out)
            # Read the line
            conc_line = self.ser_connection.read_until(
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
                logging.debug("Read_rd method returned invalid value!")
                rd = None

            return(rd)

    def read_d(self) -> float:
        """
        Read dead accumulative time (s) and accumulative counts since last time this method was used. 
        In other words used to get Cpc's counts and time counted.

        After reading two useful lines outputted by this command (time and counts) there is still a bunch of
        junk lines ("0,0") left to be read and that must be handled in order for the dmps program to work.

        Return counts per second. Serial port needs to be open for this command to work
        """

        if self.ser_connection.isOpen():
            encoding = "UTF-8"  # Maybe it would be better to use ASCII?
            carriage_return = "\r".encode(encoding)  # Str to UTF-8
            str_out = "D\r".encode(encoding)

            # Request accumulative time and counts
            self.ser_connection.write(str_out)

            # Get time
            time_line = self.ser_connection.read_until(
                carriage_return)  # Read until \r is encountered

            # Try to decode the line and handle event if it can't be decoded
            try:
                time_line = time_line.decode(encoding)  # UTF-8 to str
                time_line = time_line.strip()  # Remove any possible whitespace
            except Exception as e:
                logging.error(e)
                logging.debug(f"Can't decode line: {time_line}")
                time_line = None

            # Try to convert line to float and handle event if it can't be converted
            try:
                time = float(time_line)  # Convert to float
            except ValueError as e:
                logging.error(e)
                logging.debug("read_rd method returned invalid value!")
                time = None

            # Get counts
            # Returns line with 'counts, 0' I'm not sure what the zero stands for
            counts_line = self.ser_connection.read_until(
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
                counts = None

            if time == 0:  # Handle the possibility that we try to divide with zero
                out = 0
            else:
                try:
                    out = counts / time
                except ValueError as e:
                    out = None
                    logging.error(e)
                    logging.debug(f"read_d method returned invalid value!")

            # HACK: Read all the remaining junk lines in the output buffer
            # I tried to reset the output buffer but with reset junk lines were not removed
            # Also read_all command did not solve this problem
            junk_line = self.ser_connection.read_until(
                carriage_return)
            while(len(junk_line) != 0):
                junk_line = self.ser_connection.read_until(
                    carriage_return)

            return(out)
