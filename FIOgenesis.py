#!/usr/bin/python3
import subprocess,sys,os,re,copy,hashlib,datetime,shutil
from tabulate import tabulate
import plotly
from pprint import pprint
debug = 0
def import_install(package):
    try:
        __import__(package)
    except ImportError:
        #from pip._internal import main as pip
        #pip(['install',package])
        print ('Package not found: {0}, \n Importing package, please wait...'.format(package))
        subprocess.call([sys.executable,'-m','pip','install',package])

import_install('PyInquirer')
import fioSelector


def find_drives(display):
    """
    Function to scan drives/block devices on system
    
    Parameters: 
        display (bool): If True, will print drive list to stdout
        
    Returns: 
        block_dev (list): a list of handles containing the system drive handle 
    """
    if 'linux' in sys.platform:
        block_dev = subprocess.check_output('lsblk')
        block_dev = [x.decode('utf-8') for x in block_dev.splitlines() if x.decode('utf-8')[0] in ['n','s','v']]
        block_dev = ['/'+x.split()[0] for x in block_dev]
    else: #windows/testmode
        block_dev = subprocess.check_output('wmic diskdrive get name,model')
        block_dev = [x.decode('utf-8') for x in block_dev.splitlines() if x]
        block_dev = [x.strip() for x in block_dev if '\\' in x]
    if display:
        print('Target Drives available:')
        for drive in block_dev:
            print(drive)
    return(block_dev)

    
def createWorkloadTable(workloadData,showindex):
    """
    Function to create a tabulate library table to display workloads detected and queued for running
    
    Parameters:
        workloadData (list): a list of lists containing 1 workload file per element 
            and describing all parameters parsed from workload file
        showindex (bool): if true, will add the index to the output table;
            typically on for display/add/delete workloads, off for workload runtime monitoring (to save some screen display space)
            
    Returns:
        tabulate: a string with appropriate table formatting; exceeding terminal width will scramble the display formatting  
    """
    if showindex == 1:
        #headers = {'filename':'Filename','target':'Trgt','bs':'BS','rw':'Rnd/Seq',
        #            'readPercent':'R/W %','numJobs':'Jobs','iodepth':'QD','size':'Size','time':'Time','status':'Status'}          
        headers = ['Filename','Trgt','BS','Rnd/Seq','R/W %','Jobs','QD','Size','Time','Status']          
    else:
        headers = ['Filename','Trgt','BS','Rnd/Seq','R/W %','ETA','Status','Perf\n[IOPS]','Perf\n[MBps]']              
    for fileN in workloadData:
        fileN['shortname'] = fileN['filename'][0:7]+'..'+fileN['filename'][-8:]
    shortenedFilenameData = []
    for wl in workloadData:
        if showindex == 1:
            shortenedFilenameData.append([wl['shortname'],wl['target'],wl['bs'],wl['rw'],wl['readPercent'],
                                        wl['numJobs'],wl['iodepth'],wl['size'],wl['time'],wl['status']])
        else:
            shortenedFilenameData.append([wl['shortname'],wl['target'],wl['bs'],wl['rw'],wl['readPercent'],
                                        wl['eta'],wl['status'],wl['iops'],wl['mbps']])
    return tabulate(shortenedFilenameData, headers=headers, showindex=showindex, tablefmt='fancy_grid')

    
