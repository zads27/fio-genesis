import os,sys,platform,subprocess


def htmlMain(title,workloads): 
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
{workloads} 
<div style="text-align:center">
    <div style="display:inline;">{systemName} / FIO v{fio} / </div>
    <!-- <div id="clock" style="display:inline;"></div> -->
</div>
</body>
""".format(graphTitle=title,workloads=workloads,systemName=systemName,fio=fioVers)
    return data


def generateContainers(displayWL):
    pos = 'left' 
    workloadHTML = ''
    for ID in range(len(displayWL)):
        workloadHTML += graphContainer(pos,'{}'.format(ID))
        pos = ('right' if (pos == 'left') else 'left')
    return (workloadHTML)
        
        
def graphContainer(position,containerID): 
    container = """<div id="u{ID}" style="display:inline; float:{position}; width:48%">
    <div id="u{ID}container" style="width: 400px; height: 350px; margin: 0 auto"></div>
</div>
""".format(position=position,ID=containerID) 
    return container


def generateGraph(resultFile,workloadTitle,containerID):
    return """
<script type="text/javascript">
function loadiops(callback) {{   

    var xobj = new XMLHttpRequest();
        xobj.overrideMimeType("application/json");
    xobj.open('GET', '{resultFile}', false); // Replace 'my_data' with the path to your file
    xobj.onreadystatechange = function () {{
          //if (xobj.readyState == 4 && xobj.status == 200) {{
            // Required use of an anonymous callback as .open will NOT return a value but simply returns undefined in asynchronous mode
            // console.log(xobj.responseText);
            callback(xobj.responseText);
          //}}
    }};
    xobj.send();  
}}

Highcharts.chart('u{ID}container', {{

    chart: {{
        type: 'solidgauge'
    }},

    title: {{
        text: '{workloadTitle}'
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

    tooltip: {{
        enabled: false
    }},

    credits: {{
        enabled: false
    }},

    // the value axis
    yAxis: {{
        min: 0,
        max: 120,
        title: {{ text: 'KIOPS' }},
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
        name: 'KIOPS',
        data: [90],
        dataLabels: {{
            format: '<div style="text-align:center"><span style="font-size:40px;color:' +
                ((Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black') + '">{{y}}</span><br/>' +
                   '<span style="font-size:24px;color:#999999">KIOPS</span></div>'
        }},
        tooltip: {{
            valueSuffix: 'KIOPS'
        }}
    }}]

}},
// Add some life
function (chart) {{
    if (!chart.renderer.forExport) {{
        setInterval(function () {{
            var point = chart.series[0].points[0],
                newVal, newJSON;
                loadiops(function(response) {{
                    newVal = parseFloat(response);
                    point.update(newVal);
                }});
            point.update(newVal);

        }}, 3000);
    }}
}});
</script>
""".format(resultFile=resultFile,workloadTitle=workloadTitle,ID=containerID)

def createHTMLpage(displayWL, title='SK hynix SSD benchmark demo workloads'):
    """
    Automatically generate JS-based webpage for displaying benchmarking live results from fio running workloads
    
    Arguments: 
        displayWL (list of dict): Each dict entry in list is one workload/display graph containing elements:
            keys: {filename, targetDescription, wlDescription, datatype}
        
    Output:
        fioDisplay.html 
    """
    displayWLsample= [
        {'filename':'quartz-4krr.txt',
        'targetDescription':'SK hynix SE4011 SATA 960GB SSD',
        'wlDescription':'4k Random Read/Write 70/30',
        'datatype':'IOPS'},
        
        {'filename':'quartz-4krw.txt',
        'targetDescription':'SK hynix SE5031 SATA 3840GB SSD',
        'wlDescription':'4k Random Read/Write 100/0',
        'datatype':'QoS'},
        
        {'filename':'quartz-4krr.txt',
        'targetDescription':'SK hynix SE4011 SATA 960GB SSD',
        'wlDescription':'4k Random Read/Write 70/30',
        'datatype':'IOPS'},
        
        {'filename':'quartz-4krw.txt',
        'targetDescription':'SK hynix SE5031 SATA 3840GB SSD',
        'wlDescription':'4k Random Read/Write 100/0',
        'datatype':'QoS'}
        
        ]
        
    if not displayWL:
        displayWL = displayWLsample
    HTMLpage = ''
    workloadsContainerHTML = generateContainers(displayWL)
    HTMLpage = htmlMain('{0}'.format(title),workloadsContainerHTML)    
    
    for displayItem in displayWL:
       HTMLpage += generateGraph(displayItem['outputTrackingFile'],displayItem['wlDescription'],displayWL.index(displayItem))
    
    f = open('fioDisplay.html','w')
    f.write(HTMLpage)
    f.close()        

'''    
def main():
    createHTMLpage('')
    
if __name__ == "__main__":
    main()
'''

