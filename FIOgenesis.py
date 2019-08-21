#!/usr/bin/python3
"""
Interactive CLI program for realtime fio workload generator/process monitor/display  
Allows for tty running of FIO on systems without GUI


Features:
    Create, Import, Delete queued .fio file workloads 
    Run and monitor progress/performance of multiple fio workloads in parallel
    
Optional features: 
    Live output display using webbrowser/JS highcharts
    Results graphed display of throughput using Python plotly package


Python package dependencies:
    Python 2.7+ and 3.5+ tested
    pandas (required)
    PyInquirer (required)
    plotly (optional?)


OS Dependencies:
    lsscsi (optional?)
    nvme-cli (optional?)

modules:
    fioLiveGraph: 
        dynamically creates live graphs based on user selections
    fioRunner:
        creates fio process threads and parses live stdout output from them
    fioGenerator:
        creates/imports .fio files from system  
  
To do:
Use io.StringIO object for updating each process dynamically on line write instead of OS file
Check targets for partition map and warn for write operations(?)
Parse more fio line options? Override the unparseable error in parsing?
Edit existing workloads 
Strip .fio off new file name

ERROR CASE: SELECT ONE different GRAPH PER WORKLOAD; QOS doesn't display


"""

def import_install(package):
    try:
        __import__(package) 
        return 0
    except ImportError:
        #from pip._internal import main as pip
        #pip(['install',package])
        print ('--- Package not found: \'{0}\' --- \n Attempting to import package, please wait...'.format(package))
        install = subprocess.call(['sudo',sys.executable,'-m','pip','install',package])
        return install

#Standard Libs
import subprocess,sys,os,copy,hashlib,shutil,glob,webbrowser,json,traceback

#Installed Libs/Utils
import_install('pandas')
import_install('plotly')
import_install('PyInquirer')
import pandas
from plotly import tools
import plotly.offline as py
import plotly.graph_objs as go
from PyInquirer import style_from_dict, Token, prompt, Separator

#python 2 compatibility for input
if sys.version_info[0] < 3:
    input = raw_input
    py2 = 1
else:
    py2 = 0

#Custom Libs
import fioGenerator,fioRunner


def clearScreen():
    """
    Perform screen/terminal clear
    """
    if 'linux' in sys.platform:
        os.system('clear')
    else:
        os.system('cls')


def fileChecksum(file):
    """
    Return checksum of file contents specified by input [file]
    """
    md5check = hashlib.md5(open(file,'rb').read()).hexdigest()
    return md5check
            

def find_drives(display):
    """
    Function to scan drives/block devices on system
    
    Parameters: 
        display (bool): If True, will print drive list to stdout
        
    Returns: 
        block_dev (list): a list of handles containing the system drive handle 
    """
    if 'linux' in sys.platform:
        lsblk = subprocess.check_output(['lsblk','-Ppo','KNAME,MODEL,SIZE,TYPE,MOUNTPOINT,REV']).decode('utf-8').splitlines()
        block_dev = [line.split() for line in lsblk]
        for line in block_dev:
            try:
                for x in range(len(line)):
                    if line[x].count('\"') == 1:
                        line[x] += ' '+line.pop(x+1)
                    line[x] = line[x].replace('\"','')
            except:
                pass    
        block_dev = pandas.DataFrame([dict(entry.split('=') for entry in row) for row in block_dev])    
        block_dev.rename(columns={'KNAME':'TARGET'}, inplace=True)
        block_dev.insert(len(block_dev.columns),'Firmware','-')
        try:
            nvme_dev = json.loads(subprocess.check_output(['sudo','nvme','list','-o','json']).decode('utf-8'))
            for drive in nvme_dev['Devices']:           
                block_dev.loc[block_dev['DevicePath']==drive['DevicePath'],'Firmware'] = drive['Firmware']
        except:
            pass   
    else: #windows/testmode
        block_dev = subprocess.check_output('wmic diskdrive get name,model')
        block_dev = [x.decode('utf-8') for x in block_dev.splitlines() if x]
        block_dev = [x.strip() for x in block_dev if '\\' in x]
    
    if display:
        print('Target Drives available:')
        print(block_dev.set_index('TARGET'))
        print('')
    return(block_dev['TARGET'].tolist())