def importExtractWorkloadData():
    """
    Find fio files from pre-set pattern WL*.fio and parse the critical command line parameters
        Additionally, check for duplicate file content(via md5), or incomplete workload files 
    
    Parameters: 
        None
        
    Returns: 
        workloadData (list of dicts): list of lists containing one workload file per entry;
            [   {'filename'='WL*.fio','bs'=%bs1,'rw'='rw1','readPercent'=%rwmixread1,'numJobs'=%numjobs1,'iodepth'=%iodepth1,'size'='%size1', runtime1},
                {filename2, bs2, ...}
            ]
    """
    files = os.listdir()
    workloadFiles = []
    for filename in files:
        if filename.startswith('WL') and filename.endswith('.fio'):
            workloadFiles.append(filename)     
    available_targets = find_drives(False)
    print ('Current workloads:')
    dupCheck = {}
    workloadData = []
    for workload_file in workloadFiles:
        try:
            file = open(workload_file,'r')
            workloadFileLines = file.readlines()
            target = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('filename')][0]
            bs = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('bs')][0]
            rw = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('rw')][0]
            readPercent = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('rwmixread')][0])
            readPercent = '{0}/{1}'.format(readPercent,100-readPercent)
            numJobs = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('numjobs')][0])
            iodepth = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('iodepth')][0])
            size = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('size')][0]
            time = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('runtime')][0]            
            if str(target) not in available_targets:
                print ('*** Warning: Target drive: {0} is not detected on the system! ***'.format(target))
            fileChk = fileChecksum(workload_file)
            if fileChk in dupCheck: 
                print ('*** Warning: These are duplicate workloads!!! ***\n  \u250F\u2501\u26A0 {0}\n  \u2517\u2501\u26A0 {1}'.format(workload_file,dupCheck[fileChecksum(workload_file)]))
            else : 
                dupCheck[fileChecksum(workload_file)] = workload_file
            workloadData.append({'filename':workload_file,
                                    'target':target,
                                    'bs':bs,
                                    'rw':rw,
                                    'readPercent':readPercent,
                                    'numJobs':numJobs,
                                    'iodepth':iodepth,
                                    'size':size,
                                    'time':time,
                                    'status':'Idle',
                                    'eta':'N/A',
                                    'iops':'0',
                                    'mbps':'0',
                                    'percentComplete':0})
        except (IndexError,ValueError):
            print ('\n*** ERROR: Incomplete/Missing data from WL file: {0} ***'.format(workload_file))
            print ('This file must be deleted or the program will exit.')
            if input ('Do you want to delete this file?') in ['Y','y']:
                os.remove(workload_file)
            else:
                sys.exit()
    if not workloadFiles:
        print ('*** Workload list EMPTY! ***')
    return workloadData
'''[
    {'status': 'Idle', 'target': '/vdb', 'time': '6s', 'numJobs': 2, 'bs': '4k', 'filename': 'WL_83ababe207b11dd9d987f4f091eb12ba.fio', 'readPercent': '100/0', 'size': '100M', 'rw': 'randrw', 'iodepth': 16}, 
    {'status': 'Idle', 'target': '/vdb', 'time': '10s', 'numJobs': 2, 'bs': '128k', 'filename': 'WL_8166631393ae3f44ce7dec3bcc1cd1c2.fio', 'readPercent': '70/30', 'size': '10%', 'rw': 'rw', 'iodepth': 4}, 
    {'status': 'Idle', 'target': '/vdb', 'time': '15s', 'numJobs': 1, 'bs': '1M', 'filename': 'WL_61ec5f6d5b457b982654bf8465ca63fb.fio', 'readPercent': '100/0', 'size': '50M', 'rw': 'rw', 'iodepth': 4}, 
    {'status': 'Idle', 'target': '/vdb', 'time': '15s', 'numJobs': 1, 'bs': '1M', 'filename': 'WL_dupetest.fio', 'readPercent': '100/0', 'size': '50M', 'rw': 'rw', 'iodepth': 4}
    ]    
'''
    
    
def delete_workloads(deletion_list):
    """Delete files from input (list) parameter"""
    print ('')
    print ('Files to be deleted:')
    for file in deletion_list:
        print (file)
    if input("\n*** This will delete all previous jobs, Are you sure? ***") in ["Y","y"]:
        for file in deletion_list:
            if not debug:
                os.remove(file)
            print ('{0:<20}{1}'.format('Deleting file:',file))
        print('')


def clearScreen():
    """Perform screen/terminal clear"""
    if 'linux' in sys.platform:
        os.system('clear')
    else:
        os.system('cls')


