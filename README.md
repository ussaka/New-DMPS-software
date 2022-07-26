# New DMPS software
**General**
- Program for DMPS, HalfMini and UFDMPS. 
- Basic working principle for all setups is similar. Parameters are different and for example HalfMini uses probably different kind of blower. UFDMPS has two DMAs and two CPCs.<br /><br />
- :heavy_check_mark: = Feature is done
- :x: = Feature is not yet implemented
- :grey_question: = Not sure if the feature is needed or is implemented

**Detectors**
- :heavy_check_mark: TSI CPCs old legacy serial and pulse connection
- :x: TSI CPCs, new serial, pulse and TCP connections
- :x: TSI electrometer
- :x: Airmodus A20
- :x: Airmodus PSM+A20 (for HalfMini)
- :x: Airmodus new model (A30?)
- :x: Airmodus UFCPC model coming?
- :x: Analog electrometers
- :grey_question: Also detector status should be saved

**DMA's**
- :grey_question: Vienna different lengths
- :grey_question: HalfMini
- :grey_question: TSI nano and long

**Blowers**
- :heavy_check_mark: Both analog control and pwm using TSI flow meter
- :x: HalfMini could use 2 x blower (same type as for DMPS) in future

**TSI flow meter**
- :heavy_check_mark: Flow, T and P
- :heavy_check_mark: 4000 series
- :x: 5000 series

**Analog signals**
- :heavy_check_mark: dP (flow), T, P, RH, HV monitor
- :grey_question: Possibility to add more analog input channels

**High Voltage**
- :heavy_check_mark: Stepping voltage (DMPS)
- :grey_question: Stepping voltage (SMPS)
- :x: Continous voltage scan (DMPS and SMPS)

**PID control**
- :heavy_check_mark: Sheath flow
- :x: blower pid using microcontroller?
- :x: HV control?
- :heavy_check_mark: Blower pid control is executed in separate thread, could be improved

**Inversion**
- :x: Python inversion by Anton as module or stand alone old Fortran code from PasiA
- :x: SMPS inversion? In a separate script but the actual measurement program could give a possibility to determine the delay time. 

**Parameters**
- :heavy_check_mark: *.INI-file
- :heavy_check_mark: Program should give a possibility to create the *INI-file (graphical user interface).<br />`The ini file can be edited in the gui and ini file template is part of this repository. New ini file can not be created with the gui`
- :heavy_check_mark: Should have also a 'service mode' which allows to change the parameters from GUI. Service mode should show the scaled values.
- :x: Service mode should also show the raw values.

**Graphical user interface**
- :heavy_check_mark: Tkinter
- :x: Draw graphs of the data

**DAQ by NI**
- :heavy_check_mark: NI6211 & 6215

**Other features**
- :heavy_check_mark: Windows supported
- :heavy_check_mark: GUI
- :heavy_check_mark: Service mode as described above

**To Do**
- :x: Possibility to set calibration coefficients for each measured value (temperature, RH etc)
- :x: Plotting raw data is implemented to the main script. We'll check the inverted data later.
- :x: Possibility to switch (and modify) between 4/20 flow modes and size ranges (e.g. 10-820 nm) in the maintenance mode
- :x: Data is saved according to Actris instructions.
- :x: Change time function to performance time (Python)
- :x: SMPS measurement frequency is - at least in the beginning - 10 Hz. Every second scan is ascending and every second descending.
- :x: What's meaning of 'flow', 'flow_d' and 'flow_c' in Pasi's script? Some correction factor?

**Feature wishlist**
- :x: Check updates from Gitlab automatically

**Meeting notes**
- Week 22: 
  - Pasi goes through the scripts shortly with Kasperi. Hannu has done a very simple GUI. Kasperi has also started with the user interface.

- June 13:
  - First GUI version is done, TSI flow meter interface ready.
  - TSI flow meter could have a linear scaling option (offset + span --> 'a*x + b').
  - Adding NI DAQ to the program, including sensors connected with the NI. So T, RH, P, dP (aerosol flow), HV source (input, output, PID option), CPC pulses (counter), solenoid valves (digital output). Blower will be controlled via a microcontroller (Hannu's board) which is connected to the computer via a serial port. However, blower controlling with NI (including PID) should be an option as all current DMPS work in that way. In addition, building the microcontroller can take a while.
  - Adding detectors, i.e. CPCs, to the program (serial in this stage).
  - Board and detailed comments for the scripts (Finnish/English...doesn't matter). Comments can contain also examples how to modify the script.
  - Pasi is on holiday from Midsummer onwards. 
  - Next meeting again on next Monday (June 20).  

- June 20:
  - Pasi gives instructions how to add electrometer (TSI) communication to the script. Otherwise, TSI3750 is enough in this stage.
  - Aim is to get the DMPS measurement cycle running so that the data is produced correctly. SMPS is done after that. SMPS measurement frequency is - at least in the beginning - 10 Hz. Every second scan is ascending and every second descending. Pasi gives instructions.
  - Data is saved according to Actris instructions. 
  - Plotting raw data is implemented to the main script. We'll check the inverted data later.
  - Let's have a short meeting still on Wednesday 22.

- July 11
  - Automatic updates (e.g. 1 s) of parameter values in GUI
  - Possibility to set calibration coefficients for each measured value (temperature, RH etc)
  - CPC concentration could be visible also in the maintenance window 
  - Possibility to switch (and modify) between 4/20 flow modes and size ranges (e.g. 10-820 nm) in the maintenance mode
  - Open questions:
    - How does time function work in Python? Does it use the performance counter?
    - Is 'float' double in Python?
    - What's meaning of 'flow', 'flow_d' and 'flow_c' in Pasi's script? Some correction factor?
    - Is it possible to read 5 s average value from the CPC directly?

# Instructions
**Requirements**
- Python 3.x.x
- Tested to work with Python version 3.9.7
- :grey_question: (NI-DAQmx or NI-DAQmx Runtime)

**Installation**
- Open any terminal program(cmd) and download the repository with `git clone https://version.helsinki.fi/atm-tech/new-dmps-software.git` you might need credentials for that.
  - Or just download the zip file from the main page
  - Install the repository to any safe location<br /><br />
- Create virtual environment with `python -m venv env` inside `new-dmps-software` folder
  - Virtual environment enables you to have multiple different python and python module versions installed on the same PC. The Environment to run this program is now isolated virtual environment.
  - Usage of virtual environment is optional
- Activate the env with `env\Scripts\activate`
  - Make sure you are in correct location so the given file path will work(Root folder which contains env folder)
  - PowerShell might give you trouble
  - If your terminal displays `(env) [PATH]` everything is working correctly<br /><br />
- Navigate with `cd` inside `new-dmps-software`(root folder of the program)
- Install required depencies with `python -m pip install -r requirements.txt`
  - Pip probably gives warning to upgrade to a new version. You can do that if you want
  - Installation is now complete

**How to start the program**
- Navigate inside `new-dmps-software` folder with any terminal program(cmd)
- Activate the virtual environment `env\Scripts\activate`
- Run the main file with `python main.py`
