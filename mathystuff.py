import numpy as np
import pandas as pd

def interpolateData(bus_df,truth_df):
    """
    Interpolates two time-series dataframes to match:
        - start time
        - end time
        - frequency
    ASSUMPTION: truth_df["TIME"] is a SUBSET of bus_df["TIME"]

    Parameters:
    bus_df (DataFrame): time-series dataframe with columns ["TIME","LAT84","LONG84","HAE84"]
    truth_df (DataFrame): time-series dataframe with columns ["TIME","LAT84","LONG84","HAE84"]

    Returns:
    bus_df (DataFrame): bus_df clipped to truth data
    truth_df (DataFrame): truth_df interpolated to bus_df sampling frequency
    """
    
    # Get start end end time of truth data
    truth_start = min(truth_df["TIME"])
    truth_end = max(truth_df["TIME"])
    
    # Clip bus data to matcht truth time
    bus_df = bus_df[(bus_df["TIME"] >= truth_start) & (bus_df["TIME"] <= truth_end)]
    
    # Interpolate truth data to be at the same sampling rate and time as the bus data
    truth_time_interp = bus_df["TIME"]
    truth_lat_interp = np.interp(bus_df["TIME"],truth_df["TIME"],truth_df["LAT84"])
    truth_long_interp = np.interp(bus_df["TIME"],truth_df["TIME"],truth_df["LONG84"])
    truth_alt_interp = np.interp(bus_df["TIME"],truth_df["TIME"],truth_df["HAE84"])
    truth_df = pd.DataFrame({"TIME":truth_time_interp,"LAT84":truth_lat_interp,"LONG84":truth_long_interp,"HAE84":truth_alt_interp})
    
    # Return new bus_df and truth)df
    return bus_df,truth_df

def calcError(bus_TSPI, truth_TSPI):
    """
    Calculates navigational error for a SINGLE INSTANCE in time given true and percieved:
        - Latitude
        - Longitude
        - Height

    Parameters:
    bus_TSPI (DataFrame Row): single row in time of a time-series dataframe with columns ["TIME","LAT84","LONG84","HAE84"]
    truth_TSPI (DataFrame Row): single row in time of a time-series dataframe with columns ["TIME","LAT84","LONG84","HAE84"]

    Returns:
    time (float): Time step error is calculated for (sec)
    slantrange (Float): 3D error (ft)
    RadError (Float): 2D error (ft)
    Ee (Float): East-West Error (ft)
    En (Float): North-South Error (ft)
    Ez (Float): Altitude Error (ft)
    """
    time = bus_TSPI["TIME"] # Save time step
    a = 6378137; #equitorial radius (m)
    a = a*3937.0/1200.0; #convert to (ft)
    ec = 0.00669437999014; # Eccentricity
    Phi = np.deg2rad((truth_TSPI["LAT84"]+bus_TSPI["LAT84"])/2); #midpoint latitude (rad)

    Rn = a/np.sqrt(1-ec**2 * np.sin(Phi)**2) + (bus_TSPI["HAE84"] + truth_TSPI["HAE84"])/2; #prime vertical radius (ft)
    Rm = a*(1-ec**2)/((1-ec**2*np.sin(Phi))**(3/2)) + (bus_TSPI["HAE84"] + truth_TSPI["HAE84"])/2; # radius of curvature (ft)
    
    Ee = Rn*np.cos(Phi)*np.deg2rad(bus_TSPI["LONG84"] - truth_TSPI["LONG84"]); #East Horizontal Error (ft)
    En = Rm*np.deg2rad(bus_TSPI["LAT84"] - truth_TSPI["LAT84"]); #North Horizontal Error (ft)
    Ez = bus_TSPI["HAE84"] - truth_TSPI["HAE84"]; #Vertical Error (ft)

    RadError = np.sqrt(Ee**2 + En**2); #Radial Error (ft)
    slantrange = np.sqrt(Ee**2 + En**2 + Ez**2); #Slantrange (ft)
    return time, slantrange, RadError, Ee, En, Ez