def create_workload(targets):
    """
    Create WL*.fio file from fioSelector.py selector module
    
    Parameters: 
        targets (list): a list of target drives that will be passed to fioSelector
    
    Output:
        WL_[md5sum].fio file: a fio workload file containining selected parameters passed back from fioSelector.py     
    """
    try: 
        newWL = fioSelector.create_fio(targets)
        f = open('WL_temp.fio','w')
        f.write('[WL]\n' 
                'group_reporting=1\n'
                'name=fio-rand-RW\n'
                'filename={target}\n'
                'rw={rw}\n'
                'rwmixread={iomix}\n'
                'bs={bs}\n'
                'direct=1\n'
                'size={size}\n'
                'ioengine=libaio\n'
                'iodepth={iodepth}\n'
                '{time}\n'
                'numjobs={jobs}\n'.format(
                    target = newWL['target'],
                    rw = ('rw' if newWL['io_type']=='sequential' else 'randrw'),
                    iomix = newWL['io_mix'].split('%')[0],
                    bs = newWL['io_size'],
                    size = newWL['size'],
                    iodepth = newWL['QD'],
                    time = ('time_based=1 \nruntime={0}'.format(newWL['time']) if newWL['time'] else ''),
                    jobs = newWL['jobs'] ))
        f.close()
        newName = fileChecksum('WL_temp.fio')
        try: 
            os.rename('WL_temp.fio','WL_{0}.fio'.format(newName))
        except FileExistsError: 
            print ('*** This is a duplicate workload! Workload file not created. ***')
            os.remove('WL.fio')
            input('Enter to continue')
    except:
        print ('Error in file workload completion')
        os.remove('WL_temp.fio')   
        
        
def fileChecksum(file):
    """Return checksum of file specified by input [file]"""
    md5check = hashlib.md5(open(file,'rb').read()).hexdigest()
    return md5check


