#!/usr/bin/python
import subprocess,sys,os
from pprint import pprint
debug = 1
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

def find_drives():
    if 'linux' in sys.platform:
        block_dev = subprocess.check_output('lsblk')
        block_dev = [x for x in block_dev.splitlines() if x[0] in ['n','s']]
        block_dev = [x.split()[0] for x in block_dev]
    else:
        block_dev = subprocess.check_output('wmic diskdrive get name,model')
        block_dev = [x.decode('utf-8') for x in block_dev.splitlines() if x]
        block_dev = [x for x in block_dev if '\\' in x]
    print('Target Drives available:')
    pprint(block_dev)
    return(block_dev)

def print_workloads(workload_list):
    for workload_file in workload_list:
        iodepth = ''
        file = open(workload_file,'r')
        test = file.readlines()
        column_align = '{0:<30}{1}'
        print ('\n'+column_align.format('Workload File found:',workload_file))
        print (column_align.format('Target:',[x.split('=')[1].strip() for x in test if x.startswith('filename')][0]))
        print (column_align.format('IO BlockSize:',[x.split('=')[1].strip() for x in test if x.startswith('bs')][0]))
        readPercent = int([x.split('=')[1].strip() for x in test if x.startswith('rwmixread')][0])
        print (column_align.format('R/W distribution:','{0}% Read, {1}% Write'.format(readPercent,(100-readPercent))))
        numJobs = int([x.split('=')[1].strip() for x in test if x.startswith('numjobs')][0])
        iodepth = int([x.split('=')[1].strip() for x in test if x.startswith('iodepth')][0])
        print (column_align.format('Queue Depth per job:','{0}'.format(iodepth)))
        print (column_align.format('Number of jobs:','{0}'.format(numJobs)))
        print (column_align.format('Total queue depth:','{0}'.format(numJobs*iodepth)))
    print('')
    
def delete_workloads(deletion_list):
    if input("\n*** This will delete all previous jobs, Are you sure? ***") in ["Y","y"]:
        for file in deletion_list:
            if not debug:
                os.delete(file)
            print ('{0:<20}{1}'.format('Deleting file:',file))
        print('')

        
def main():
    
    workloads = []
    files = os.listdir()
    for object in files:
        if object.startswith('WL') and object.endswith('.fio'):
            workloads.append(object)
    print_workloads(workloads) 
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
    if keep_Workloads:
        print ('Running FIO jobs', end='', flush=1)
        import time
        for x in range(3):
            print ('.', end='', flush=1)
            time.sleep(1)
        #runFIO
        sys.exit()
    else:
        delete_workloads(workloads)
        targets = find_drives()
        while input("Do you want to add a workload?") in ["Y","y"]:
            workloads.append(fio_selector.create_fio(targets))
            print("Current queued workloads:")
            pprint(workloads)
        for job in range(len(workloads)):
            f = open('WL{:1d}.fio'.format(job),'w')
            f.write('test')
            f.close()


if __name__ == "__main__":
    main()  
