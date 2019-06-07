#!/usr/bin/python
import subprocess,sys,os
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

#import_install('PyInquirer')
#import fio_selector

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
        iodepth = ''
        file = open(workload_file,'r')
        workloadFileLines = file.readlines()
        column_align = '{0:<30}{1}'
        print ('')
        print ('_____WORKLOAD_#{0:>30}'.format(str(workload_list.index(workload_file))+'_'*100)[0:60])
        print (column_align.format('Workload File found:',workload_file))
        target = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('filename')][0]
        print (column_align.format('Target:',target))
        print (column_align.format('IO BlockSize:',[x.split('=')[1].strip() for x in workloadFileLines if x.startswith('bs')][0]))
        print (column_align.format('Random/Sequential:',[x.split('=')[1].strip() for x in workloadFileLines if x.startswith('rw')][0]))
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

def import_workloads_from_file():
    files = os.listdir()
    workloads = []
    for object in files:
        if object.startswith('WL') and object.endswith('.fio'):
            workloads.append(object)    
    return workloads 

def clear_screen_print_workloads():
    if 'linux' in sys.platform:
        os.system('reset')
    else:
        os.system('cls')
    workloads = import_workloads_from_file()
    print_workloads(workloads)

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
    fioThread = subprocess.Popen('./fiorun.py -j {0}'.format(file),
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,shell=1)
    







def main():
    ### Find files matching pattern WL*.fio in ./currentWL
    ### Store in workloads object
    ### Print previous workloads and details
    workloads = []
    os.chdir(path='./currentWL')
    workloads = import_workloads_from_file()
    print_workloads(workloads) 
    
    ### Ask user if they want to keep the existing current workloads
    while True:
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
    print ('')
    print_workloads(workloads)   
    targets = find_drives(True)
    while True:
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
                        workloads = import_workloads_from_file()
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
            clear_screen_print_workloads()
        elif response in ['n','N']:
            break
        else:
            print ("Sorry, I could not understand that response.")
            
    sys.exit()
    try:
        if input("Do you want to run these workloads? (Y/N) ") in ["Y","y"]:
            
        else:
            print ("Okay, exiting...")
            sys.exit() 
    sys.exit()

if __name__ == "__main__":
    main()  