def runFIOprocess(workload):                  
    """
    Runs fio executable with JSON fio output for WL*.fio to WL*.log 
    
    Parameters: 
        file (string): target .fio workload file to run
        
    Returns:
        object handle pointing to subprocess.Popen that is running
        
    Note:
        stdout/stderr are routed to Popen object PIPE   
    """        
    try: 
        fioThread = subprocess.Popen(
            ['fio',
            workload['filename'],
            '--eta=always',
            '--output=results/{}'.format(workload['filename'].split('.')[0]+'.log'),
            '--output-format=json'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=False)
        workload['process'] = fioThread
        workload['filename'].split('.')[0]+'.dat'
        workload['wlDescription'] = ' '.join([workload['bs'],workload['rw']])
        workload['targetDescription'] = 'SK hynix drive'
        workload['dataType'] = 'IOPS'
        workload['outputTrackingFileH'] = open('results/{0}.dat'.format(workload['filename'].split('.')[0]),'w')
        workload['outputTrackingFileH'].write('timestamp,iops,mbps\n')        
    except Exception as e:
        print('runFIOprocess error: {0}'.format(e))


def to_number(mstring):
    """Convert strings like 13.9k or 1733MiB/s to numbers"""
    if mstring == '0':
        return 0
    m = re.match(r'([\d\.]+)(.*)', mstring)
    if m:
        # print 'to_number: groups', m.group(1), m.group(2)
        v = float(m.group(1))
        units = m.group(2)
        if units == 'MiB/s':
            return v * 1.024 * 1.024    # Mbps
        elif units == 'KiB/s':
            return v * 0.001024    # Mbps
        elif units == 'k':
            return v*1000            # IOPS
        elif units == '':
            return v
    else:
        raise ValueError('unknown units %s' % mstring)   

   
def get_value(line):
    """Parse continuous fio output and get requested value"""
    # jobs: 1 (f=1): [R(1)][1.2%][r=1733MiB/s,w=0KiB/s][r=13.9k,w=0 IOPS][eta 59m:17s]
    result = {'percentComplete':'0',
                'iops':'0',
                'mbps':'0',
                'eta':'Unknown'}
    
    pattern = r'\[r=([^,]+),w=([^\]]+)\s+(?i)IOPS\]'
    m = re.search(pattern, line)
    if m:
        r, w = to_number(m.group(1)), to_number(m.group(2))
        result['iops'] = '{0:2f}'.format(r + w)
    
    pattern = r'\[([0-9]+[.0-9]+)%.*\[eta\s+([0-9hms:]+)'
    m = re.search(pattern, line)
    if m:
        result['percentComplete'], result['eta'] = m.group(1), m.group(2)
    
    pattern = r'\[r=([^,]+),w=([^\]]+)\]'
    m = re.search(pattern, line)
    if m:
        r, w = to_number(m.group(1)), to_number(m.group(2))
        result['mbps'] = '{0:.1f}'.format(r + w)
    return result  
    
    
def progBar(percentage):
    """
    Create 'shaded' progress bar string of variable length
    
    Parameters:
        percentage (float or int): percentage completion of task/progress
    
    Returns: 
        String of length 'barLength' (hardcoded) shaded according to progress percentage
    """
    barLength = 30
    progress = '\u2588'*int(percentage*barLength/100)
    segmentSpan = 100/barLength
    segmentRemainder = percentage % barLength
    if segmentRemainder:
        if segmentRemainder < (segmentSpan/3):
            progress += '\u2591' #light shade
        elif segmentRemainder < (2*segmentSpan/3):
            progress += '\u2592' #medium shade
        elif percentage < 100:
            progress += '\u2593' #dark shade
    progress += '-'*(barLength-len(progress))
    return progress
 
def plotOutput():
    import glob
    from plotly import tools
    import plotly.offline as py
    import plotly.graph_objs as go
    import pandas as pd
    import webbrowser
    iopsdata,mbpsdata = [],[]
    
    for filename in glob.glob('results/*.dat'):
        df = pd.read_csv(filename)
        filename = filename[8:-4]
        shortname = (filename[:5]+'...'+filename[-5:]) if len(filename) > 10 else filename
        iopsTrace = go.Scatter( 
                        x=df['timestamp'], y=df['iops'], # Data
                        mode='lines', name=shortname+' IOps' # Additional options
                       )
        mbpsTrace = go.Scatter(
                        x=df['timestamp'], y=df['mbps'], # Data
                        mode='lines', name=shortname+' MBps' # Additional options
                       )
        iopsdata.append(iopsTrace)
        mbpsdata.append(mbpsTrace)
    layout = go.Layout(title='Workload Performance chart output',
                       paper_bgcolor='rgb(230, 230, 230)',
                       plot_bgcolor='rgb(200 , 200 , 200)')    
    fig = tools.make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=0.02,print_grid=False)
    fig['layout']['yaxis1'].update(title='IOPS')
    fig['layout']['yaxis2'].update(title='MBps')
    fig['layout'].update(layout)
    for trace in iopsdata:
        fig.append_trace(trace,1,1)
    for trace in mbpsdata:
        fig.append_trace(trace,2,1)
    
    py.plot(fig, filename='results/results.html',auto_open=False)
    webbrowser.open('results/results.html', new=0)

