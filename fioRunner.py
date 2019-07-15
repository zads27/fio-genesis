#!/usr/bin/python3

#Standard Libs
import subprocess,os,re,datetime,webbrowser

#Installed Libs

#Custom Libs
import fioLiveGraph,FIOgenesis



debug = 0

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
                '--output-format=json'],
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
        if units in ['MiB','MB']:
            return v * 1.024 * 1.024    # Mbps
        elif units in ['KiB','KB']:
            return v * 0.001024    # Mbps
        elif units == 'k':
            return v*1000            # IOPS
        elif units == '':
            return v
    else:
        raise ValueError('unknown units %s' % mstring)   

   
def get_value(line):
    """Parse continuous fio output and get requested value"""
    # fio 2.16-1 format:
    #   Jobs: 1 (f=1): [R(1)] [37.5% done] [727.0MB/0KB/0KB /s] [727/0/0 iops] [eta 00m:10s]
    # fio ?? format
    #   jobs: 1 (f=1): [R(1)][1.2%][r=1733MiB/s,w=0KiB/s][r=13.9k,w=0 IOPS][eta 59m:17s]
    # fio 3.12 format:
    #   Jobs: 1 (f=1): [R(1)][40.0%][r=409MiB/s][r=409 IOPS][eta 00m:09s]
    result = {'percentComplete':'0',
                'iops':'0',
                'mbps':'0',
                'eta':'Unknown'}
    pattern = r'(\[[^\]]+\])'    
    m = re.findall(pattern,line)
    if m:
        m.pop(0)
        result['percentComplete'] = re.search('\[([0-9]+[.0-9]+)%',m[0]).group(1)
        result['mbps'] = '{0:.1f}'.format(sum([to_number(x) for x in re.findall('[0-9.]+[MmKk][Ii]*[Bb]',m[1])]))
        #array of 1 or more throughput numbers suffixed with M or K
        result['iops'] = '{0:2f}'.format(sum([to_number(x) for x in re.findall('[0-9.]+[Kk]*',m[2])]))
        #array of 1 or more iops numbers (may be suffixed with k)
        result['eta'] = re.search('\[eta\s+([0-9hms:]+)',m[3]).group(1)
    return result  
                
'''
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
'''
    
    
def progBar(percentage):
    """
    Create 'shaded' progress bar string of variable length
    
    Parameters:
        percentage (float or int): percentage completion of task/progress
    
    Returns: 
        String of length 'barLength' (hardcoded) shaded according to progress percentage
    """
    barLength = 40
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
    

def runFIO(workloadData,liveDisplay):
    """
    Find files matching pattern WL*.fio in ./currentWL
    
    Inputs: 
        User keyed inputs from context menus
    
    Outputs:
        Print queued workload details and running workload status/progress/performance
    
    Internal structures:
         Store in workloads object

    """ 
    for wlDict in workloadData:
        print ('{0}{1}'.format('Starting Workload:',wlDict['filename']))
        runFIOprocess(wlDict)

    if liveDisplay:
        fioLiveGraph.createHTMLpage(workloadData,title='Live FIO Benchmark display')
        webbrowser.open('fioLiveGraph.html',new=0)
    
    print('\n'*(len(workloadData)+2))              
    while any(wl['percentComplete'] != 100 for wl in workloadData):
        for workload in workloadData:
            line = workload['process'].stdout.readline() 
            if line[0:4] == 'Jobs':
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
                        )) #3 significant figures
                print('\x1b[A'*(len(workloadData)+3)+'\r') #move caret back to beginning of table
                print(FIOgenesis.createWorkloadDF(workloadData,0)) #reprint workload monitor table
            if line == '' and workload['process'].poll() is not None: 
                workload['percentComplete'] = 100   
                workload['outputTrackingFileH'].close()
    
    print('\x1b[A'*(len(workloadData)+3)+'\r') #move caret back to beginning of table
    print(FIOgenesis.createWorkloadDF(workloadData,0)) #reprint workload monitor table
    
    print('FIO-run Complete')        
    

       
   
