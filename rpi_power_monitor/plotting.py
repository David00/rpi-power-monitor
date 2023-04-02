import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# This package is imported by power-monitor.py and is used to create interactive HTML plots of the raw data collected by the power monitor.

webroot = '/var/www/html'


def plot_data(samples, title, sample_rate, enabled_channels, *args, **kwargs):
    """ Plots the raw sample data from the individual CT channels and the AC voltage channel. """
    
    # x-axis labels
    x = [x for x in range(1, len(samples[f'ct{enabled_channels[0]}']))]

    # Make plot for all enabled CT channels
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for chan_num in enabled_channels:

        fig.add_trace(go.Scatter(x=x, y=samples[f'ct{chan_num}'], name=f'CT {chan_num}'))
        fig.add_trace(go.Scatter(x=x, y=samples[f'v{chan_num}'], name=f'AC Voltage ({chan_num})'), secondary_y=True)

    fig.update_layout(
        title=title,
        xaxis_title='Sample Number',
        yaxis_title='ADC Value (CTs)',
        yaxis2_title="ADC Value (Voltage)",
    )

    div = plotly.offline.plot(fig, show_link=False, output_type='div', include_plotlyjs='cdn')
    home_link = '<a href="/">Back to Index</a>'
    div = home_link + div
    if sample_rate:
        sample_rate = f'<p>Sample Rate: {sample_rate} KSPS</p>'
        div += sample_rate

    with open(f"{webroot}/{title.replace(' ', '_')}.html", 'w') as f:
        f.write(div)