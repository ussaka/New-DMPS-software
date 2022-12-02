"""
Provides access to the configuration ini file
"""

import logging

from configupdater import ConfigUpdater


class Config:
    """
    This object provides access to the configurations. Read and write from/to config.ini file is also provided.
    Configuration values are saved to this object.
    """

    def __init__(self):
        self.__config_updater = ConfigUpdater()
        logging.info("Created Config object")

        try:
            self.__config_updater.read("config.ini")
        except FileNotFoundError as e:
            logging.error(e)
            logging.debug("config.ini file not found")

        self.__ni_daq_conf = {"device_id": self.read("NI_DAQ", "device_id"), "ai_min": self.read("NI_DAQ", "ai_min"),
                              "ai_max": self.read("NI_DAQ", "ai_max"), "ai_min_v": self.read("NI_DAQ", "ai_min_v"),
                              "ai_max_v": self.read("NI_DAQ", "ai_max_v"),
                              "blower_pulse_chan": self.read("NI_DAQ", "blower_pulse_chan"),
                              "cpc_counter_chan": self.read("NI_DAQ", "cpc_counter_chan"),
                              "cpc_pulses_chan": self.read("NI_DAQ", "cpc_pulses_chan"),
                              "port_chan": self.read("NI_DAQ", "port_chan"),
                              "conc_line_chan": self.read("NI_DAQ", "conc_line_chan"),
                              "bypass_line_chan": self.read("NI_DAQ", "bypass_line_chan")}

        self.__ni_daq_scaling = {"p_chan": self.read("NI_DAQ:Scaling", "p_chan"),
                                 "t_chan": self.read("NI_DAQ:Scaling", "t_chan"),
                                 "rh_chan": self.read("NI_DAQ:Scaling", "rh_chan"),
                                 "hvi_chan": self.read("NI_DAQ:Scaling", "hvi_chan"),
                                 "hvo_chan": self.read("NI_DAQ:Scaling", "hvo_chan"),
                                 "f_chan": self.read("NI_DAQ:Scaling", "f_chan")}

        self.__pid_conf = {"frequency": self.read("Pid", "frequency"), "sample_time": self.read("Pid", "sample_time"),
                           "p": self.read("Pid", "p"), "i": self.read("Pid", "i"), "d": self.read("Pid", "d")}

        self.__flow_meter_conf = {"port": self.read("Flow_Meter:Serial_port", "port"),
                                  "baudrate": self.read("Flow_Meter:Serial_port", "baudrate"),
                                  "bytesize": self.read("Flow_Meter:Serial_port", "bytesize"),
                                  "parity": self.read("Flow_Meter:Serial_port", "parity"),
                                  "stopbits": self.read("Flow_Meter:Serial_port", "stopbits"),
                                  "timeout": self.read("Flow_Meter:Serial_port", "timeout"),
                                  "xonxoff": self.read("Flow_Meter:Serial_port", "xonxoff"),
                                  "rtscts": self.read("Flow_Meter:Serial_port", "rtscts")}

        self.__flow_meter_scaling = {"f_multiplier": self.read("Flow_Meter:Scaling", "f_multiplier"),
                                     "f_offset": self.read("Flow_Meter:Scaling", "f_offset"),
                                     "t_multiplier": self.read("Flow_Meter:Scaling", "t_multiplier"),
                                     "t_offset": self.read("Flow_Meter:Scaling", "t_offset"),
                                     "p_multiplier": self.read("Flow_Meter:Scaling", "p_multiplier"),
                                     "p_offset": self.read("Flow_Meter:Scaling", "p_offset")}

        self.__cpc_conf = {"port": self.read("Cpc:Serial_port", "port"),
                           "baudrate": self.read("Cpc:Serial_port", "baudrate"),
                           "bytesize": self.read("Cpc:Serial_port", "bytesize"),
                           "parity": self.read("Cpc:Serial_port", "parity"),
                           "stopbits": self.read("Cpc:Serial_port", "stopbits"),
                           "timeout": self.read("Cpc:Serial_port", "timeout"),
                           "xonxoff": self.read("Cpc:Serial_port", "xonxoff"),
                           "rtscts": self.read("Cpc:Serial_port", "rtscts")}

        self.__dma_conf = {"small_p_d_min": float(self.read("Dma", "small_p_d_min")),
                           "small_p_d_max": float(self.read("Dma", "small_p_d_max")),
                           "number_of_small_p": int(self.read("Dma", "number_of_small_p")),
                           "large_p_d_min": float(self.read("Dma", "large_p_d_min")),
                           "large_p_d_max": float(self.read("Dma", "large_p_d_max")),
                           "number_of_large_p": int(self.read("Dma", "number_of_large_p")),
                           "length": float(self.read("Dma", "length")),
                           "in_electrode_r": float(self.read("Dma", "in_electrode_r")),
                           "out_electrode_r": float(self.read("Dma", "out_electrode_r"))}

        self.__automatic_measurement_conf = {"pulse_count_t": self.read("Automatic_measurement", "pulse_count_t"),
                                             "cycle_wait_t": self.read("Automatic_measurement", "cycle_wait_t"),
                                             "between_voltages_wait_t": self.read("Automatic_measurement",
                                                                                  "between_voltages_wait_t"),
                                             "flow": self.read("Automatic_measurement", "flow"),
                                             "flow_d": self.read("Automatic_measurement", "flow_d"),
                                             "flow_c": self.read("Automatic_measurement", "flow_c"), }

    def update_configuration(self, conf_dict: dict, section: str) -> None:
        """
        Update the configuration values from the ini file
        """

        for key in conf_dict:
            conf_dict.update({key: self.read(section, key)})
        logging.info(f"Updated {conf_dict} configuration dictionary")

    def get_configuration(self, conf_name: str) -> dict:
        """
        Return the configuration dictionary
        """

        if conf_name == "NI_DAQ":
            return self.__ni_daq_conf
        elif conf_name == "NI_DAQ_Scaling":
            return self.__ni_daq_scaling
        elif conf_name == "Flow_Meter":
            return self.__flow_meter_conf
        elif conf_name == "Flow_Meter_Scaling":
            return self.__flow_meter_scaling
        elif conf_name == "Pid":
            return self.__pid_conf
        elif conf_name == "Cpc":
            return self.__cpc_conf
        elif conf_name == "Dma":
            return self.__dma_conf
        elif conf_name == "Automatic_measurement":
            return self.__automatic_measurement_conf
        else:
            logging.error(f"Invalid configuration dictionary name: {conf_name}")

    def read(self, section: str, key: str) -> str:
        """
        Read a value from the config.ini file
        """

        try:
            return self.__config_updater[section][key].value
        except KeyError as e:
            logging.error(e)
            logging.debug(f"Error happened when reading section:{section}, key:{key} from the config.ini file")
            return ""

    def write(self, section: str, key: str, value: str) -> None:
        """
        Write a value to the config.ini file
        """

        try:
            self.__config_updater[section][key].value = value
            self.__config_updater.update_file()  # Save all the changes done to the config.ini file
        except KeyError as e:
            logging.error(e)
            logging.debug(f"Error happened when writing section:{section}, key:{key} to the config.ini file")

    def write_configuration(self, conf: dict, section: str) -> None:
        """
        Write the configuration to the config.ini file
        """

        for item in conf:
            self.write(item, section, conf[item])
