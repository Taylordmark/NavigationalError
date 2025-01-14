import dash
from dash.dependencies import Input, Output, State
import plotly.express as px
import dash_bootstrap_components as dbc
import plotly.io as pio
import requests
import json
import boto3
import re
import pandas as pd
from io import StringIO
from dash import Dash, dcc, html, dash_table, Input, Output, State, callback
import base64
import io
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import plotly.express as px
from PIL import Image, ImageOps
import math

from mathystuff import interpolateData, calcError
from appconfig import app, configure_app




configure_app()


# DATA STORAGE CODE HERE

# Store the contents of the truth data upload
@app.callback(
    Output("truth", "data"),
    Input("truth-data", "contents"),
    prevent_initial_call=True
)
def parse_contents_truth(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    truth_row_skip = lambda x: x in list(range(0,4)) + list(range(5, 9))

    if 'csv' in content_type or 'xlsx' in content_type:
        if 'csv' in content_type:
            truth_df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), skiprows=truth_row_skip)

        elif 'xlsx' in content_type:
            truth_df = pd.read_excel(decoded, skiprow)


        truth_df.columns = truth_df.columns.str.strip()
        truth_Data = [truth_df["TIME"],truth_df["LAT84"],truth_df["LONG84"],truth_df["HAE84"]] # Collect only necessary columns
        truth_df = pd.DataFrame(truth_Data)
        truth_df = truth_df.T
        truth_df.columns = ["TIME","LAT84","LONG84","HAE84"]

        truth_df = truth_df.iloc[1:,:]
        
        return truth_df.to_json(date_format='iso', orient='records')
    else:
        return {}

