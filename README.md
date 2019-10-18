# fio-genesis
python based cli for fio benchmark workload generation, monitoring, and visualization

Overview
  Written as CLI to enable usage on both GUI and headless Linux servers/workstations
    Visualizations require GUI system
  
Package Contents
  FIOgenesis.py
    Main program to run, has menu options to create/import/delete FIO workloads and run/monitor/visualize parallel FIO instances
  fioGenerator.py
    Called by FIOgenesis to rapidly create simple FIO workloads (only single jobs supported currently)
  fioRunner.py 
    Called by FIOgenesis to run all queued FIO workloads
  fioLiveGraph.py
    Called by FIOgenesis to dynamically generate HTML/JS webpages for monitoring realtime performance of running workloads
  
    
