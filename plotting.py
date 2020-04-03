import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from datetime import datetime


# This package is imported by power-monitor.py
# plot_data will be called when power-monitor.py is started in debug mode. See the documentation for more information about debug mode.

webroot = '/var/www/html'


def plot_data(samples, title):
    # Plots the raw sample data from the individual CT channels and the AC voltage channel.
    ct0 = samples['ct0']
    ct1 = samples['ct1']
    ct2 = samples['ct2']
    ct3 = samples['ct3']
    voltage = samples['voltage']
    x = [x for x in range(1, len(ct0))]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=x, y=ct0, mode='lines', name='CT0'), secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=ct1, mode='lines', name='CT1'), secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=ct2, mode='lines', name='CT2'), secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=ct3, mode='lines', name='CT3'), secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=voltage, mode='lines', name='AC Voltage'), secondary_y=True)

    if 'vWave_ct0' in samples.keys():
        fig.add_trace(go.Scatter(x=x, y=samples['vWave_ct0'], mode='lines', name='New V wave (ct0)'), secondary_y=True)
        fig.add_trace(go.Scatter(x=x, y=samples['vWave_ct1'], mode='lines', name='New V wave (ct1)'), secondary_y=True)
        fig.add_trace(go.Scatter(x=x, y=samples['vWave_ct2'], mode='lines', name='New V wave (ct2)'), secondary_y=True)
        fig.add_trace(go.Scatter(x=x, y=samples['vWave_ct3'], mode='lines', name='New V wave (ct3)'), secondary_y=True)
        fig.add_trace(go.Scatter(x=x, y=samples['vWave_ct4'], mode='lines', name='New V wave (ct4)'), secondary_y=True)


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