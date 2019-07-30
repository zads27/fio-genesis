#!/usr/bin/python3

#Standard Libs
import subprocess,os,re,datetime,webbrowser
from threading import Thread
import json

#Installed Libs
from pprint import pprint

#Custom Libs
import fioLiveGraph,FIOgenesis



debug = 0

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
            return v * 0.001024         # Mbps
        elif units == 'k':
            return v*1000               # IOPS
        elif units == '':
            return v
    else:
        raise ValueError('unknown units %s' % mstring)   

   
def get_value(line):
    """
    # Input: String passed from FIO stdout
    #
    # Output: parsed dict of performance/eta/percentage values 
    #
    # fio 2.16-1 format:
    #   Jobs: 1 (f=1): [R(1)] [37.5% done] [727.0MB/0KB/0KB /s] [727/0/0 iops] [eta 00m:10s]
    # fio ?? format
    #   jobs: 1 (f=1): [R(1)][1.2%][r=1733MiB/s,w=0KiB/s][r=13.9k,w=0 IOPS][eta 59m:17s]
    # fio 3.12 format:
    #   Jobs: 1 (f=1): [R(1)][40.0%][r=409MiB/s][r=409 IOPS][eta 00m:09s]
    """
    result = {'percentComplete':0,
                'iops':'0',
                'mbps':'0',
                'eta':'-'}
    pattern = r'(\[[^\]]+\])'    
    m = re.findall(pattern,line)
    if m:
        m.pop(0)
        result['percentComplete'] = float(re.search('\[([0-9]+[.0-9]+)%',m[0]).group(1))
        result['mbps'] = '{0:.1f}'.format(sum([to_number(x) for x in re.findall('[0-9.]+[MmKk][Ii]*[Bb]',m[1])]))
        #array of 1 or more throughput numbers suffixed with M or K
        result['iops'] = '{0:2d}'.format(int(sum([to_number(x) for x in re.findall('[0-9.]+[Kk]*',m[2])])))
        #array of 1 or more iops numbers (may be suffixed with k)
        result['eta'] = re.search('\[eta\s+([0-9dhms:]+)',m[3]).group(1)
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
    progress = u'\u2588'*int(percentage*barLength/100)
    segmentSpan = 100/barLength
    segmentRemainder = percentage % barLength
    if segmentRemainder:
        if segmentRemainder < (segmentSpan/3):
            progress += u'\u2591' #light shade
        elif segmentRemainder < (2*segmentSpan/3):
            progress += u'\u2592' #medium shade
        elif percentage < 100:
            progress += u'\u2593' #dark shade
    progress += '-'*(barLength-len(progress))
    return progress
    
    
def startFIOprocess(workload, liveDisplayOptions):                  
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
        fio_command = ['sudo','fio',workload['filename']]
        if 'QoS' in workload['liveGraphs']:
            fio_command.append('--status-interval=1')
            fio_command.append('--output-format=json')
            fio_command.append('--percentile_list={}'.format(liveDisplayOptions['QoS_percentiles']))
        else:
            fio_command.append('--output=results/{}'.format(workload['filename'].split('.')[0]+'.log'))
            fio_command.append('--eta=always')
            fio_command.append('--eta-newline=250ms')
            fio_command.append('--output-format=normal')
                                    
        fioThread = subprocess.Popen(
            fio_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=False)
        workload['process'] = fioThread
        workload['wlDescription'] = ' <br>'.join([
                        'Target= {}'.format(workload['target']),
                        'Block= {}'.format(workload['bs']),
                        'Rnd/Seq= {}'.format(workload['rw']),
                        'Rd/Wr= {}'.format(workload['readPercent'])
                        ])
        workload['targetDescription'] = 'SK hynix drive'
        workload['outputTrackingFileH'] = open('results/{0}.dat'.format(workload['filename'].split('.')[0]),'w')
        workload['outputTrackingFileH'].write('timestamp,iops,mbps\n')  
        workload['outputTrackingFileL'] = workload['outputTrackingFileH'].name +'live'      
    except Exception as e:
        print('startFIOprocess error: {0}'.format(e))


