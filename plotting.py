import plotly
import plotly.graph_objs as go
from datetime import datetime


# This package is imported by power-monitor.py
# plot_data will be called when power-monitor.py is started in debug mode. See the documentation for more information about debug mode.

webroot = '/var/www/html'


def plot_data(samples, title):
    # Plots the raw sample data from the individual CT channels and the 
    ct0 = samples['ct0']
    ct1 = samples['ct1']
    ct2 = samples['ct2']
    ct3 = samples['ct3']
    voltage = samples['voltage']


    x = [x for x in range(1, len(ct0))]

    fig = go.Figure(data=go.Scatter(x=x, y=ct0, mode='lines', name='CT0'))
    fig.add_trace(go.Scatter(x=x, y=ct1, mode='lines', name='CT1'))
    fig.add_trace(go.Scatter(x=x, y=ct2, mode='lines', name='CT2'))
    fig.add_trace(go.Scatter(x=x, y=ct3, mode='lines', name='CT3'))
    fig.add_trace(go.Scatter(x=x, y=voltage, mode='lines', name='AC Voltage'))

    fig.update_layout(
        title=title,
        xaxis_title='Sample Number',
        yaxis_title='ADC Value'        

    )

    div = plotly.offline.plot(fig, show_link=False, output_type='div', include_plotlyjs='cdn')
    home_link = '<a href="/">Back to Index</a>'
    div = home_link + div

    with open(f"{webroot}/{title.replace(' ', '_')}.html", 'w') as f:
        f.write(div)