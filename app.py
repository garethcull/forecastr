# Import Modules

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import numpy as np
import requests
from datetime import datetime
from fbprophet import Prophet
import pandas as pd
from helper_v4 import forecastr,determine_timeframe,get_summary_stats,validate_model
import logging



# Socket IO Flask App Setup

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, logger=False, engineio_logger=False)


# Suppress logs except for error: https://stackoverflow.com/questions/43487264/disabling-logger-in-flask-socket-io
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('geventwebsocket.handler').setLevel(logging.ERROR)



@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

# Flask App

@app.route('/app/')
def index():
    return render_template('build-forecast-v3.html') # Application

@app.route('/')
def about():
    return render_template('forecastr.html') # Product Page


@socketio.on('connection_msg')
def connected(message):
    
    data = message
    print(data)


@socketio.on('forecast_settings')
def forecast_settings(message):
    
    # Initial forecast settings - the first time the user sends forecast settings through the app - will use this value in forecastr method
    build_settings = 'initial'
    
    # store message['data'] into a df called data
    data = message['data']
    
    # Keep Original Data in Exisiting Structure
    original_dataset = data[1]['data'][1]['data']
    
    #print("******************** ORIGINAL DATASET *****************************")
    #print(original_dataset)
    #print("******************** ORIGINAL DATASET *****************************")
    
    # Extract info from forecast_settings message
    time_series_data = pd.DataFrame(data[1]['data'][1]['data'])
    forecast_settings = data[0]
    freq = data[2]
    column_headers = data[1]['data'][0]
    
    # Format the date and metric unit
    time_unit = column_headers[0]
    time_series_data[time_unit] = time_series_data[time_unit].apply(lambda x: pd.to_datetime(str(x)))
    metric = column_headers[1]
    
    # y (aka as "the original data for the metric being forecasted") will be used in the chartjs line graph 
    y = time_series_data[metric].tolist()
    
    # Use Facebook Prophet through forecastr method
    forecast = forecastr(time_series_data,forecast_settings,column_headers,freq,build_settings)
        
    # Need to convert forecast back into a list / array for y, y_hat and date so it can be properly graphed with chartjs
    y_hat = forecast[0]
    dates = forecast[1]
    model = forecast[2]
    csv_export = forecast[3]
    
    # Send data back to the client
    data_back_to_client = [dates,y_hat,y,forecast_settings,column_headers,freq,original_dataset,csv_export]
    #print(data_back_to_client)
    
    
    emit('render_forecast_chart', {'data': data_back_to_client})
    
    
    
    # Validate Model
    #mape_score = validate_model(model,dates)

    #emit('model_validation', {'data':mape_score})
    
    
@socketio.on('update_chart_settings')
def update_chart(message):
    
    # This is an update to the initial forecast settings. The user has changed their settings on Step 3, so we set build_settings to update.
    build_settings = 'update'
    
    data = message['data']
    
    ### Setup variables for use in the forecastr method    
    time_series_data = data[4]
    original_dataset = time_series_data
    time_series_data = pd.DataFrame(time_series_data)
    
    #print("********* TIME SERIES DF ****************")
    #print(time_series_data.head())
    #print("********* TIME SERIES DF ****************")
    
    forecast_settings = data[1]
    column_headers = data[2]
    freq = data[3]
    
    # Dimension and Metric
    time_unit = column_headers[0]
    metric = column_headers[1]
    
    # Make sure time_unit is converted to datetime in order to join in helper_v3
    time_series_data[time_unit] = time_series_data[time_unit].apply(lambda x: pd.to_datetime(str(x)))

    
    #print([time_unit,metric])
    
    # Original Data
    y = time_series_data[metric].tolist()
    
    # Use Facebook Prophet through forecastr method
    forecast = forecastr(time_series_data,forecast_settings,column_headers,freq,build_settings)
    
    # Need to convert forecast back into a list / array for y, y_hat and date so it can be properly graphed with chartjs
    y_hat = forecast[0]
    dates = forecast[1]
    model = forecast[2]
    csv_export = forecast[3]
    
    # Send data back to the client - took out original dataset
    data_back_to_client = [dates,y_hat,y,forecast_settings,column_headers,freq,original_dataset,csv_export]
    emit('render_forecast_chart', {'data': data_back_to_client})
    
    # Validate Model
    #mape_score = validate_model(model,dates)
    
    #emit('model_validation', {'data':mape_score})
    
    #print(forecast)
    
    
    
    
    #print("UPDATING **********************")
    #print(time_series_data)
    
    
@socketio.on('reset')    
def reset(message):
    
    data = message['data']
    #print(data)

    
@socketio.on('send_csv')
def main(message):
        
    # Store message['data'] in data
    data = message['data']
    
    # Convert data to a pandas DataFrame
    data = pd.DataFrame(data)
    
    # Get list of column headers
    column_headers = list(data)
    
    time_unit = column_headers[0]
    metric_unit = column_headers[1]
    
    #print([time_unit,metric_unit])
    
    # Determine whether the timeframe is daily, weekly, monthly, or yearly
    timeframe = determine_timeframe(data, time_unit)
    
    # Get summary statistics about original dataset
    summary_stats = get_summary_stats(data,column_headers)
    
    # Send original data to a list
    dimension = data[time_unit].tolist()
    metric = data[metric_unit].tolist()
    
    original_data = [dimension,metric]
    
    # Send data back to the client in the form of a label detected or text extracted.
    emit('render_uploaded_csv_data', {'data': [column_headers,message, timeframe, summary_stats,original_data]})
    
    # Probably need some sort of date checker function to properly format the date.
    data[time_unit] = data[time_unit].apply(lambda x: pd.to_datetime(str(x)))

    

if __name__ == '__main__':
    socketio.run(app, log_output=False)