def updateStatus(workload): 
    jsonBuf = ''
    while True:    
        line = workload['process'].stdout.readline()
        if 'QoS' in workload['liveGraphs']:
            if (line == '{\n') or jsonBuf:
                jsonBuf += line
            if  jsonBuf[-3:] == '\n}\n':
                jsonFrame = json.loads(jsonBuf) 
                
                eta = jsonFrame['jobs'][0]['eta']
                workload['eta'] = str(datetime.timedelta(seconds=eta)) if eta < 1000000 else '0'
                #create fake percentage remaining? 
                workload['status'] = 'Runnning'
                iops = int(jsonFrame['jobs'][0]['read']['iops']+jsonFrame['jobs'][0]['write']['iops'])
                #write to bandwidth log file, live output file, status panel (workload)
                workload['iops'] = str(iops) 
                mbps = (jsonFrame['jobs'][0]['read']['bw']+jsonFrame['jobs'][0]['write']['bw'])/1024
                mbps = str(float('{:.{p}g}'.format(mbps,p=3)))
                workload['mbps'] = mbps
                if 'clat_ns' in jsonFrame['jobs'][0]['read']:
                    #fio 3.12:
                    readQoS = jsonFrame['jobs'][0]['read']['clat_ns']['percentile']
                    writeQoS = jsonFrame['jobs'][0]['write']['clat_ns']['percentile']
                else:
                    #fio 2.16:
                    readQoS = jsonFrame['jobs'][0]['read']['clat']['percentile']
                    writeQoS = jsonFrame['jobs'][0]['write']['clat']['percentile']
                timestamp = datetime.datetime.isoformat(datetime.datetime.now()) 
                data = ('{timestamp},{iops},{mbps}\n'.format(
                        timestamp=timestamp,
                        iops = str(int(float('{:.{p}g}'.format(iops,p=3)))),
                        mbps=mbps))# = str(int(float('{:.{p}g}'.format(mbps,p=3))))
                        #3 significant figures
                workload['outputTrackingFileH'].write(data)
                data = ','.join([data.strip('\n'),str(readQoS),str(writeQoS)]) 
                open(workload['outputTrackingFileL'],'w').write(data)
                jsonBuf = ''           
        else:       
            if line[0:4] == 'Jobs':
                workload.update(get_value(line))
                percent = float(workload['percentComplete'])
                workload['status'] = progBar(percent)+' {0:3}%'.format(int(percent)) 
                iops = int(workload['iops'])
                mbps = int(float(workload['mbps']))
                timestamp = datetime.datetime.isoformat(datetime.datetime.now())
                data = ('{timestamp},{iops},{mbps}\n'.format(
                        timestamp=timestamp,
                        iops = str(int(float('{:.{p}g}'.format(iops,p=3)))),
                        mbps = str(int(float('{:.{p}g}'.format(mbps,p=3))))
                        )) #3 significant figures
                workload['outputTrackingFileH'].write(data)
                open(workload['outputTrackingFileL'],'w').write(data)
                #df.at[workload['filename'],'status'] = workload['status']
        if line == '' and workload['process'].poll() is not None: 
            workload['percentComplete'] = 100   
            workload['outputTrackingFileH'].close()
            if 'QoS' in workload['liveGraphs']: 
                workload['status'] = 'Complete'
            if workload['process'].poll() != 0:
                workload['status'] = 'Error: {}'.format(workload['process'].returncode)
            break


def runFIO(workloadData,liveDisplay):
    """
    Find files matching pattern WL*.fio in ./currentWL
    
    Inputs:     
        workloadData (list): of dict describing workload parameters
    
    Outputs:
        Print queued workload details and running workload status/progress/performance
    
    Internal structures:
         Store in workloads object

    """ 
    if 1:#try:
        df = FIOgenesis.createWorkloadDF(workloadData,2)
        updaters = []
        for workload in workloadData:
            print ('Starting Workload:   {}'.format(workload['filename']))
            startFIOprocess(workload,liveDisplay)
            t = Thread(target=updateStatus, args=(workload,))
            t.start()
            updaters.append(t)
        if liveDisplay:
            liveHtmlFilename = 'fioLiveGraph.html'
            fioLiveGraph.createHTMLpage(liveHtmlFilename,workloadData,liveDisplay)
            try: 
                webbrowser.get('firefox').open(liveHtmlFilename,new=0)
            except:
                webbrowser.open(liveHtmlFilename,new=0)
        print('\n'*(len(workloadData)+3))       
        resetCaret = len(workloadData)+3
        while any(wl['percentComplete'] != 100 for wl in workloadData):
            df = FIOgenesis.createWorkloadDF(workloadData,2)
            print('\x1b[A'*(resetCaret)+'\r') #move caret back to beginning of table
            print(df.set_index('file')) #reprint workload monitor table
        #Update and print completed table
        df = FIOgenesis.createWorkloadDF(workloadData,2)
        print('\x1b[A'*(resetCaret)+'\r') #move caret back to beginning of table
        print(df.set_index('file')) #reprint workload monitor table    
        [t.join() for t in updaters]
        for workload in workloadData:
            workload['process'] = workload['process'].poll()
            if workload['process'] != 0:
                print('\nFIO Error:')
                print(open('results/{}'.format(workload['filename'].split('.')[0]+'.log'),'r').read())

        print('FIO-run Complete')
        
    #except KeyboardInterrupt:
        #print('\nFIO-run Terminated') 
       
   
