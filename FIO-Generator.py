#!/usr/bin/python
import subprocess,sys,os,re,copy
from tabulate import tabulate
from pprint import pprint
debug = 0
tqdmDisplay = 0
if tqdmDisplay: import tqdm
def import_install(package):
    try:
        __import__(package)
    except ImportError:
        #from pip._internal import main as pip
        #pip(['install',package])
        print ('Package not found: {0}, \n Importing package, please wait...'.format(package))
        subprocess.call([sys.executable,'-m','pip','install',package])

import_install('PyInquirer')
import fio_selector


def find_drives(display):
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
    headers = ['Filename','Trgt','BS','Rnd/Seq','R/W %','Jobs','QD','Size','Time','Status']          
    shortenedFilenameData = copy.deepcopy(workloadData)
    for fileN in shortenedFilenameData:
        fileN[0] = fileN[0][0:7]+'..'+fileN[0][-8:]
    return tabulate(shortenedFilenameData, headers=headers, showindex=showindex, tablefmt='fancy_grid')

    
def importExtractWorkloadData():
    """
    
    """
    files = os.listdir()
    workloadFiles = []
    for filename in files:
        if filename.startswith('WL') and filename.endswith('.fio'):
            workloadFiles.append(filename)     
    available_targets = find_drives(False)
    print ('Current workloads:')
    dupCheck = []
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
                print ('*** Warning: This is a duplicate workload!!! ***')
                input('')
            else : 
                dupCheck.append(fileChecksum(workload_file))
                workloadData.append([workload_file,target,bs,rw,readPercent,numJobs,iodepth,size,time,'Idle'])
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
    
    
def delete_workloads(deletion_list):
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
    if 'linux' in sys.platform:
        os.system('reset')
    else:
        os.system('cls')


def create_workload(targets):
    newWL = fio_selector.create_fio(targets)
    f = open('WL_temp.fio','w')
    f.write('[WL]\n' 
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
   
        
def fileChecksum(file):
    import hashlib
    md5check = hashlib.md5(open(file,'rb').read()).hexdigest()
    return md5check


def runFIOprocess(file):                          
    try: 
        fioThread = subprocess.Popen(
            ['fio',
            file,
            '--eta=always'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=False)
        return (fioThread)    
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
            return v            # kIOPS
        elif units == '':
            return v
    else:
        raise ValueError('unknown units %s' % mstring)   

   
def get_value(line, value='iops'):
    """Parse continuous fio output and get requested value"""
    # jobs: 1 (f=1): [R(1)][1.2%][r=1733MiB/s,w=0KiB/s][r=13.9k,w=0 IOPS][eta 59m:17s]
    result = {'percentComplete':'0',
                'performance':'0.00',
                'eta':'0'}
    # result: percentage complete; performance (IOPS OR Throughput); eta (time)
    if value == 'iops':
        pattern = r'\[r=([^,]+),w=([^\]]+)\s+(?i)IOPS\]'
    else:
        pattern = r'\[r=([^,]+),w=([^\]]+)\]'
    m = re.search(pattern, line)
    if m:
        # print 'get_value: groups', m.group(1), m.group(2)
        r, w = to_number(m.group(1)), to_number(m.group(2))
        result['performance'] = '{0:2f}'.format(r + w)
    pattern = r'\[([0-9]+[.0-9]+)%.*\[eta\s+([0-9hms:]+)'
    m = re.search(pattern, line)
    if m:
        result['percentComplete'], result['eta'] = m.group(1), m.group(2)
    return result  
    
    
def progBar(percentage):
    barLength = 20
    progress = '\u2588'*int(percentage*barLength/100)
    segmentSpan = 100/barLength
    segmentResidual = percentage % barLength
    if segmentResidual:
        if segmentResidual < (segmentSpan/3):
            progress += '\u2591'
        elif segmentResidual < (2*segmentSpan/3):
            progress += '\u2592'
        else:
            progress += '\u2593'
    progress += '-'*(barLength-len(progress))
    return progress
 
 
def main():
    ### Find files matching pattern WL*.fio in ./currentWL
    ### Store in workloads object
    ### Print previous workloads and details
    os.chdir(path='./currentWL')
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
        workloadFiles = [x[0] for x in workloadData]
        delete_workloads(workloadFiles)

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
                        workloadFiles = [x[0] for x in importExtractWorkloadData()]
                        deletionID = input ('Which workload do you want to delete? (X to exit)')
                        if deletionID in ['x','X']:
                            break
                        deletionID = int(deletionID)
                    except ValueError:
                        print ('Sorry, I did not understand the deletion number')
                    os.remove(workloadFiles[deletionID])
                    print ('file deleted: {0}'.format(workloadFiles[deletionID]))
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
    try:
        if input("Do you want to run these workloads? (Y/N) ") in ["Y","y"]:
            # processTracker = {filename:{process: processHandle, percentage:0,performance:0,eta:0}}
            processTracker = {}
            workloadFiles = [x[0] for x in workloadData]
            for file in workloadFiles:
                print ('{0}{1}'.format('Starting Workload:',file))
                processTracker[file]={'process':runFIOprocess(file)}
            progressBars = {}
            performanceBars = {}
            if tqdmDisplay == 1:
                for workload in processTracker:
                    progressBars[workload] = tqdm.tqdm(desc='{0}'.format(workload),unit='%',total=100)
                    #performanceBars[workload] = tqdm.tqdm(desc='{0} IOPS:'.format(workload),unit='',total=100000)
            else:
                print('\n'*(2*len(workloadData)+2))    
            while processTracker:
                removal = []
                for workload in processTracker:
                    line = processTracker[workload]['process'].stdout.readline()              
                    if debug:
                        sys.stdout.write(line)
                    if line[0:4] == 'Jobs':
                        processTracker[workload].update(get_value(line))
                        if tqdmDisplay == 1:
                            progressBars[workload].n = float(processTracker[workload]['percentComplete'])
                            progressBars[workload].display()
                            #performanceBars[workload].n = float(processTracker[workload]['performance'])
                            #performanceBars[workload].display() 
                        else:
                            for row in workloadData: 
                                if row[0] == workload:
                                    percent = float(processTracker[workload]['percentComplete'])
                                    row[-1] = progBar(percent)+' {0:3}%'.format(int(percent)) 
                                    print('\x1b[A'*(2*len(workloadData)+4)+'\r')
                                    print(createWorkloadTable(workloadData,0))
                    if line == '' and processTracker[workload]['process'].poll() is not None: 
                        removal.append(workload)
                        if tqdmDisplay == 1:
                            progressBars[workload].close()
                for x in removal:
                    processTracker.pop(x)
    except KeyError as key: 
        if processTracker: 
            print ('possible error? \n {0}'.format(key))
    except Exception as e:
        print ('error: {0}'.format(e))
        sys.exit()
   
    sys.stdout.flush()
    print('FIO run Complete')

if __name__ == "__main__":
    main()  
