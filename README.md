# fio-genesis
python based cli for fio benchmark workload generation, monitoring, and performnace visualization (real-time and historical)

## Overview
  Written primarily as CLI to enable usage on both GUI and headless/remote Linux systems
    Performance visualizations are HTML/JS based and require compatible web browser

## Package Contents
* FIOgenesis.py
   * Main program, displays drives attached to system, current queued workload parameters. Has menu options to create/import/delete FIO workloads and run/monitor/visualize parallel FIO instances 
* fioGenerator.py
   * Called by FIOgenesis to rapidly create simple FIO workloads (only single jobs supported currently)
* fioRunner.py 
   * Called by FIOgenesis to run all queued FIO workloads
* fioLiveGraph.py
   * Called by FIOgenesis to dynamically generate HTML/JS webpages for monitoring realtime performance of running workloads
* currentWL/
  * Stores currently queued FIO workloads
* currentWL/results
  * Stores results (log file, data, visualizations) from last workload run by FIOgenesis
* results/
  * Results history of workloads previously run by FIOgenesis
  
## Requirements
* Python 2.7+ or 3.4+
* fio 
* non-standard python packages:
  * pandas 
  * PyInquirer
  * plotly
  
 ## Install Instructions
1. Check if you have pip installed:
>pip --version
2. If you need to install pip, it is included in fio-genesis folder: 
>python get-pip.py
3. Install required Python packages (may require sudo):
>pip install pandas
>pip install PyInquirer
>pip install plotly
4. Run FIOgenesis:
>python FIOgenesis.py

## Notes
* FIOgenesis tries its best to parse multiple jobs within a single FIO file, but more complex options will not be parsed/displayed. However, FIOgenesis can still be used to run and display the performance of these jobs (though it will show overall performance graphs per .fio file, rather than parsed by job) 
* Stonewall parameters are not intelligently parsed (yet)

## To do:
* Add integrated secure erase functionality for unmounted drives(..?) to allow complex performance characterizations without user interaction
* Add steady state fio parameters to create workload(?)
* Add fast/simple preconditioning callouts in create workload function

