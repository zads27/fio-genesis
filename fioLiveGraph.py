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
function startTime() {{
    var today = new Date();
    var h = today.getHours();
    var m = today.getMinutes();
    var s = today.getSeconds();
    m = checkTime(m);
    s = checkTime(s);
    document.getElementById('clock').innerHTML =
    h + ":" + m + ":" + s;
    var t = setTimeout(startTime, 500);
}}
function checkTime(i) {{
    if (i < 10) {{i = "0" + i}};  // add zero in front of numbers < 10
    return i;
}}
</script>
</head>
<body onload="startTime()">
<br/>
    <h2 style="text-align:center">
    {graphTitle}
    </h2>
{workloadsContainerHTML} 
<div style="text-align:center">
    <div style="display:inline;">{systemName} / FIO v{fio} / </div>
    <!-- <div id="clock" style="display:inline;"></div> -->
</div>
</body>
""".format(graphTitle=title,workloadsContainerHTML=workloadsContainerHTML,systemName=systemName,fio=fioVers)
    return data
        
        
def generateWorkloadContainers(workloadData): 
    ID = 0
    workloadsContainerHTML = ''
    for workload in workloadData: 
        graphsHTML = ''
        for graph in workload['liveGraphs']:
            graphsHTML += """
<td>
<div id="u{ID}container" style="max-width:100%; height: 100%; margin: 0 auto">
</div>
<td>
""".format(ID=ID)
            workload['liveGraphs'][graph] = ID
            ID += 1
        if graphsHTML: 
            workloadsContainerHTML += """
<table style="width:100%">
<thead>
<tr>
<td style="text-align:right; font-size:20px; width:33%">{File}</td> 
<td style="text-align:left; font-size:12px; width:33%">{Title}</td>
<td style="width:33%"> </td>
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


def generateGraphJS(resultFile,workloadTitle,liveGraphs):
    graphJS = ''
    for graphType in liveGraphs:
        containerID = liveGraphs[graphType]
        dataloc = {'IOPS':1,'MBPS':2}
        if graphType in dataloc:    
            perf = dataloc[graphType]
            graphJS += """
<script type="text/javascript">
function loadperf{ID}(callback) {{   

    var xobj = new XMLHttpRequest();
        xobj.overrideMimeType("text/csv");
    xobj.open('GET', '{File}', false); // Replace 'my_data' with the path to your file
    xobj.onreadystatechange = function () {{
          //if (xobj.readyState == 4 && xobj.status == 200) {{
            // Required use of an anonymous callback as .open will NOT return a value but simply returns undefined in asynchronous mode
            // console.log(xobj.responseText);
            callback(xobj.responseText.split(',')[{perf}]/1000);
          //}}
    }};
    xobj.send();  
}}

Highcharts.chart('u{ID}container', {{

    chart: {{
        type: 'solidgauge'
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
        min: 0,
        max: 200,
        title: {{ text: '{units}' }},
        stops: [
            [0.2, '#DF5353'], // red
            [0.5, '#DDDF0D'], // yellow
            [0.8, '#33CC33'] // green
        ],
        lineWidth: 0,
        minorTickInterval: null,
        tickAmount: 2,
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
        }}
    }},

    series: [{{
        name: '{units}',
        data: [90],
        dataLabels: {{
            format: '<div style="text-align:center"><span style="font-size:40px;color:' +
                ((Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black') + '">{{y}}</span><br/>' +
                   '<span style="font-size:24px;color:#999999">{units}</span></div>'
        }},
        tooltip: {{
            valueSuffix: '{units}'
        }}
    }}]

}},
// Add some life
function (chart) {{
    if (!chart.renderer.forExport) {{
        setInterval(function () {{
            var point = chart.series[0].points[0],
                newVal, newJSON;
                loadperf{ID}(function(response) {{
                    newVal = parseFloat(response);
                    point.update(newVal);
                }});
            point.update(newVal);

        }}, 1000);
    }}
}});
</script>
""".format(File=resultFile,ID=containerID,perf=perf,units=('KIOPS' if graphType == 'IOPS' else 'MBPS'))
    
    
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
    
    for displayItem in workloadData:
        if displayItem['liveGraphs']: #if livegraphs are recorded for the workload
            HTMLpage += generateGraphJS(
               displayItem['file'],
               displayItem['wlDescription'],
               displayItem['liveGraphs'])

    f = open(outputName,'w')
    f.write(HTMLpage)
    f.close()        

'''    
def main():
    createHTMLpage('')
    
if __name__ == "__main__":
    main()
'''

