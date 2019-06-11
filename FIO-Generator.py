#!/usr/bin/python
import subprocess,sys,os,re,tqdm
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
import fio_selector

def find_drives(display):
    if 'linux' in sys.platform:
        block_dev = subprocess.check_output('lsblk')
        block_dev = [x.decode('utf-8') for x in block_dev.splitlines() if x.decode('utf-8')[0] in ['n','s','v']]
        block_dev = [x.split()[0] for x in block_dev]
    else: #windows/testmode
        block_dev = subprocess.check_output('wmic diskdrive get name,model')
        block_dev = [x.decode('utf-8') for x in block_dev.splitlines() if x]
        block_dev = [x.strip() for x in block_dev if '\\' in x]
    if display:
        print('Target Drives available:')
        for drive in block_dev:
            print(drive)
    return(block_dev)

def print_workloads(workload_list):
    available_targets = find_drives(False)
    print ('Current workloads:')
    dupCheck = []
    for workload_file in workload_list:
        try:
            iodepth = ''
            file = open(workload_file,'r')
            workloadFileLines = file.readlines()
            column_align = '{0:<30}{1}'
            print ('')
            print ('_____WORKLOAD_#{0:>30}'.format(
                str(workload_list.index(workload_file))+'_'*100)[0:60])
            print (column_align.format('Workload File found:',workload_file))
            target = [x.split('=')[1].strip() for x in 
                workloadFileLines if x.startswith('filename')][0]
            print (column_align.format('Target:',target))
            print (column_align.format('IO BlockSize:',[x.split('=')[1].strip() 
                for x in workloadFileLines if x.startswith('bs')][0]))
            print (column_align.format('Random/Sequential:',[x.split('=')[1].strip() 
                for x in workloadFileLines if x.startswith('rw')][0]))
            readPercent = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('rwmixread')][0])
            print (column_align.format('R/W distribution:','{0}% Read, {1}% Write'.format(readPercent,(100-readPercent))))
            numJobs = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('numjobs')][0])
            iodepth = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('iodepth')][0])
            print (column_align.format('Queue Depth per job:','{0}'.format(iodepth)))
            print (column_align.format('Number of jobs:','{0}'.format(numJobs)))
            print (column_align.format('Total queue depth:','{0}'.format(numJobs*iodepth)))
            if str(target) not in available_targets:
                print ('*** Warning: This target drive is not detected on the system! ***')
            print ('-'*60)
            fileChk = fileChecksum(workload_file)
            if fileChk in dupCheck:
                print ('*** Warning: This is a duplicate workload!!! ***')
                input('')
            else : 
                dupCheck.append(fileChecksum(workload_file))
        except IndexError:
            print ('\n*** ERROR: Incomplete/Missing data from WL file: {0} ***'.format(workload_file))
            print ('This file must be deleted or the program will exit.')
            if input ('Do you want to delete this file?') in ['Y','y']:
                os.remove(workload_file)
            else:
                sys.exit()
    if not workload_list:
        print ('*** EMPTY! ***')
    print('')
    
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

def importWLfromFile():
    files = os.listdir()
    workloads = []
    for object in files:
        if object.startswith('WL') and object.endswith('.fio'):
            workloads.append(object)    
    return workloads 

def clearScreen():
    if 'linux' in sys.platform:
        os.system('reset')
    else:
        os.system('cls')


def create_workload(targets,numWorkloads):
    newWL = fio_selector.create_fio(targets)
    f = open('WL.fio'.format(numWorkloads),'w')
    f.write("""
[global]
name=fio-rand-RW
filename={0}
rw={1}
rwmixread={2}
bs={3}
direct=1
numjobs=4   
time_based=1
runtime=900

[file1]
ioengine=libaio
iodepth={4}
    """.format(newWL['target'],('rw' if newWL['io_type']=='sequential' else 'randrw'),newWL['io_mix'].split('%')[0],newWL['io_size'],newWL['QD']))
    f.close()
    newName = fileChecksum('WL.fio')
    try: 
        os.rename('WL.fio','WL_{0}.fio'.format(newName))
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
        '''
        while True:
            nextline = fioThread.stdout.readline()
            if nextline == '' and fioThread.poll() is not None:
                break
            sys.stdout.write(nextline)
            with open('test.log', 'w') as of:
                of.write(get_value(nextline,'iops'))
        '''
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
 
def main():
    ### Find files matching pattern WL*.fio in ./currentWL
    ### Store in workloads object
    ### Print previous workloads and details
    workloads = []
    os.chdir(path='./currentWL')
    clearScreen()
    workloads = importWLfromFile()
    print_workloads(workloads) 
    
    ### Ask user if they want to keep the existing current workloads
    while True  :
        try:
            keep_Workloads = input("\nDo you want to use existing workloads?")
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
        
    ### Keep previous workloads 
    if not keep_Workloads:
        delete_workloads(workloads)

    ### List target drives available
    clearScreen()
    workloads=importWLfromFile()
    print_workloads(workloads)   
    print ('')
    targets = find_drives(True)
    # Change target workload dialog prompts
    while True and not debug:
        response = input("Do you want to change a workload? (Y/N) ")
        if response in ["Y","y"]:
            response = input ('Do you want to add or delete a workload? (A/D) ')
            if response in ['a','A']:
                # Add workload
                create_workload(targets, len(workloads))
            elif response in ['d','D']:
                # Delete workload
                while True:
                    try:
                        workloads = importWLfromFile()
                        deletion = input ('Which workload do you want to delete? (X to exit)')
                        if deletion in ['x','X']:
                            break
                        else:
                            deletion = int(deletion)
                    except ValueError:
                        print ('Sorry, I did not understand the deletion number')
                    if not debug:
                        os.remove(workloads[deletion])
                    print ('file deleted: {0}'.format(workloads[deletion]))
            clearScreen()
            workloads = importWLfromFile()
            print_workloads(workloads)
        elif response in ['n','N']:
            break
        else:
            print ("Sorry, I could not understand that response.")
    clearScreen()
    workloads = importWLfromFile()
    print_workloads(workloads)
    
    # Import WLs  from files and Run target workloads
    try:
        if input("Do you want to run these workloads? (Y/N) ") in ["Y","y"]:
            # processTracker = {filename:{process: processHandle, percentage:0,performance:0,eta:0}}
            processTracker = {}
            for file in workloads:
                print ('{0}{1}'.format('Starting Workload:',file))
                processTracker[file]={'process':runFIOprocess(file)}
            progressBars = {}
            performanceBars = {}
            for workload in processTracker:
                progressBars[workload] = tqdm.tqdm(desc='{0}'.format(workload),unit='%',total=100)
                performanceBars[workload] = tqdm.tqdm(desc='{0} IOPS:'.format(workload),unit='',total=100000)
            while processTracker:
                removal = []
                for workload in processTracker:
                    line = processTracker[workload]['process'].stdout.readline()              
                    if debug:
                        sys.stdout.write(line)
                    if line[0:4] == 'Jobs':
                        processTracker[workload].update(get_value(line))
                        progressBars[workload].n = float(processTracker[workload]['percentComplete'])
                        progressBars[workload].display()
                        performanceBars[workload].n = float(processTracker[workload]['performance'])
                        performanceBars[workload].display() 
                        
                    if line == '' and processTracker[workload]['process'].poll() is not None: 
                        removal.append(workload)
                for x in removal:
                    processTracker.pop(x)
    except KeyError as key: 
        if processTracker: 
            print ('possible error? \n {0}'.format(key))
    except Exception as e:
        print ('error: {0}'.format(e))
        sys.exit()

if __name__ == "__main__":
    main()  
