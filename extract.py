import os

def importExtractWorkloadData():
    """
    Find fio files from pre-set pattern *.fio and parse the critical command line parameters
        Additionally, check for duplicate file content(via md5), or incomplete workload files 
    
    Parameters: 
        None
        
    Returns: 
        workloadData (list of dicts): list of lists containing one workload file per entry;
            [   {'filename'='*.fio',
                'bs'=%bs1,'rw'='rw1',
                'readPercent'=%rwmixread1,
                'numJobs'=%numjobs1,
                'iodepth'=%iodepth1,
                'size'='%size1', 
                runtime1},
                {filename2, bs2, ...}
            ]
    """
    files = os.listdir()
    workloadFiles = []
    for filename in files:
        if filename.endswith('.fio'):
            workloadFiles.append(filename)     
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
            if not rw: 
                rw = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('readwrite')][0]
            if rw in ['read','write','rw','readwrite']:
                seqRand = 'seq'
            elif rw in ['randread','randwrite','randrw']:
                seqRand = 'rand'
            if rw in ['read','randread']:
                readPercent = 100
            elif rw in ['write','randwrite']:
                readPercent = 0
            else: 
                readPercent = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('rwmixread')][0])
            readPercent = '{0}/{1}'.format(readPercent,100-readPercent)
            numJobs = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('numjobs')][0])
            iodepth = int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('iodepth')][0])
            size = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('size')][0]
            if int([x.split('=')[1].strip() for x in workloadFileLines if x.startswith('time_based')][0])   :
                time = [x.split('=')[1].strip() for x in workloadFileLines if x.startswith('runtime')][0]
            else: 
                time = 0         
            workloadData.append({'filename':workload_file,
                                    'target':target,
                                    'bs':bs,
                                    'rw':rw,
                                    'seqRand':seqRand,
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
            print ('\n*** ERROR: Could not parse complete data from WL file: {0} ***'.format(workload_file))
            print ('This file must be deleted or the program will exit.')
            if input ('Do you want to delete this file?') in ['Y','y']:
                os.remove(workload_file)
            else:
                if not debug: 
                    sys.exit()
    if not workloadFiles:
        print ('*** Workload list EMPTY! ***')
    return workloadData
