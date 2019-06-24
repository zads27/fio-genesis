#!/bin/bash/python3
import glob
import plotly.offline as py
import plotly.graph_objs as go
import plotly.figure_factory as FF
import dash_core_components as dcc
import time
import pandas as pd
import webbrowser

data = []
for filename in glob.glob('*.dat'):
	df = pd.read_csv(filename)
	#sample_data_table = FF.create_table(df.head())
	#py.plot(sample_data_table, filename='sample-data-table')
	trace = go.Scatter(
                    x=df['timestamp'], y=df['performance'], # Data
                    mode='lines', name=filename # Additional options
                   )
	data.append(trace)

layout = go.Layout(title='Simple Plot from csv data',
                   plot_bgcolor='rgb(230, 230,230)')

fig = go.Figure(data=data, layout=layout)

py.plot(fig, filename='results.html',auto_open=False)
webbrowser.open('results.html', new=0)
