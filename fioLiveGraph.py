#Standard Libs 
import platform,subprocess

def htmlMain(title,workloadsContainerHTML): 
    systemName = ' '.join(platform.linux_distribution()) 
    fioVers = subprocess.check_output('fio -v',shell=1).decode('utf-8').split('-')[1]    
    data = """  
<html>
<head>
<script type="text/javascript" src="js/highcharts.js"></script>
<script type="text/javascript" src="js/highcharts-more.js"></script>
<script type="text/javascript" src="js/solid-gauge.js"></script>
<script>
var start = new Date();
function timer() {{
    var now = new Date() 
    var ms = now - start;
    var s = ms/1000;
    var h = parseInt(s/3600);
    s = s % 3600;
    var m = parseInt(s/60);
    s = parseInt(s % 60);
    s = addZerosTime(s)
    m = addZerosTime(m)
    timers = document.getElementsByClassName('timer');
    for ( var i = 0; i < timers.length; i++) {{    
        timers.item(i).innerHTML = h + ":" + m + ":" + s;
        }}
    var t = setTimeout(timer, 1000);
}}
function curTime() {{
    var today = new Date();
    var h = today.getHours();
    var m = today.getMinutes();
    var s = today.getSeconds();
    m = addZerosTime(m);
    s = addZerosTime(s);
    document.getElementById('clock').innerHTML =
    h + ":" + m + ":" + s;
    var t = setTimeout(curTime, 1000);
}}
function addZerosTime(i) {{
    if (i < 10) {{i = "0" + i}};  // add zero in front of numbers < 10
    return i;
}}
</script>
</head>
<body onload="curTime();timer();">
<br/>
    <h2 style="text-align:center">
    {graphTitle}
    </h2>
{workloadsContainerHTML} 
<div style="text-align:center">
    <div style="display:inline;">{systemName} / FIO v{fio} / </div>
    <div id="clock" style="display:inline;"></div>
</div>
</body>
""".format(graphTitle=title,workloadsContainerHTML=workloadsContainerHTML,systemName=systemName,fio=fioVers)
    return data
        
        
def generateWorkloadContainers(workloadData): 
    ID = 0
    workloadsContainerHTML = ''
    for workload in workloadData: 
        graphsHTML = ''
        for graph in ['IOPS','MBPS','QoS']:
            if graph in workload['liveGraphs']:
                workload['liveGraphs'][graph] = ID
                graphsHTML += """
<td>
<div id="u{ID}container" style="max-width:100%; height: 100%; margin: 0 auto">
</div>
</td>
""".format(ID=ID)
                ID += 1                
                
        if graphsHTML: 
            workloadsContainerHTML += """
<table style="width:100%">
<thead>
<tr>
<td style="text-align:right; font-size:20px; width:33%">{File}</td> 
<td style="text-align:center; font-size:12px; width:33%">{Title}</td>
<td style="text-align:left; width:33%">Elapsed time:  <div class='timer'></div></td>
</tr>
</thead>
<tbody>
<tr>
        {graphsHTML}    
</tr>
</tbody>
</table>
""".format(graphsHTML=graphsHTML,Title=workload['wlDescription'],File=workload['filename']) 
    return workloadsContainerHTML


