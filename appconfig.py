import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import plotly.express as px
import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
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


app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], prevent_initial_callbacks=True)
server = app.server
app.config.suppress_callback_exceptions=True

# Primary app code
# data upload id's are truth-data and bus-data

def configure_app():
    app.layout = html.Div(
    
    dbc.Container([
    # Storage for data
    dcc.Store(id="truth"),
    dcc.Store(id="bus"),
    dcc.Store(id="nav"),
    dcc.Store(id="heatmap"),
    dcc.Store(id="error"),
    dcc.Store(id="jam"),
    # Title Row
    dbc.Row([
        dbc.Col([
            dbc.Row(html.Br()),
            html.H1('Navigational Error Calculation Tool'),

        ],)
    ]),
    dbc.Card([
        dbc.Row(html.Br()),
        # Row one
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                dbc.Row(html.H4('Inputs')),
                                dbc.Row(html.Br()),
                                # Mission Data Upload Label
                                dbc.Row(html.H6("Enter Mission Number:")),
                                dbc.Input(id="textarea-input", placeholder="Ex. 69",
                                    style={
                                            'borderWidth': '2px',
                                            'borderStyle': 'solid',
                                            'borderRadius': '5px',
                                            'textAlign': 'center',
                                            'backgroundColor':'#fce9e6',
                                        },
                                    ),

                                dbc.Row(html.Br()),

                                dbc.Row(html.H6("Bus Data Type:")),

                                dcc.Dropdown(['NSS', 'INS', 'AINS','GPS'],'GPS',
                                    id='bus-dtype-output',
                                    style={
                                        'backgroundColor':'#fce9e6',
                                    },
                                ),

                                dbc.Row(html.Br()),
                                dbc.Row(html.Br()),
                        
                                # Bus data upload
                                dcc.Upload(id='bus-data',
                                    children=html.Div(['Upload Bus Data']),
                                    style={
                                        'height':'30px',
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'backgroundColor':'#FFAF9E'
                                    }, multiple=False
                                ),
                                
                                dbc.Row(html.Br()),
                                dbc.Row(html.Br()),
                                
                                dbc.Row(html.Br()),
                                # Truth Data Upload
                                dcc.Upload(id='truth-data',
                                    children=html.Div(['Upload TSPI Data']),
                                    style={
                                        'height':'30px',
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'backgroundColor':'#FFAF9E'
                                    }, multiple=False
                                ),
                                
                            ],
                            style={
                                    'textAlign': 'center',
                                    'justify-content': 'center',
                                    'align-items': 'center',
                                    'width':'85%'
                                },
                            ), 
                            
                        ], width={"offset":2}
                        ),
                    ]),
            
                    dbc.Row(html.Br()),
                ],
                style={'height':'100%'}
                ),
            # width={"size":3}, style={'height':'100%'}
            ),

            # Data Processing Card
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                dbc.Row(html.H4('Data Processing', className='text-center')),
                                
                                dbc.Row(html.Br()),

                                dbc.Row(html.H6('Choose a Plot to', className='text-center')),
                                dbc.Row(html.H6('Troubleshoot', className='text-center')),

                                dcc.Dropdown(['Uncorrected Times', 'Uncorrected Lat/Long', 'Uncorrected Altitude'],
                                    id='troubleshoot-plot-dropdown',
                                    style={
                                        'background-color': '#fce9e6',
                                    },
                                ),
                                dbc.Row(html.Br()),dbc.Row(html.Br()),

                                html.Button('Calculate Errors', id="error-button",
                                    style={
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '10px',
                                        'backgroundColor':'#FFAF9E',
                                        'height':'45px',
                                    },
                                ),

                                html.Label("(Please be Patient, I\'m Slow)"),

                                dbc.Row(html.Br()),dbc.Row(html.Br()),

                                # SLIDER STUFF
                                dbc.Row(html.H6('Select Time Range', className='text-center')),

                                dcc.RangeSlider(0, 1,
                                    id="time-slider",
                                    value=[0, 1],
                                    allowCross=False,
                                    marks=None,
                                ),

                                dbc.Row(html.Br()),

                                html.Button('Populate Plots', id="plot-button",
                                    style={
                                        "background-color": "#FFAF9E",
                                        "border-radius": "10px",
                                        'height':'45px',
                                    },
                                ),
                            ],
                            style={
                                    'textAlign': 'center',
                                    'justify-content': 'center',
                                    'align-items': 'center',
                                    'width':'85%'
                                },
                            ), 
                            
                        ],
                        width={"offset":2}
                        ),
                    ]),
                    dbc.Row(html.Br()),
                ],
                style={'height':'100%'}
                ),
            width={"size":3},
            ),

            # Troubleshooting Plot
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Row(html.H4('Troubleshooting Plot', className='text-center')),
                        dbc.Col([
                            dcc.Graph(id='troubleshooting-plot', figure={})
                        ])
                    ]),
                ],
                style={'height':'100%',}
                ),
            width={"size":6}
            ),
                                
        ]),

        # Break between plot rows
        dbc.Row(html.Br()),
        
        # Row two
        dbc.Row([
            # TSPI Lat/Long Plot
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Row(html.H4('TSPI Lat/Long', className='text-center')),
                        dbc.Col([
                            dcc.Graph(id='TSPI_LL', figure={})
                        ])
                    ])], style={'height':'100%'}), width={"size":4}
            ),

            # TSPI Alt vs Time PLot
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Row(
                            html.H4('TSPI Alt vs time', className='text-center')
                        ),
                        dbc.Col([
                            dcc.Graph(id='TSPI_AT', figure={})
                        ]),
                    ])
                ], style={'height':'100%',}), width={"size":4}
            ),
            # Uncorrected Times Plot
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Row(html.H4(" Clipped and Interpolated Datasets", className='text-center')),
                        dbc.Col([
                            dcc.Graph(id='UC_T', figure={})
                        ]),
                    ])], style={'height':'100%'}
                ), width={"size":4}
            ),
        ]),

        # Break between plot rows
        dbc.Row(html.Br()),

        # May add these back later idk
        # # Row three
        # dbc.Row([
        #     # Bus Uncorrected Lat/Long Plot
        #     dbc.Col(
        #         dbc.Card([
        #             dbc.Row([
        #                 dbc.Row(
        #                     html.H4('Bus Uncorrected Lat/Long', className='text-center')),
        #                 dbc.Col([
        #                     dcc.Graph(id='BUC_LL', figure={})
        #                     ])
        #                 ])
        #             ], style={'height':'100%'}), width={"size":4}
        #         ),
        #     # Bus Alt vs Time Plot
        #     dbc.Col(
        #         dbc.Card([
        #             dbc.Row([
        #                 dbc.Row(html.H4('Bus Alt vs Time', className='text-center')),
        #                 dbc.Col([
        #                     dcc.Graph(id='BUS_AT', figure={})
        #                 ]),
        #                 ])
        #             ], style={'height':'100%'}), width={"size":4}
        #         ),
        #     ]),

        # Break between plot rows
        dbc.Row(html.Br()),

        # Row four box and whisker plots
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Row(html.H4('Box and Whisker Plots', className='text-center')),
                        dbc.Col([
                            dcc.Graph(id='BWP', figure={})
                        ]),
                    ])
                ], style={'height':'100%'}), width={"size":12}
            ), 
        ]),

        # Break between plot rows
        dbc.Row(html.Br()),

        # Row five GIANT plot setup and plotting
        dbc.Row([
        # Row five first card - Data Processing Card
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                # Code Here
                                html.H4("GIANT Plot Setup"),
                                dbc.Row(html.Br()),
                                
                                # Heatmap Data Upload
                                dcc.Upload(id='heatmap-upload',
                                    children=html.Div(['Upload Heatmap Image']),
                                    style={
                                        'height':'30px',
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'backgroundColor':'#FFAF9E'
                                    }, multiple=False
                                ),

                                dbc.Row(html.Br()),

                                dbc.Input(id="minlat-input", placeholder="Minimum Latitude",
                                    style={
                                            'borderWidth': '2px',
                                            'borderStyle': 'solid',
                                            'borderRadius': '5px',
                                            'textAlign': 'center',
                                            'backgroundColor':'#fce9e6',
                                    },
                                ),
                                dbc.Input(id="maxlat-input", placeholder="Maximum Latitude",
                                    style={
                                            'borderWidth': '2px',
                                            'borderStyle': 'solid',
                                            'borderRadius': '5px',
                                            'textAlign': 'center',
                                            'backgroundColor':'#fce9e6',
                                    },
                                ),

                                dbc.Input(id="minlon-input", placeholder="Minimum Longitude",
                                    style={
                                            'borderWidth': '2px',
                                            'borderStyle': 'solid',
                                            'borderRadius': '5px',
                                            'textAlign': 'center',
                                            'backgroundColor':'#fce9e6',
                                    },
                                ),
                                dbc.Input(id="maxlon-input", placeholder="Minimum Longitude",
                                    style={
                                            'borderWidth': '2px',
                                            'borderStyle': 'solid',
                                            'borderRadius': '5px',
                                            'textAlign': 'center',
                                            'backgroundColor':'#fce9e6',
                                    },
                                ),
                                dbc.Row(html.Br()),
                                
                                html.H6("TSPI or Bus Data Upload Required for this plot", className='text-center'),

                                html.Button('Draw GIANT Plot', id="giant-plot-button",
                                    style={
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '10px',
                                        'backgroundColor':'#FFAF9E',
                                        'height':'45px',
                                    },
                                ),

                                dbc.Row(html.Br()),

                            ],
                            style={
                                    'textAlign': 'center',
                                    'justify-content': 'center',
                                    'align-items': 'center',
                                    'width':'85%'
                                },
                            ), 
                        ],
                        width={"offset":2}
                        ),
                    ]),
                    dbc.Row(html.Br()),
                ],
                style={'height':'100%'}
                ),
            width={"size":3},
            ),

            # Row five Second card
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Row(html.H4('GIANT Plot', className='text-center')),
                        dbc.Col([
                            dcc.Graph(id='giant-plot', figure={}, style={'width': '90%', 'height': '60vh'}), # "offset":1
                        ]),
                    ])
                ], style={'height':'100%'}), width={"size":9}, # "offset":1
            ),

        ]),
        
        # Break between plot rows
        dbc.Row(html.Br()),

        # Row six Error plot setup and plotting
        dbc.Row([
        # Data Processing Card
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                dbc.Row(html.H4('Error Plot Setup', className='text-center')),

                                
                                
                                dbc.Row(html.Br()),

                                dbc.Row(html.H6('Errors Filter', className='text-center')),

                                dcc.Checklist(id='error-checklist-output',
                                    options={"slantrange":"Slant Range", "RadError": "Rad Error", "Ee":"Ee", "En":"En", "Ez":"Ez"},
                                    style={
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'backgroundColor':'#fce9e6',
                                    },
                                value= ["slantrange", "RadError"]
                                ),

                                dbc.Row(html.Br()),

                                # Nav Data Upload
                                dcc.Upload(id='nav-data',
                                    children=html.Div(['Upload Nav Updates']),
                                    style={
                                        'height':'30px',
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'backgroundColor':'#FFAF9E'
                                    }, multiple=False
                                ),

                                dbc.Row(html.Br()),

                                dbc.Label("Optional Nav Display",
                                    style={
                                            'textAlign': 'center',
                                    },
                                ),

                                dcc.Checklist(
                                    id='nav-options',
                                    style={
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'backgroundColor':'#fce9e6',
                                    },
                                ),

                                dbc.Row(html.Br()),

                                html.Button('Populate Error Plot', id="error-plot-button",
                                    style={
                                        "background-color": "#FFAF9E",
                                        "border-radius": "10px",
                                        'height':'45px',
                                    },
                                ),

                                dbc.Row(html.Br()),

                                html.Button('Download Error Data as CSV', id="download-button",
                                    style={
                                    "width": "75%",
                                    "height": "70px",
                                    "background-color": "#FFAF9E",
                                    "border-radius": "20px",
                                    },
                                ),
                                dcc.Download(id='download-dataframe-csv'),
                            ],
                            style={
                                    'textAlign': 'center',
                                    'justify-content': 'center',
                                    'align-items': 'center',
                                    'width':'85%'
                                },
                            ), 
                        ],
                        width={"offset":2}
                        ),
                    ]),
                    dbc.Row(html.Br()),
                ],
                style={'height':'100%'}
                ),
            width={"size":3},
            ),
            # Plotting error I guess
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Row(html.H4('Error Plot', className='text-center')),
                        dbc.Col([
                            dcc.Graph(id='ERROR1', figure={})
                        ]),
                    ])
                ], style={'height':'100%'}), width={"size":9}
            ),
        ]),

        # Break between rows
        dbc.Row(html.Br()),

        # Row seven plot setup and plotting
        dbc.Row([

        # Row seven first card - Data Processing Card
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                # Code Here
                                html.H4("Jamming Data"),
                                dbc.Row(html.Br()),
                                dbc.Row(html.Br()),
                                # Jam data upload
                                dcc.Upload(id='jam-data',
                                    children=html.Div(['Upload Jamming Data']),
                                    style={
                                        'height':'30px',
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'backgroundColor':'#FFAF9E'
                                    }, multiple=False
                                ),

                                dbc.Row(html.Br()),
                                dbc.Row(html.Br()),

                                dcc.Checklist(
                                    id='jam-options',
                                    style={
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '5px',
                                        'textAlign': 'center',
                                        'backgroundColor':'#fce9e6',
                                    },
                                ),

                                dbc.Row(html.Br()),
                                dbc.Row(html.Br()),

                                html.Button('Draw Jamming Plot', id="jam-plot-button",
                                    style={
                                        'borderWidth': '2px',
                                        'borderStyle': 'solid',
                                        'borderRadius': '10px',
                                        'backgroundColor':'#FFAF9E',
                                        'height':'45px',
                                    },
                                ),

                                dbc.Row(html.Br()),

                            ],
                            style={
                                    'textAlign': 'center',
                                    'justify-content': 'center',
                                    'align-items': 'center',
                                    'width':'85%'
                                },
                            ), 
                        ],
                        width={"offset":2}
                        ),
                    ]),
                    dbc.Row(html.Br()),
                ],
                style={'height':'100%'}
                ),
            width={"size":3},
            ),

            # Row seven Second card
            dbc.Col(
                dbc.Card([
                    dbc.Row([
                        dbc.Row(html.H4('Jamming Plot', className='text-center')),
                        dbc.Col([
                            dcc.Graph(id='jam-plot', figure={})
                        ]),
                    ])
                ], style={'height':'100%'}), width={"size":9}
            ),
        ]),
    ]),
    ]), style={"background-color": "#FFCBBF"},
    )


# Colors -

# lighter orange #FFCBBF
# darker orange #FFAF9E
# xtra light pink #fce9e6


# #ffcbbf	#ffebbf	#ffbfd3 #bfffcb	#cbbfff #bff3ff 