def createWorkloadDF(workloadData,dfType):
    """
    Function to create a pandas DataFrame to display workloads detected and queued for running
    
    Parameters:
        workloadData (list): a list of lists containing 1 workload file per element 
            and describing all parameters parsed from workload file
        dfType (int): 
            1: clip some output for queued drive workloads 
            2: clip more output to make room for longer/detailed status during fio monitoring/runtime
    Returns:
        DataFrame: a pandas DF with limited columns for display; exceeding terminal width will clip the displayed columns  
    """ 
    df = pandas.DataFrame.from_dict(workloadData)
    
    if dfType == 1:
        df = df[['file','target','bs','seqRand','readPercent','size','numjobs','iodepth','size','time']]
    elif dfType == 2: 
        widths = {'iops':6,'mbps':5,'eta':15,'status':35}
        for label in widths:
            if py2:
                df.at[0,label] = df.iloc[0][label].encode('utf-8').rjust(widths[label])    
            else:
                df.at[0,label] = df.iloc[0][label].rjust(widths[label])    
            #df.at[0,label] = str(df.iloc[0][label]).rjust(widths[label])    
        df = df[['filename','file','target','bs','seqRand','readPercent','iops','mbps','eta','status']].set_index('filename')
    
    return df
   
   
def parseFIOline(workloadFileLines,key):
    return [x.split('=')[1].strip() for x in workloadFileLines if x.startswith(key)][0]
    
def importExtractWorkloadData():
    """
    Find fio files from currentWL/*.fio and parse the critical command line parameters
        Additionally, check for duplicate file content(via md5), or incompatible workload files 
    
    Parameters: 
        None
        
    Returns: 
        workloadData (list of dicts): list of lists containing one workload file per entry;
            [{'filename':workload_file,
                'file':shortfile,
                'target':target,
                'bs':bs,
                'rw':rw,
                'seqRand':seqRand,
                'readPercent':readPercent,
                'numjobs':numjobs,
                'iodepth':iodepth,
                'size':size,
                'time':time,
                'status':'Idle',
                'eta':'N/A',
                'iops':'0',
                'mbps':'0',
                'percentComplete':0,
                'liveGraphs':{}}
            ]
    """
    files = os.listdir('.')
    workloadFilenames,workloadData,dupCheck = [],[],{}
    for filename in files:
        if filename.endswith('.fio'):
            workloadFilenames.append(filename)     
    print ('Current workloads:')
    for workload_file in workloadFilenames:
        try:
            file = open(workload_file,'r')
            workloadFileLines = file.readlines()
            target = parseFIOline(workloadFileLines,'filename')
            bs = parseFIOline(workloadFileLines,'bs')
            rw = parseFIOline(workloadFileLines,'rw')
            if not rw: 
                rw = parseFIOline(workloadFileLines,'readwrite')
            if rw in ['read','write','rw','readwrite']:
                seqRand = 'seq'
            elif rw in ['randread','randwrite','randrw']:
                seqRand = 'rand'
            if rw in ['read','randread']:
                readPercent = 100
            elif rw in ['write','randwrite']:
                readPercent = 0
            else: 
                readPercent = int(parseFIOline(workloadFileLines,'rwmixread'))
            readPercent = '{0}/{1}'.format(readPercent,100-readPercent)
            numjobs = int(parseFIOline(workloadFileLines,'numjobs'))
            iodepth = int(parseFIOline(workloadFileLines,'iodepth'))
            size = parseFIOline(workloadFileLines,'size')
            if int(parseFIOline(workloadFileLines,'time_based')):
                time = parseFIOline(workloadFileLines,'runtime')
            else: 
                time = 0         
            fileChk = fileChecksum(workload_file)
            if fileChk in dupCheck: 
                print ('*** Warning: These are duplicate workloads!!! ***\n',  
                        u'\u250F\u2501\u26A0 {0}\n'.format(workload_file),  
                        u'\u2517\u2501\u26A0 {0}'.format(dupCheck[fileChecksum(workload_file)]))
            else : 
                dupCheck[fileChecksum(workload_file)] = workload_file
            if len(workload_file) > 20:
                shortfile = workload_file[:8] + '...' + workload_file[-8:]
            else:
                shortfile = workload_file 
            workloadData.append({'filename':workload_file,
                                    'file':shortfile,
                                    'target':target,
                                    'bs':bs,
                                    'rw':rw,
                                    'seqRand':seqRand,
                                    'readPercent':readPercent,
                                    'numjobs':numjobs,
                                    'iodepth':iodepth,
                                    'size':size,
                                    'time':time,
                                    'status':'Idle',
                                    'eta':'N/A',
                                    'iops':'0',
                                    'mbps':'0',
                                    'percentComplete':0,
                                    'liveGraphs':{}
                                })

        except (IndexError,ValueError) as e:
            print(traceback.format_exc())
            print ('\n*** ERROR: Could not parse complete data from WL file: {0} ***'.format(workload_file))
            print ('This file must be deleted or the program will exit.')
            if input ('Do you want to delete this file?') in ['Y','y']:
                os.remove(workload_file)
            else:
                sys.exit()
    print('')
    return workloadData
    