def main():
    """
    Find files matching pattern WL*.fio in ./currentWL
    
    Inputs: 
        User keyed inputs from context menus
    
    Outputs:
        Print queued workload details and running workload status/progress/performance
    
    Internal structures:
         Store in workloads object

    """    
    os.chdir(path='./currentWL')
    shutil.rmtree('results',ignore_errors=True)
    os.mkdir('results')
    clearScreen()
    workloadData = importExtractWorkloadData()
    print(createWorkloadTable(workloadData,1))  

    ### Ask user if they want to keep the existing current workloads
    while True  :
        try:
            keep_Workloads = input("Do you want to use existing workloads?")
            if keep_Workloads not in ['y','Y','n','N']:
                raise ValueError
            elif keep_Workloads in ['y','Y']:
                keep_Workloads = True
            else:
                keep_Workloads = False
            break
        except ValueError:
            print ("Sorry I didn't understand that response")
            continue
        
    ### Delete or keep previous workloads with pattern WL*.fio 
    if not keep_Workloads:
        delete_workloads([x['filename'] for x in workloadData])

    ### List target drives available
    clearScreen()
    print(createWorkloadTable(importExtractWorkloadData(),1)) 
    targets = find_drives(True)
    
    # Ask user if they want to change workloads
    while True and not debug:
        response = input("Do you want to change a workload? (Y/N) ")
        if response in ["Y","y"]:
            response = input ('Do you want to add or delete a workload? (A/D) ')
            # Add a workload
            if response in ['a','A']:
                create_workload(targets)
            # Delete a workload
            elif response in ['d','D']:
                while True:
                    try:
                        deletionID = input ('Which workload do you want to delete? (X to exit)')
                        if deletionID in ['x','X']:
                            break
                        deletionID = int(deletionID)
                        os.remove(workloadData[deletionID]['filename'])   
                        print ('file deleted: {0}'.format(workloadData[deletionID]['filename']))    
                    except ValueError:
                        print ('Sorry, I did not understand the deletion number')
            clearScreen()
            print(createWorkloadTable(importExtractWorkloadData(),1)) 
        elif response in ['n','N']:
            break
        else:
            print ("Sorry, I could not understand that response.")
    clearScreen()
    workloadData = importExtractWorkloadData()
    print(createWorkloadTable(workloadData,1))
    
    # Import WLs  from files and Run target workloads, display progress bars 
    if 1:#try:
        if input("Do you want to run these workloads? (Y/N) ") in ["Y","y"]:
            # processTracker = {filename:{process: processHandle, percentage:0,performance:0,eta:0},
            #                    filename2:{process2: processHandle2, percentage:0,performance:0,eta:0}}
            import fioDisplay,webbrowser
            for wlDict in workloadData:
                print ('{0}{1}'.format('Starting Workload:',wlDict['filename']))
                runFIOprocess(wlDict)    
            print('\n'*(2*len(workloadData)+2))            
            #fioDisplay.createHTMLpage(workloadData,title='check title passage')
            #webbrowser.open('fioDisplay.html',new=0)
            while any(wl['percentComplete'] != 100 for wl in workloadData):
                #pprint(workloadData)
                for workload in workloadData:
                    line = workload['process'].stdout.readline() #check/read new workload stdout
                    if line[0:4] == 'Jobs': #output is currently printing live status output from workload process
                        workload.update(get_value(line))
                        percent = float(workload['percentComplete'])
                        workload['status'] = progBar(percent)+' {0:3}%'.format(int(percent)) 
                        iops = int(float(workload['iops']))
                        mbps = int(float(workload['mbps']))
                        timestamp = datetime.datetime.isoformat(datetime.datetime.now())
                        workload['outputTrackingFileH'].write(
                            '{timestamp},{iops},{mbps}\n'.format(
                            timestamp=timestamp,
                            iops = str(int(float('{:.{p}g}'.format(iops,p=3)))),
                            mbps = str(int(float('{:.{p}g}'.format(mbps,p=3))))
                                )
                            ) #3 significant figures
                        print('\x1b[A'*(2*len(workloadData)+5)+'\r') #move caret back to beginning of table
                        print(createWorkloadTable(workloadData,0)) #reprint workload monitor table
                    if line == '' and workload['process'].poll() is not None: 
                        workload['percentComplete'] = 100   
                        workload['outputTrackingFileH'].close()
            print('\x1b[A'*(2*len(workloadData)+5)+'\r') #move caret back to beginning of table
            print(createWorkloadTable(workloadData,0)) #reprint workload monitor table
            plotOutput()
    """                
    except KeyError as key: 
        if processTracker: 
            print ('possible error? \n {0}'.format(key))
    except Exception as e:
        print ('error: {0}'.format(e))
        sys.exit()
    """   
    sys.stdout.flush()
    if 0:
        #Delete live output files
        try: 
            for x in workloadData:
                os.remove(x['outputTrackingFile'])
        except KeyError:
            pass
    print('FIO-Generator Complete')

if __name__ == "__main__":
    main()  
