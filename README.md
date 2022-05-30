# New DMPS software

General
- Program for DMPS, HalfMini and UFDMPS. 
- Basic working principle for all setups is similar. Parameters are different and for example HalfMini uses probably different kind of blower. UFDMPS has two DMAs and two CPCs.

**Detectors**
- TSI CPCs, both old and new serial, pulse and TCP connections
- TSI electrometer
- Airmodus A20
- Airmodus PSM+A20 (for HalfMini)
- Airmodus new model (A30?)
- Airmodus UFCPC model coming?
- Analog electrometers
- Also detector status should be saved

**DMA's**
- Vienna different lengths
- HalfMini
- TSI nano and long

**Blowers**
- Both analog control and pwm using TSI flow meter
- HalfMini could use 2 x blower (same type as for DMPS) in future

**TSI flow meter**
- Flow, T and P
- Both 4000 and 5000 serie

**Analog signals**
- dP (flow), T, P, RH, HV monitor
- Possibility to add more analog input channels

**Stepping voltage and continous voltage scan (DMPS and SMPS)**

**PID control**
- Sheath flow? Or using microcontroller?
- HV control?
- Parallel script

**Inversion**
- Python inversion by Anton as module or stand alone old Fortran code from PasiA
- SMPS inversion? In a separate script but the actual measurement program could give a possibility to determine the delay time. 

**Parameters**
- *.INI-file
- Program should give a possibility to create the *INI-file (graphical user interface).
- Should have also a 'service mode' which allows to change the parameters from GUI. Service mode should show both the raw and the scaled values.

**Graphical user interface**
- TKINTER? (not sure of the name)
- Separate result pictures (matplotlib)

**DAQ by NI**
- NI6211 & 6215

**Other features**
- Windows
- GUI
- Service mode as described above

**PLAN**
- Everything should go to Git
- Pasi's previous scripts are used (these are alredy given to Kasperi)
- Programmers: Hannu, Pasi, Kasperi,...(Pekka?)
- Pasi supervises Kasperi with the programming
- Hannu supervises Kasperi with hardware

**HOW TO START WITH PYTHON**
- Separate Python environment (how to do?)
- Measurement mode, service mode, configuration mode

**SCHEDULE**
- Let's start at week 21
- Short meetings every week 
- Summer holidays around mid summer and in July. Project should be in a good progress before that.

**NOTES**
Week 22: Pasi goes through the scripts shortly with Kasperi. Hannu has done a very simple GUI. Kasperi has also started with the user interface. 