def generateGraphJS(trackingFile,workloadTitle,liveGraphs,liveDisplay):
    graphJS = ''
    for graphType in liveGraphs:
        containerID = liveGraphs[graphType]
        units = {'IOPS':'IOPS','MBPS':'MBPS','QoS':'mS'}[graphType]
        
        if graphType in ['IOPS','MBPS']:    
            yAxis = 'min:0,tickAmount: 2,'
            xAxis = ''
            dataLoc = {'IOPS':1,'MBPS':2}[graphType]
            chartType = 'solidgauge'            
            dataCallback = "callback(xobj.responseText.split(',')[{dataLoc}]);".format(dataLoc=dataLoc)
            dataSeries = """
                {{
                name: '{units}',
                data: [0],
                dataLabels: {{
                    format: '<div style="text-align:center"><span style="font-size:40px;color:' +
                        ((Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black') + 
                        '">{{y}}</span><br/>' +
                        '<span style="font-size:24px;color:#999999">{units}</span></div>'}},
                tooltip: {{
                    valueSuffix: '{units}'
                    }}
                }},
                """.format(units=units)            
            updateDataFunc = """
                var point = chart.series[0].points[0],
                    newVal, newJSON;
                    loadperf{ID}(function(response) {{
                        newVal = parseFloat(response);
                        point.update(newVal);
                    }});
                point.update(newVal);            
                """.format(ID=containerID)
        
        
        elif graphType == 'QoS':
            yAxis = "type: 'logarithmic', min:0.1, title:{text:'Completion Latency (mS)'},"
            xAxis = "categories: ['{}']".format(liveDisplay['QoS_percentiles'].replace(':',"','"))
            xAxis += ",\ntitle:{text:'Latency QoS Percentile'}"
            chartType = 'column'
            dataCallback = '''
                resp = xobj.responseText;
                callback(resp.slice(resp.indexOf('{'),resp.lastIndexOf('}')+1));
                '''
            dataSeries = """
                {{
                name: 'Read',
                data: [1],
                dataLabels: {{
                    format: '<div style="text-align:center"><span style="font-size:40px;color:' +
                        ((Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black') + 
                        '">{{y}}</span><br/>' +
                        '<span style="font-size:24px;color:#999999">{units}</span></div>'}},
                tooltip: {{
                    valueSuffix: '{units}'
                    }}
                }},
                {{
                name: 'Write',
                data: [1],
                dataLabels: {{
                   format: '<div style="text-align:center"><span style="color:' +
                        ((Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black') + 
                        '">{{y:.3f}}</span>' +
                        '<span style="color:#999999">{units}</span></div>'}},
                tooltip: {{
                    valueSuffix: '{units}'
                    }}
                }},
                """.format(units=units)             
            updateDataFunc = """
                var rd = chart.series[0], wr=chart.series[1]
                    newRd = [], newWr = [];
                    loadperf{ID}(function(response) {{
                        var data = JSON.parse('['+response.replace(/'/g,'"')+']');
                        for (var key in data[0]) {{
                            newRd.push(data[0][key]/1000000); 
                        }}
                        for (var key in data[1]) {{
                            newWr.push(data[1][key]/1000000); 
                        }}
                    }});    
                newRd.sort(function(a,b){{return a-b}});
                newWr.sort(function(a,b){{return a-b}});
            rd.update({{data:newRd}});
            wr.update({{data:newWr}});
                """.format(ID=containerID)
        
        graphJS += """
<script type="text/javascript">
function loadperf{ID}(callback) {{   

    var xobj = new XMLHttpRequest();
        xobj.overrideMimeType("text/csv");
    xobj.open('GET', '{File}', false); 
    xobj.onreadystatechange = function () {{
            // console.log(xobj.responseText);
            {dataCallback}

    }};
    xobj.send();  
}}

Highcharts.chart('u{ID}container', {{

    chart: {{
        type: '{chartType}'
    }},

    pane: {{
        size: '100%',
        startAngle: -120,
        endAngle: 120,
        background: {{
            backgroundColor: (Highcharts.theme && Highcharts.theme.background2) || '#EEE',
            innerRadius: '60%',
            outerRadius: '100%',
            shape: 'arc'
        }}
    }},
    
    xAxis:{{
        {xAxis} 
    }},
    
    title: {{
        text: undefined
    }},

    tooltip: {{
        enabled: false
    }},

    credits: {{
        enabled: false
    }},

    // the value axis
    yAxis: {{
        {yAxis}
        title: {{ text: '{units}' }},
        stops: [
            [0.2, '#DF5353'], // red
            [0.5, '#DDDF0D'], // yellow
            [0.8, '#33CC33'] // green
        ],
        lineWidth: 0,
        minorTickInterval: null,
        title: {{
            y: -70
        }},
        labels: {{
            y: 30,
            style: {{
                fontSize: "20px"
            }}
        }}
    }},

    plotOptions: {{
        solidgauge: {{
            dataLabels: {{
                y: -25,
                borderWidth: 0,
                useHTML: true
            }}
        }},
        column: {{
            dataLabels: {{
                y: -35,
                borderWidth: 0,
                useHTML: true,
                enabled: true,
                rotation: -90,
                crop: false,
                overflow: "none"
            }}
        }}
    }},

    series: [
        {dataSeries}
    ]

}},
// Add some life
function (chart) {{
    if (!chart.renderer.forExport) {{
        setInterval(function () {{
            {updateDataFunc}
        }}, 1000);
    }}
}});
</script>
""".format(File=trackingFile,
            ID=containerID,
            units=units,
            dataCallback=dataCallback,
            chartType=chartType,
            updateDataFunc=updateDataFunc,
            xAxis=xAxis,
            yAxis=yAxis,
            dataSeries=dataSeries
            )
    
    
    return graphJS


def createHTMLpage(outputName, workloadData, liveDisplay, title='SK hynix SSD benchmark live demo workloads'):
    """
    Automatically generate JS-based webpage for displaying benchmarking live results from fio running workloads
    
    Arguments: 
        displayWL (list of dict): Each dict entry in list is one workload/display graph containing elements:
            keys: {filename, targetDescription, wlDescription, datatype}
        
    Output:
        fioDisplay.html 
    """
    HTMLpage = ''
    workloadsContainerHTML = generateWorkloadContainers(workloadData)
    HTMLpage = htmlMain('{0}'.format(title),workloadsContainerHTML)    
    
    for workload in workloadData:
        if workload['liveGraphs']: #if livegraphs are recorded for the workload
            HTMLpage += generateGraphJS(
               workload['outputTrackingFileL'],
               workload['wlDescription'],
               workload['liveGraphs'],
               liveDisplay)

    f = open(outputName,'w')
    f.write(HTMLpage)
    f.close()        

'''    
def main():
    createHTMLpage('')
    
if __name__ == "__main__":
    main()
'''