def create_workload(targets):
    """
    Create WL*.fio file from fioGenerator.py selector module
    
    Parameters: 
        targets (list): a list of target drives that will be passed to fioSelector
    
    Output:
        WL_[md5sum].fio file: a fio workload file containining selected parameters passed back from fioGenerator.py     
    """
    try: 
        newWL = fioGenerator.create_fio(targets)
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
        try: 
            newName = input("Enter new fio file name (enter will use file checksum as filename):\n")
            if not newName: 
                newName = fileChecksum('WL_temp.fio')
                os.rename('WL_temp.fio','WL_{0}.fio'.format(newName))
            else:
                os.rename('WL_temp.fio','{0}.fio'.format(newName))
        except FileExistsError: 
            print ('*** This is a duplicate workload! Workload file not created. ***')
            os.remove('WL_temp.fio')
            input('Enter to continue')
    except:
        print ('Error in file workload completion')
        os.remove('WL_temp.fio')   
    
    
def plotOutput(liveDisplay):    

    iopsdata,mbpsdata = [],[]
    
    for filename in glob.glob('results/*.dat'):
        df = pandas.read_csv(filename)
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
    layout = go.Layout(title='Running Average Performance chart' if 'QoS' in liveDisplay['graphTypes'] else 'Workload Performance chart output',
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
    try: 
        webbrowser.get('firefox').open('results/results.html',new=0)
    except:
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
    os.chdir('/home/fio-genesis/currentWL')
    
    while True: 
        clearScreen()
        targets = find_drives(True)       
    
        workloadData = importExtractWorkloadData()
        if workloadData: 
            print(createWorkloadDF(workloadData,1))
            userAction = [{
                    'type': 'list',
                    'message': 'Select Action:',
                    'name': 'action',
                    'choices': ['Create a workload', 
                                'Import a workload', 
                                'Delete a workload',
                                'Run all currently queued workloads',
                                'Exit FIOgenesis']
                    }]
        else:
            print("---No Workloads found in currentWL folder!---")
            userAction = [{
                'type': 'list',
                'message': 'Select Action:',
                'name': 'action',
                'choices': ['Create a workload', 
                            'Import a workload', 
                            'Exit FIOgenesis']
                }]
      
        print('')              
        action = prompt(userAction,style=fioGenerator.style)
        try: 
            action = action['action']
        except KeyError:
            continue
        if action == 'Create a workload':
            create_workload(targets)
       
        elif action == 'Import a workload':
            try: 
                startdir = os.getcwd()
                for files in fioGenerator.importFIO()['selection']:
                    shutil.copy(files,startdir)
            except:
                pass
            finally: 
                os.chdir(startdir)

                
        elif action == 'Delete a workload':
            try: 
                print('\x1b[A'*(len(workloadData)+3)+'\r')
                df = createWorkloadDF(workloadData,1)
                deletion = [{
                    'type': 'checkbox',
                    'message': 'Select Files for deletion:',
                    'name': 'deletionSelection',
                    'choices': [{'name':x} for x in df.to_string().split('\n')[1:]]
                    }]                
                delFiles = prompt(deletion,style=fioGenerator.style)['deletionSelection']
                for x in delFiles:
                    print(workloadData[int(x[0])]['filename'])
                confirm = input("Are you sure you want to delete these files?")
                if confirm in ['y','Y']:
                    for x in delFiles:
                        os.remove(workloadData[int(x[0])]['filename'])
            except:
                pass
                
        elif action == 'Run all currently queued workloads':
            try:
                confirm = 1 if not os.path.isdir('results') else input('Previous Results will be overwritten! Continue?')
                if confirm not in ['n','N','x','X']:
                    shutil.rmtree('results',ignore_errors=True)
                    os.mkdir('results')
                    
                    liveOutputSelect = [
                        {
                            'type': 'checkbox',
                            'message': 'Would you like to plot and display live Benchmark Data?:',
                            'name': 'displayTypes',
                            'choices': [{'name':'IOPS','checked':True},
                                        {'name':'MBPS','checked':True},
                                        {'name':'QoS','checked':True}] 
                        },
                        {
                            'type': 'input',
                            'message': 'Enter desired QoS percentiles:',
                            'name': 'QoS_percentiles',
                            'default': u'10:50:90:95:99:99.9:99.99:99.999:99.9999:99.99999:99.999999',
                            'when': lambda answers: 'QoS' in answers['displayTypes']
                        },
                        {
                            'type': 'checkbox',
                            'message': 'Select workloads for {} live output:'.format('IOPS'),
                            'name': 'IOPS',
                            'choices': [{'name':x['filename'],'checked':True} for x in workloadData],
                            'when': lambda answers: 'IOPS' in answers['displayTypes']
                        },
                        {
                            'type': 'checkbox',
                            'message': 'Select workloads for {} live output:'.format('MBPS'),
                            'name': 'MBPS',
                            'choices': [{'name':x['filename'],'checked':True} for x in workloadData],
                            'when': lambda answers: 'MBPS' in answers['displayTypes']
                        },
                        {
                            'type': 'checkbox',
                            'message': 'Select workloads for {} live output:'.format('QoS'),
                            'name': 'QoS',
                            'choices': [Separator(
                                'Note that MBPS and IOPS will be running averages when QoS is selected')] +
                                [{'name':x['filename'],'checked':True} for x in workloadData],
                            'when': lambda answers: 'QoS' in answers['displayTypes']
                        }]
                    liveOutputSelect = prompt(liveOutputSelect,style=fioGenerator.style)
                    liveDisplay = {'graphTypes':liveOutputSelect.pop('displayTypes')}
                    if 'QoS_percentiles' in liveOutputSelect:
                        liveDisplay['QoS_percentiles'] = liveOutputSelect.pop('QoS_percentiles')
                    for graphType in liveOutputSelect: #{'mbps':[file1,file2],'iops':[file2,file3],'qos':[]}
                        for workload in workloadData: 
                            if workload['filename'] in liveOutputSelect[graphType]:
                                workload['liveGraphs'][graphType] = ''
                    fioRunner.runFIO(workloadData,liveDisplay)
                    question = [{
                        'type': 'confirm',
                        'message': 'Would you like to plot and display performance charts?:',
                        'name': 'plotResults',
                        'default': True
                        }]   
                    if prompt(question,style=fioGenerator.style)['plotResults']:
                        plotOutput(liveDisplay)
            except: 
                raise
                pass   
        elif action == 'Exit FIOgenesis':
            break
    
    print('FIO-genesis Complete')        
 
 
if __name__ == "__main__":
    main()  