# Store the contents of the bus data upload
@app.callback(
    Output("bus", "data"),
    Input("bus-data", "contents"),
    prevent_initial_call=True
)
def parse_contents_Bus(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if 'csv' in content_type or 'xlsx' in content_type:
        if 'csv' in content_type:
            bus_df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        
        elif 'xlsx' in content_type:
            bus_df = pd.read_excel(decoded)

        bus_Data = [bus_df["TIME"],bus_df["GP0003"]*180,bus_df["GP0004"]*180,bus_df["GP0005"]] # Collect only necessary columns
        bus_df = pd.DataFrame(bus_Data)
        bus_df = bus_df.T
        bus_df.columns = ["TIME","LAT84","LONG84","HAE84"]

        return bus_df.to_json(date_format='iso', orient='records')
    else:
        return {}

# Store the contents of the jam data upload
@app.callback(
    [
        Output("jam", "data"),
        Output("jam-options", "options"),
    ],
    Input("jam-data", "contents"),
    prevent_initial_call=True
)
def parse_contents_jam(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if 'csv' in content_type or 'xlsx' in content_type:
        if 'csv' in content_type:
            jam_df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        
        elif 'xlsx' in content_type:
            jam_df = pd.read_excel(decoded)

        jam_df = jam_df

        return jam_df.to_json(date_format='iso', orient='records'), jam_df.columns[1:]
    else:
        return {}


# Store the contents of the nav updates data upload
@app.callback(
    [
        Output("nav", "data"),
        Output("nav-options", "options"),
    ],
    Input("nav-data", "contents"),
    prevent_initial_call=True
)
def parse_contents_jam(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if 'csv' in content_type or 'xlsx' in content_type:
        if 'csv' in content_type:
            nav_df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        
        elif 'xlsx' in content_type:
            nav_df = pd.read_excel(decoded)

        return nav_df.to_json(date_format='iso', orient='records'), nav_df.columns[1:]
    else:
        return {}

# Store the contents of the heatmap data upload
@callback(
    Output('heatmap', 'data'),
    Input('heatmap-upload', 'contents'),
    prevent_initial_call=True
)
def store_image_data(imij):
    if imij is not None:
        encoded_data = imij.split(',')[1]
        decoded_data = base64.b64decode(encoded_data)
        img_buf = io.BytesIO(decoded_data)
        imij = Image.open(img_buf)
        return imij
    return None

# Error Calculation and Storage
@app.callback(
    [
        Output("error", "data"),
        Output("time_minmax", "data"),
    ],
    [Input("error-button", "n_clicks")],
    [State("bus", "data"), State("truth", "data")],
    prevent_initial_call=True,
)
def calculate_error(n_clicks, contents_bus, contents_truth):
    if n_clicks is None:
        return {}

    df_bus = pd.read_json(contents_bus, orient="records")
    df_truth = pd.read_json(contents_truth, orient="records")

    bus_new, truth_new = interpolateData(df_bus,df_truth) # Interpolate Data
    time_series = list(truth_new["TIME"])
    
    error = [] # Empty error dataframe
    
    for i,time in enumerate(time_series[::1]): # Iterate through each time step in time, calculate error, save error
        bus_TSPI = bus_new[bus_new["TIME"]==time].reset_index(drop=True).to_dict(orient='records')[0] # Gets bus data at single time step instance "time"
        truth_TSPI = truth_new[truth_new["TIME"]==time].reset_index(drop=True).to_dict(orient='records')[0] # Gets truth data at single time step instance "time"
        error.append(list(calcError(bus_TSPI, truth_TSPI))) # Calculate Nav Error and save 
    
    error_df = pd.DataFrame(error,columns=["TIME","slantrange", "RadError", "Ee", "En", "Ez"]) # Convert to dataframe
    print("\tProgress: 100%")

    times_minmax = [min(error_df['TIME']), max(error_df['TIME'])]

    # Return CSV data as bytes along with the filename
    return [error_df.to_json(date_format='iso', orient='records'), times_minmax]


# PLOTS CODE HERE

# Troubleshooting Plot
@app.callback(
    Output("troubleshooting-plot", "figure"),
    [Input("troubleshoot-plot-dropdown", "value")],
    [State("truth", "data"), State("bus", "data")],
    prevent_initial_call=True,
)
def update_graph_0(plot_type, contents_truth, contents_bus):
    if plot_type is None or contents_truth is None and contents_bus is None:
        return {}

    # Initialize empty figures for each graph
    troubleshoot_plot = go.Figure()

    # If bus data not uploaded plot truth only
    if contents_bus is None:

        df_truth = pd.read_json(contents_truth, orient="records")
        
        # If Uncorrected Times Selected plot truth data
        if plot_type == 'Uncorrected Times':
            
            truth_time_ones = np.ones_like(df_truth["TIME"])

            troubleshoot_plot.add_trace(go.Scatter(
                    x=df_truth["TIME"],
                    y= truth_time_ones * 1,
                    name="Truth data"
                ),),
            
            troubleshoot_plot.update_layout(
            title="UC_T Plot", xaxis_title="Time", yaxis_title="Dataset",
            legend_font_size=20,
            )
        
        # If Uncorrected Lat Long Plot Selected plot truth data
        elif plot_type == 'Uncorrected Lat/Long':

            troubleshoot_plot.add_trace(go.Scatter(x=df_truth["LONG84"][::10], y=df_truth["LAT84"][::10], mode="lines"))

            troubleshoot_plot.update_layout(
                title="UC_LL Plot", xaxis_title="Longitude", yaxis_title="Latitude",
                legend_font_size=20
            )

        # If Uncorrected Altitude Plot Selected plot truth data
        elif plot_type == 'Uncorrected Altitude':

            troubleshoot_plot.add_trace(go.Scatter(x=df_truth["TIME"][::10], y=df_truth["HAE84"][::10], mode="lines"))

            troubleshoot_plot.update_layout(
                title="UC_A Plot", xaxis_title="Longitude", yaxis_title="Latitude",
                legend_font_size=20
            )
    
    # If truth data not uploaded plot bus only
    elif contents_truth is None:

        df_bus = pd.read_json(contents_bus, orient="records")
        
        # If Uncorrected Times Selected plot bus data
        if plot_type == 'Uncorrected Times':
            
            bus_time_ones = np.ones_like(df_bus["TIME"])

            troubleshoot_plot.add_trace(go.Scatter(
                    x=df_bus["TIME"],
                    y= bus_time_ones * 1,
                    name="Truth data"
                ),),
            
            troubleshoot_plot.update_layout(
            title="UC_T Plot", xaxis_title="Time", yaxis_title="Dataset",
            legend_font_size=20,
            )
        
        # If Uncorrected Lat Long Plot Selected plot bus data
        elif plot_type == 'Uncorrected Lat/Long':

            troubleshoot_plot.add_trace(go.Scatter(x=df_bus["LONG84"][::10], y=df_bus["LAT84"][::10], mode="lines"))

            troubleshoot_plot.update_layout(
                title="UC_LL Plot", xaxis_title="Longitude", yaxis_title="Latitude",
                legend_font_size=20
            )

        # Uncorrected Altitude Plot
        elif plot_type == 'Uncorrected Altitude':

            troubleshoot_plot.add_trace(go.Scatter(x=df_bus["TIME"][::10], y=df_bus["HAE84"][::10], mode="lines"))

            troubleshoot_plot.update_layout(
                title="UC_A Plot", xaxis_title="Longitude", yaxis_title="Latitude",
                legend_font_size=20
            )

    # If both uploaded plot both
    else:

        df_bus = pd.read_json(contents_bus, orient="records")
        df_truth = pd.read_json(contents_truth, orient="records")
        
        # If Uncorrected Times Selected plot bus data
        if plot_type == 'Uncorrected Times':
            
            truth_time_ones = np.ones_like(df_truth["TIME"])
            bus_time_ones = np.ones_like(df_bus["TIME"])

            troubleshoot_plot.add_trace(go.Scatter(
                    x=df_bus["TIME"],
                    y= bus_time_ones * 1,
                    name="Bus"
                ),),

            troubleshoot_plot.add_trace(go.Scatter(
                    x=df_truth["TIME"],
                    y= truth_time_ones * 2,
                    name="Truth"
                ),),
            
            troubleshoot_plot.update_layout(
            title="UC_T Plot", xaxis_title="Time", yaxis_title="Dataset",
            legend_font_size=20, yaxis_range=[0,3],
            )
        
        # If Uncorrected Lat Long Plot Selected plot bus data
        elif plot_type == 'Uncorrected Lat/Long':

            troubleshoot_plot.add_trace(go.Scatter(x=df_bus["LONG84"][::10], y=df_bus["LAT84"][::10], mode="lines", name="Bus"))
            troubleshoot_plot.add_trace(go.Scatter(x=df_truth["LONG84"][::10], y=df_truth["LAT84"][::10], mode="lines", name="Truth"))

            troubleshoot_plot.update_layout(
                title="UC_LL Plot", xaxis_title="Longitude", yaxis_title="Latitude",
                legend_font_size=20
            )

        # Uncorrected Altitude Plot
        elif plot_type == 'Uncorrected Altitude':

            troubleshoot_plot.add_trace(go.Scatter(x=df_bus["TIME"][::10], y=df_bus["HAE84"][::10], mode="lines", name="Bus"))
            troubleshoot_plot.add_trace(go.Scatter(x=df_truth["TIME"][::10], y=df_truth["HAE84"][::10], mode="lines", name="Truth"))

            troubleshoot_plot.update_layout(
                title="UC_A Plot", xaxis_title="Longitude", yaxis_title="Latitude",
                legend_font_size=20
            )
    
    return troubleshoot_plot


# TSPI_LL plot (plot_one)
@app.callback(
    Output("TSPI_LL", "figure"),
    [
        Input("plot-button", "n_clicks"),
        Input("time-slider", "value"),
    ],
    [State("truth", "data")],
    prevent_initial_call=True,
)
def update_graph_1(n_clicks, times, contents_truth):
    if n_clicks is None or contents_truth is None:
        return {}

    print(times)

    df_truth = pd.read_json(contents_truth, orient="records")

    first_val = math.ceil(len(df_truth) * times[0])
    last_val = math.ceil(len(df_truth) * times[1])

    df_truth = df_truth.iloc[first_val:last_val,:]

    # Initialize empty figures for each graph
    plot_one = go.Figure()

    tdr = max(df_truth['TIME']) - min(df_truth['TIME'])

    plot_one.add_trace(go.Scatter(x=df_truth["LONG84"][::10], y=df_truth["LAT84"][::10], mode="lines"))

    xrange = max(df_truth["LONG84"]) - min(df_truth["LONG84"])
    yrange = max(df_truth["LAT84"]) - min(df_truth["LAT84"])

    plot_one.update_layout(
        title="TSPI_LL Plot", xaxis_title="Longitude", yaxis_title="Latitude",
        xaxis_range=[min(df_truth["LONG84"])-0.1*xrange, max(df_truth["LONG84"])+0.1*xrange],
        yaxis_range=[min(df_truth["LAT84"])-0.1*yrange, max(df_truth["LAT84"])+0.1*yrange],
        legend_font_size=20
    )

    # Return the figures for TSPI_LL
    return plot_one

# TSPI_AT plot (plot_two)
@app.callback(
    Output("TSPI_AT", "figure"),
    [
        Input("plot-button", "n_clicks"),
        Input("time-slider", "value"),
    ],
    [State("truth", "data")],
    prevent_initial_call=True,
)
def update_graph_2(n_clicks, times, contents_truth):
    if n_clicks is None or contents_truth is None:
        return {}

    df_truth = pd.read_json(contents_truth, orient="records")

    first_val = math.ceil(len(df_truth) * times[0])
    last_val = math.ceil(len(df_truth) * times[1])

    df_truth = df_truth.iloc[first_val:last_val,:]

    # Initialize empty figures for each graph
    plot_two = go.Figure()

    plot_two.add_trace(go.Scatter(x=df_truth["TIME"][::10], y=df_truth["HAE84"][::10], mode="lines"))

    plot_two.update_layout(
        title="TSPI_AT Plot", xaxis_title="Time", yaxis_title="Altitude",
        legend_font_size=20
    )

    plot_two.update_layout(
        xaxis_range=[min(df_truth["TIME"]), max(df_truth["TIME"])],
        yaxis_range=[min(df_truth["HAE84"]), max(df_truth["HAE84"])],
    )

    # Return the figures for TSPI_AT
    return plot_two

# Uncorrected Times Plot (plot_three)
@app.callback(
    Output("UC_T", "figure"),
    [
        Input("plot-button", "n_clicks"),
        Input("time-slider", "value"),
    ],
    [
        State("truth", "data"),
        State("bus","data"),
    ],
    prevent_initial_call=True,
)
def update_graph_3(n_clicks, times, contents_truth, contents_bus):
    if n_clicks is None or contents_truth is None or contents_bus is None:
        return {}

    df_truth = pd.read_json(contents_truth, orient="records")

    first_val = math.ceil(len(df_truth) * times[0])
    last_val = math.ceil(len(df_truth) * times[1])

    df_truth = df_truth.iloc[first_val:last_val,:]

    
    df_bus = pd.read_json(contents_bus, orient="records")

    # Get start end end time of truth data
    truth_start = min(df_truth["TIME"])
    truth_end = max(df_truth["TIME"])

    df_bus_new = df_bus[(df_bus["TIME"] >= truth_start) & (df_bus["TIME"] <= truth_end)]

    df_bus_new, truth_new = interpolateData(df_bus_new,df_truth)
    # Don't need truth new for this plot

    new_bus_time_ones = np.ones_like(df_bus_new["TIME"])
    bus_time_ones = np.ones_like(df_bus["TIME"])
    truth_time_ones = np.ones_like(df_truth["TIME"])


    data = [
        go.Scatter(
            x=df_bus_new["TIME"],
            y= new_bus_time_ones * 3,
            name="New bus data",
        ),
        go.Scatter(
            x=df_bus["TIME"],
            y= bus_time_ones * 2,
            name="Bus data"
        ),
        go.Scatter(
            x=df_truth["TIME"],
            y= truth_time_ones * 1,
            name="Truth data"
        ),
        # Data Labels
        go.Scatter(
            x=[min(df_truth["TIME"]), max(df_truth["TIME"]),
            min(df_bus["TIME"]), max(df_bus["TIME"]),
            min(df_bus_new["TIME"]), max(df_bus_new["TIME"])],
            y=[1, 1, 2, 2, 3, 3],
            mode="markers",
            name="Min/Max",
        ),
    ]

    layout = go.Layout(
        xaxis=dict(
            title="Time (24 Hour Elapsed Sec)\n",
        ),
        yaxis_title="Dataset\n",
        title="Clipped and Interpolated Datasets\n",
        legend=dict(
            orientation="h",  # Adjust the legend orientation to horizontal
            yanchor="top",  # Place the legend at the bottom
            xanchor="right",  # Position the legend at the center
            y=.7,  # Adjust the value to set legend y-position
            x=0.5,   # Adjust the value to set legend x-position
        ),
    )

    xrange = max(df_bus['TIME']) - min(df_bus['TIME'])

    plot_three = go.Figure(data=data, layout=layout)
    plot_three.update_layout(
        title="UC_T Plot", xaxis_title="Time", yaxis_title="Dataset", yaxis_range=[0, 5],
        legend=dict(orientation="v", yanchor="bottom", xanchor="left", y=.7, x=0.5),
        xaxis_range=[min(df_bus['TIME'])-0.1*xrange, max(df_bus['TIME'])+0.1*xrange],
        legend_font_size=20
    )

    return plot_three

# Box and Whisker Plots (plot_four)
@app.callback(
    Output("BWP", "figure"),
    [
        Input("plot-button", "n_clicks")
    ],
    [
        State("error", "data"),
    ],
    prevent_initial_call=True,
)
def update_graph_4(n_clicks, contents_error):
    if n_clicks is None or contents_error is None:
        return {}

    marker_color_dict = {1:'#7fa5af',2:'#9ba7f7',3:'#e6bc87',4:'#e68cab',5:'#8ed6f7',6:'#9ba7f7'}
    mark=1

    df_error = pd.read_json(contents_error, orient="records")

    plot_four = go.Figure()

    for column_name in df_error.columns:
        if column_name != "TIME":
            plot_four.add_trace(go.Box(
                y=df_error[column_name],
                name=column_name,
                marker_color=marker_color_dict[mark]))
            mark += 1

    plot_four.update_layout(
        title="BWP Plot", xaxis_title="Measure", yaxis_title="Error", legend_font_size=20
    )

    return plot_four



# These plots not used currently
'''
# Define the callback for updating the BUS_LL plot (plot_four)
@app.callback(
    Output("BUC_LL", "figure"),
    [Input("plot-button", "n_clicks")],
    [State("bus", "data"), State("truth", "data")],
    prevent_initial_call=True,
)
def update_graph_4(n_clicks, contents_Bus, contents_truth):
    if n_clicks is None:
        return {}

    df_Bus = pd.read_json(contents_Bus, orient="records")
    df_truth = pd.read_json(contents_truth, orient="records")

    # Initialize empty figures for each graph
    plot_four = go.Figure()

    plot_four.add_trace(go.Scatter(x=df_Bus['LONG84'][::10], y=df_Bus["LAT84"][::10], mode="lines"))

    xrange = max(df_truth["LONG84"]) - min(df_truth["LONG84"])
    yrange = max(df_truth["LAT84"]) - min(df_truth["LAT84"])

    plot_four.update_layout(
        title="TSPI_AT Plot", xaxis_title="Time", yaxis_title="Altitude",
        xaxis_range=[min(df_truth["LONG84"])-0.1*xrange, max(df_truth["LONG84"])+0.1*xrange],
        yaxis_range=[min(df_truth["LAT84"])-0.1*yrange, max(df_truth["LAT84"])+0.1*yrange],
    )

    # Return the figures for TSPI_AT
    return plot_four


# Define the callback for updating the BUS_AT plot (plot_five)
@app.callback(
    Output("BUS_AT", "figure"),
    [Input("plot-button", "n_clicks")],
    [State("bus", "data"), State("truth", "data")],
    prevent_initial_call=True,
)
def update_graph_5(n_clicks, contents_Bus, contents_truth):
    if n_clicks is None:
        return {}

    df_Bus = pd.read_json(contents_Bus, orient="records")
    df_truth = pd.read_json(contents_truth, orient="records")

    # Initialize empty figures for each graph
    plot_five = go.Figure()

    plot_five.add_trace(go.Scatter(x=df_Bus["TIME"][::10], y=df_Bus["HAE84"][::10], mode="lines"))

    plot_five.update_layout(
        title="BUS_AT Plot", xaxis_title="Time", yaxis_title="Altitude",
    )

    plot_five.update_layout(
        xaxis_range=[min(df_truth["TIME"]), max(df_truth["TIME"])],
        yaxis_range=[min(df_truth["HAE84"]), max(df_truth["HAE84"])],
    )

    # Return the figures for TSPI_AT
    return plot_five
'''


# ERROR PLOT

# Trying to do error stuff part 1
@app.callback(
    Output("ERROR1", "figure"),
    [Input("error-plot-button", "n_clicks"), Input("error-checklist-output", "value")],
    [State("error", "data")],
    prevent_initial_call=True,
)
def update_graph_error(n_clicks, contents_checklist, contents_error):
    if n_clicks is None or contents_checklist is None or contents_error is None:
        return {}
    
    df_error = pd.read_json(contents_error, orient="records")

    plot_error=go.Figure()
    
    for val in contents_checklist:
        plot_error.add_trace(go.Scatter(x=df_error["TIME"][::10], y=df_error[val][::10], mode="lines", name=val))
    
    plot_error.update_layout(
        title="Error-Plot", xaxis_title="Time",
        legend_font_size=20
    )

    # Return the figures for Error
    return plot_error


# Giant Plot
@app.callback(
    Output("giant-plot", "figure"),
    [
        Input("giant-plot-button", "n_clicks"),
    ],
    [
        State("truth", "data"),
        State("bus", "data"),
        State("heatmap","data"),
        State("minlat-input","value"),
        State("maxlat-input","value"),
        State("minlon-input","value"),
        State("maxlon-input","value"),
    ],
    prevent_initial_call=True,
)
def update_graph_giant(n_clicks, contents_truth, contents_bus, contents_heatmap, minlat, maxlat, minlon, maxlon):
    if n_clicks is None:
        return {}

    # If truth and bus and heat and selections made plot
    elif contents_truth and contents_bus and contents_heatmap:

        df_truth = pd.read_json(contents_truth, orient="records")
        df_bus = pd.read_json(contents_bus, orient="records")

        giant_plot = go.Figure()

        giant_plot.add_trace(go.Scatter(x=df_truth["LONG84"][::10], y=df_truth["LAT84"][::10], mode="lines"))
        giant_plot.add_trace(go.Scatter(x=df_bus["LONG84"][::10], y=df_bus["LAT84"][::10], mode="lines"))

        giant_plot.add_layout_image(
            dict(
                source=contents_heatmap,
                xref="paper",
                yref="paper",
                x=0,
                y=1,
                sizex=1,
                sizey=.6,

                opacity=0.7,
                layer="below"
            )
        )

        if minlat and maxlat and minlon and maxlon:
            giant_plot.update_layout(
                title="GIANT-Plot",
                legend_font_size=20,
                xaxis_range=[minlon, maxlon],
                yaxis_range=[minlat, maxlat],  # Add the xaxis_range and yaxis_range only to the scatter _traces_
            )

        # A workaround to hide ticks from the heatmap axes
        if contents_heatmap:
            giant_plot.update_xaxes(showticklabels=False)
            giant_plot.update_yaxes(showticklabels=False)

        return giant_plot

    return {}



# Jamming Plot
@app.callback(
    Output("jam-plot", "figure"),
    [
        Input("jam-plot-button", "n_clicks"),
        Input("jam-options", "value")
    ],
    [State("jam", "data")],
    prevent_initial_call=True,
)
def update_graph_error(n_clicks, jam_options, contents_jam):
    if n_clicks is None or jam_options is None or contents_jam is None:
        return {}

    jam_df = pd.read_json(contents_jam, orient="records")

    # Initialize empty figures for each graph
    jam_plot = go.Figure()    

    for val in jam_options:
        jam_plot.add_trace(go.Scatter(x=jam_df.iloc[:, 0], y=jam_df[val], mode="lines", name=val))
    
    jam_plot.update_layout(
        title="Jam-Plot", xaxis_title="Time",
        legend_font_size=20
    )

    # Return the figures for TSPI_AT
    return jam_plot


# CSV Download Button
@app.callback(
    Output("download-dataframe-csv", "data"),
    [
        Input("download-button", "n_clicks"),
        Input("bus-dtype-output", "value")
    ],
    [
        State("error", "data"),
        State("textarea-input",'value')
    ],
    prevent_initial_call=True,
)
def create_downloadable_data(n_clicks, dtype, contents_error, mission_num):
    if n_clicks is None or contents_error is None:
        return {}

    df_error = pd.read_json(contents_error, orient="records")

    # Provide the download file name
    if mission_num:
        # filename = f"Mission_{mission_num}_{dtype}_errors.csv"
        filename = "Mission_errors.csv"
    else:
        # filename = f"Mission_{dtype}_errors.csv"
        filename = "Mission_errors.csv"

    # Return CSV data as bytes along with the filename
    return dcc.send_data_frame(df_error.to_csv, filename)



if __name__ == '__main__':
    app.run(debug=True)
