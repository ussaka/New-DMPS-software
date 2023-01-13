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
- :x: Also detector status should be saved (concentration and all other data)

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
- :x: Stepping voltage (SMPS)
- :x: Continous voltage scan (DMPS and SMPS)

**PID control**
- :heavy_check_mark: Sheath flow
- :x: Blower pid using microcontroller?
- :x: HV control
- :heavy_check_mark: Blower pid control is executed in separate thread, could be improved

**Inversion**
- :x: Python inversion by Anton as module or stand alone old Fortran code from PasiA
- :x: SMPS inversion? In a separate script but the actual measurement program could give a possibility to determine the delay time. 

**Parameters**
- :heavy_check_mark: *.INI-file
- :heavy_check_mark: Program should give a possibility to create the *INI-file (graphical user interface). -> _The ini file can be edited in the gui and ini file template is part of this repository. New ini file can not be created with the gui._
- :heavy_check_mark: Should have also a 'service mode' which allows to change the parameters from GUI. Service mode should show the scaled values.
- :x: Service mode should also show the raw values

**Graphical user interface**
- :heavy_check_mark: Tkinter
- :heavy_check_mark: Draw graphs of the data

**DAQ by NI**
- :heavy_check_mark: NI6211 & 6215


# Instructions
**Requirements**
- Python 3.x.x
- Tested to work with Python version 3.9.7
- NI-DAQmx (NI-DAQmx Runtime might be enough?)

**Installation**
- Open any terminal program(cmd) and download the repository with `git clone https://version.helsinki.fi/atm-tech/new-dmps-software.git` you need credentials for that
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
  - PowerShell might give you trouble
  - If you encounter problems ensure that your PATH is correct
- Run the main file with `python main.py`

**Bugs/Issues**
- Known small priority bugs are documented in Gitlab's Issues section
- If you encounter a bug you can document it in the Issues section. It would be helpful if you attach debug.log from debug folder (and screenshot of terminal output) to the report
