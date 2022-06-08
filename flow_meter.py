# TODO: Make it work with 5000 series also
# TODO: Load serial settings from somewhere, json? --> default parameter values for __init__ from there
# TODO: Log errors somewhere, file? instead of printing them
# TODO: Read temp and pressure also from the TSI?

import serial

# This class is used for reading data from TSI flow meter


class FlowMeter:
    def __init__(self, port: str = "COM2", baud_rate: int = 38400, bytesize: int = 8, parity=serial.PARITY_NONE, stopbits: int = 1, timeout: int = 1, xon: int = 0, rts: int = 0) -> None:
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baud_rate
        self.ser.bytesize = bytesize
        self.ser.parity = parity
        self.ser.stopbits = stopbits
        self.ser.timeout = timeout
        self.ser.xonxoff = xon  # Software flow control
        self.ser.rtscts = rts  # Hardware flow control

    # Read flow
    def read_flow(self) -> float:
        encoding = "UTF-8"
        # Check that COM port can be opened
        try:
            self.ser.open()
        except:
            print("Error! Serial port can not be opened!")
            exit()

        if self.ser.isOpen():
            new_line = '\n'.encode(encoding)  # Str to utf-8
            # Request one sample of flow rate
            str_out = "DAFxx0001\r".encode(encoding)

            self.ser.write(str_out)  # Send the command
            # Read OK or ERR from the TSI
            str_in = self.ser.read_until(new_line)
            str_in = str_in.decode(encoding)  # ASCII(bytes) to str
            str_in = str_in.strip()  # Remove whitespace

            # Check that the command worked succesfully
            if str_in != "OK":
                print("Error! Flow rate can not be read!")
                print("Error code:", str_in)
                exit()

            str_in = self.ser.read_until(new_line)  # Read flow rate (L/min)
            flow = float(str_in)  # Convert ascii to float

            self.ser.close
            return flow


# This code is for testing purposes only and
# is only executed if this module is run as main
if __name__ == "__main__":
    tsi_4000 = FlowMeter()
    print(tsi_4000.read_flow())
