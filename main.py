# TODO: Clean gui.py code
# TODO: Update requirements.txt
# TODO: Update readme.md
# TODO: All ready to merge expect gui.py

import gui
import flow_meter as tsi

flow_meter = tsi.FlowMeter() # Create tsi 4000 series flow meter object

app = gui.MainWindow()  # Create gui object
app.mainloop()  # Start TKinter loop for the gui