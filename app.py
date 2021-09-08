# Import Modules
import logging

import pandas as pd
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

from helper_v4 import forecastr, determine_timeframe, get_summary_stats, preprocessing

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
    return render_template('build-forecast-v3.html')  # Application


@app.route('/')
def about():
    return render_template('forecastr.html')  # Product Page


@socketio.on('connection_msg')
def connected(message):
    data = message
    print(data)


@socketio.on('forecast_settings')
def forecast_settings(message):
    # Initial forecast settings
    # - the first time the user sends forecast settings through the app
    # - will use this value in forecastr method
    build_settings = 'initial'

    # store message['data'] into a df called data
    data = message['data']
    print(data)

    # Keep Original Data in Exisiting Structure
    # data[0] is settings
    forecast_settings = data[0]

    # data[1] is message send by main
    # [column_headers, message, timeframe, summary_stats, original_data]
    original_dataset = data[1]['data'][4]

    # print("******************** ORIGINAL DATASET *****************************")
    # print(original_dataset)
    # print("******************** ORIGINAL DATASET *****************************")

    # Extract info from forecast_settings message
    column_headers = data[1]['data'][0]
    print(original_dataset)
    print(column_headers)
    time_series_data = pd.DataFrame(
        data={column_headers[0]: original_dataset[0],
              column_headers[1]: original_dataset[1]}
    )
    freq = data[2]

    # Format the date and metric unit
    time_unit = column_headers[0]
    print(time_unit)
    time_series_data[time_unit] = time_series_data[time_unit].apply(lambda x: pd.to_datetime(str(x)))
    metric = column_headers[1]

    # y (aka as "the original data for the metric being forecasted") will be used in the chartjs line graph
    y = time_series_data[metric].tolist()

    # Use Facebook Prophet through forecastr method
    y_hat, dates, model, csv_export, forecasted_vals, forecasted_vals_mean, yhat_lower, yhat_upper = forecastr(
        time_series_data, forecast_settings, column_headers, freq, build_settings)

    # Send data back to the client
    data_back_to_client = [dates, y_hat, y, forecast_settings, column_headers, freq, original_dataset, csv_export,
                           forecasted_vals, forecasted_vals_mean, yhat_lower, yhat_upper]
    # print(data_back_to_client)

    emit('render_forecast_chart', {'data': data_back_to_client})

    # Validate Model
    # mape_score = validate_model(model,dates)

    # emit('model_validation', {'data':mape_score})


@socketio.on('update_chart_settings')
def update_chart(message):
    # This is an update to the initial forecast settings. The user has changed their settings on Step 3, so we set build_settings to update.
    build_settings = 'update'

    data = message['data']

    ### Setup variables for use in the forecastr method
    forecast_settings = data[1]
    column_headers = data[2]
    freq = data[3]
    # original_dataset
    time_series_data = data[4]
    original_dataset = time_series_data
    time_series_data = pd.DataFrame(data={
        column_headers[0]: time_series_data[0],
        column_headers[1]: time_series_data[1],
    })

    # print("********* TIME SERIES DF ****************")
    # print(time_series_data.head())
    # print("********* TIME SERIES DF ****************")

    # Dimension and Metric
    time_unit = column_headers[0]
    metric = column_headers[1]

    # Make sure time_unit is converted to datetime in order to join in helper_v3
    time_series_data[time_unit] = time_series_data[time_unit].apply(lambda x: pd.to_datetime(str(x)))

    # print([time_unit,metric])

    # Original Data
    y = time_series_data[metric].tolist()

    # Use Facebook Prophet through forecastr method
    y_hat, dates, model, csv_export, forecasted_vals, forecasted_vals_mean, yhat_lower, yhat_upper = forecastr(
        time_series_data, forecast_settings, column_headers, freq, build_settings)

    # Send data back to the client - took out original dataset
    data_back_to_client = [dates, y_hat, y, forecast_settings, column_headers, freq, original_dataset, csv_export,
                           forecasted_vals, forecasted_vals_mean, yhat_lower, yhat_upper]
    emit('render_forecast_chart', {'data': data_back_to_client})

    # Validate Model
    # mape_score = validate_model(model,dates)

    # emit('model_validation', {'data':mape_score})


@socketio.on('reset')
def reset(message):
    data = message['data']
    # print(data)


@socketio.on('send_csv')
def main(message):
    # Store message['data'] in data
    data = message['data']
    print(data)

    # Convert data to a pandas DataFrame
    if str(data).endswith('csv'):
        # /static/sampledata/shampoo_sales.csv
        # need remove the head '/'
        df = pd.read_csv(str(data)[1:])
    else:
        df = pd.DataFrame(data)

    print(df.head())

    # Let's do some preprocessing on this data to determine which column is the dimension vs. metric.
    column_headers = preprocessing(df)

    # Set the time unit and metrc unit names
    time_unit = column_headers[0]
    metric_unit = column_headers[1]

    # Determine whether the timeframe is daily, weekly, monthly, or yearly
    timeframe = determine_timeframe(df, time_unit)

    # Get summary statistics about original dataset
    summary_stats = get_summary_stats(df, column_headers)

    # Send original data to a list
    dimension = df[time_unit].tolist()
    metric = df[metric_unit].tolist()

    original_data = [dimension, metric]

    # Send data back to the client in the form of a label detected or text extracted.
    emit('render_uploaded_csv_data', {'data': [column_headers, message, timeframe, summary_stats, original_data]})


if __name__ == '__main__':
    socketio.run(app, log_output=True, debug=True, use_reloader=True)
