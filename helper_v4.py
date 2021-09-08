import time

import numpy as np
import pandas as pd
from flask_socketio import emit
from prophet import Prophet
from prophet.diagnostics import cross_validation
from prophet.diagnostics import performance_metrics


def forecastr(data, forecast_settings, column_headers, freq_val, build_settings):
    """
    Background: This function will take the data from the csv and forecast out x number of days.

    Input:

    data: This is a pandas dataframe containing time series data (2 columns: date and metric)
    forecast_settings: This is a list containing values for model type, forecast period length and seasonality parameters
    column_headers: List containing the name of the date and metric
    freq_val: String containing "D","M","Y"
    build_settings: String determining whether this is an initial or updated forecast.


    Output:

    [y_hat,dates,m,csv_ready_for_export]: A list containing forecasted data, dimension, model and data for the csv export


    """

    ##### Variables, Model Settings & Facebook Prophet Hyper Parameters #####

    # Initial Variables
    build = build_settings  # Determine the build_setting - either initial or update forecast settings.
    dimension = column_headers[0]  # date
    metric = column_headers[1]  # metric name

    # Rename the columns so we can use FB Prophet
    data.rename(index=str, columns={dimension: "ds", metric: "y"}, inplace=True)

    # Hyper-parameters
    fs_model_type = forecast_settings[0]  # linear or logistic
    fs_period = int(forecast_settings[1])  # int
    fs_seasonality_mode = forecast_settings[4]  # additive or multiplicative
    fs_daily_seasonality = forecast_settings[6][0]  # True or False
    fs_weekly_seasonality = forecast_settings[6][1]  # True or False
    fs_yearly_seasonality = forecast_settings[6][2]  # True or False

    # Need to set carrying capacity and saturated min as an int if model_type = 'logistic', else we'll set as 'auto' to be filtered out.

    if fs_model_type == 'logistic':
        fs_carrying_capacity = int(forecast_settings[2])  # int
        fs_saturated_minimum = int(forecast_settings[3])  # int
        data['cap'] = fs_carrying_capacity
        data['floor'] = fs_saturated_minimum
    else:
        print('no cap or floor needed as it is a linear model.')
        fs_carrying_capcity = 'auto'
        fs_saturated_minimum = 'auto'

    # Additional Hyper Parameters
    fs_seasonality_prior_scale = forecast_settings[5]  # int
    fs_n_changepoints = forecast_settings[7]  # int
    fs_changepoints_prior_scale = forecast_settings[8]  # int??

    # Check the following hyper parameters to see if they were set from within the UI. If not, they'll be set to 'auto'
    fs_seasonality_prior_scale = check_val_of_forecast_settings(fs_seasonality_prior_scale)
    fs_n_changepoints = check_val_of_forecast_settings(fs_n_changepoints)
    fs_changepoints_prior_scale = check_val_of_forecast_settings(fs_changepoints_prior_scale)

    # Holidays - to be included in a future iteration....
    holidays_prior_scale = 10  # Determines how much of an effect holidays should have on a prediction. Default value is 10

    #### End of Hyper Parameters Settings ####

    # No let's set up the arguments so that we can pass them into Prophet() when we instantiate the model.

    arguments = ['growth',
                 'seasonality_mode',
                 'seasonality_prior_scale',
                 'daily_seasonality',
                 'weekly_seasonality',
                 'yearly_seasonality',
                 'n_changepoints',
                 'changepoint_prior_scale']

    arg_values = [fs_model_type,
                  fs_seasonality_mode,
                  fs_seasonality_prior_scale,
                  fs_daily_seasonality,
                  fs_weekly_seasonality,
                  fs_yearly_seasonality,
                  fs_n_changepoints if fs_n_changepoints == 'auto' else int(fs_n_changepoints),
                  fs_changepoints_prior_scale]

    # Needs to be a dictionary
    model_arg_vals = dict(zip(arguments, arg_values))

    ###### CHECK TO SEE WHAT VALUES WERE SET FROM WITHIN THE UI ######

    # Check to see if any values are 0, auto or false. If any hyper-parameters have these values, they will not be included
    # when the pass in the dictionary prophet_arg_vals as kwarg

    prophet_arg_vals = {}

    for key, value in model_arg_vals.items():
        if value != "" and value != False and value != 0 and value != 'auto':
            prophet_arg_vals[key] = value
        else:
            print(f'skipping {key}: {value}')

    ##### TIME TO INSTANTIATE, FIT AND PREDICT WITH FACEBOOK PROPHET ######

    # Instantiate with prophet_arg_vals that are not auto, 0 or False.
    m = Prophet(**prophet_arg_vals)

    # Fit the Model - Side Note it would be interesting to time how long this takes by file size #start = time.time()
    start = time.time()
    m.fit(data)
    end = time.time()
    print(end - start)

    # Status update
    emit('processing', {'data': 'model has been fit'})

    # Let's create a new data frame for the forecast which includes how long the user requested to forecast out in time units and by time unit type (eg. "D", "M","Y")
    future = m.make_future_dataframe(periods=fs_period, freq=freq_val)

    # If fs_model_type = 'logistic', create a column in future for carrying_capacity and saturated_minimum
    if fs_model_type == 'logistic':
        future['cap'] = fs_carrying_capacity
        future['floor'] = fs_saturated_minimum
    else:
        print('no cap or floor needed as it is a linear model.')

    # Let's predict the future :)
    forecast = m.predict(future)

    ##### Removed Cross-Validation for this release - see v3 for previous implementation #####

    ##### Send y_hat and dates to a list, so that they can be graphed easily when set in ChartJS

    y_hat = forecast['yhat'].tolist()
    yhat_lower = forecast['yhat_lower'].tolist()
    yhat_upper = forecast['yhat_upper'].tolist()
    dates = forecast['ds'].apply(lambda x: str(x).split(' ')[0]).tolist()

    ##### Lets see how the forecast compares to historical performance #####

    # First, lets sum up the forecasted metric
    forecast_sum = forecast['yhat'][-fs_period:].sum()
    forecast_mean = forecast['yhat'][-fs_period:].mean()

    # Now lets sum up the actuals for the same time interval as we predicted
    actual_sum = float(data['y'][-fs_period:].sum())
    actual_mean = float(data['y'][-fs_period:].mean())

    difference = '{0:.1%}'.format(((forecast_sum - actual_sum) / forecast_sum))
    difference_mean = '{0:.1%}'.format(((forecast_mean - actual_mean) / forecast_mean))

    forecasted_vals = ['{0:.1f}'.format(forecast_sum), '{0:.1f}'.format(actual_sum), difference]
    forecasted_vals_mean = ['{0:.1f}'.format(forecast_mean), '{0:.1f}'.format(actual_mean), difference_mean]

    '''


    # Lets compare those two numbers, if forecast_sum is greater than actual, calculate the increase.  Else, calculate the decrease
    if forecast_sum - actual_sum > 0:  # this if else handles percent increase vs. decrease
        difference = '{0:.2%}'.format(((forecast_sum - actual_sum) / forecast_sum))
        print("*********** DIFFERENCE IS ********")
        print(difference)
    else:
        difference = '{0:.2f}'.format(((actual_sum - forecast_sum) / actual_sum))
        print("*********** DIFFERENCE IS ********")
        print(difference)

    '''

    ####### Formatting data for CSV Export Functionality ##########

    # First, let's merge the original and forecast dataframes
    data_for_csv_export = pd.merge(forecast, data, on='ds', how='left')

    # Select the columns we want to include in the export
    export_formatted = data_for_csv_export[['ds', 'y', 'yhat', 'yhat_upper', 'yhat_lower']]

    # Rename y and yhat to the actual metric names
    export_formatted.rename(index=str, columns={'ds': 'date', 'y': metric, 'yhat': metric + '_forecast',
                                                'yhat_upper': metric + '_upper_forecast',
                                                'yhat_lower': metric + '_lower_forecast'}, inplace=True)

    # replace NaN with an empty val
    export_formatted = export_formatted.replace(np.nan, '', regex=True)

    # Format timestamp
    export_formatted['date'] = export_formatted['date'].apply(lambda x: str(x).split(' ')[0])

    # Create dictionary format for sending to csv
    csv_ready_for_export = export_formatted.to_dict('records')

    # print(y_hat)
    # print(csv_ready_for_export)
    print(forecasted_vals)
    print(forecasted_vals_mean)

    return [y_hat, dates, m, csv_ready_for_export, forecasted_vals, forecasted_vals_mean, yhat_lower, yhat_upper]


def validate_model(model, dates):
    """

    Background:

    This model validation function is still under construction and will be updated during a future release.


    """

    count_of_time_units = len(dates)
    # print(count_of_time_units)
    initial_size = str(int(count_of_time_units * 0.20)) + " days"
    horizon_size = str(int(count_of_time_units * 0.10)) + " days"
    period_size = str(int(count_of_time_units * 0.05)) + " days"

    df_cv = cross_validation(model, initial=initial_size, horizon=horizon_size, period=period_size)
    # df_cv = cross_validation(model,initial='730 days', period='180 days', horizon = '365 days')
    df_p = performance_metrics(df_cv)

    # print(df_cv.head(100))
    # print(df_p.head(100))

    mape_score_avg = str(round(df_p['mape'].mean() * 100, 2)) + "%"

    return mape_score_avg


def check_val_of_forecast_settings(param):
    """

    Background:

    This function is used to check to see if there is a value (submitted from the user in the UI) for a given Prophet Hyper Parameter. If there is no value or false or auto, return that, else we'll return a float of the param given that the value may be a string.

    If the param value is blank, false or auto, it will eventually be excluding from the dictionary being passed in when instantiating Prophet.

    """

    # Check hyper parameter value and return appropriate value.
    if (param == "") or (param == False) or (param == 'auto'):
        new_arg = param
        return new_arg

    else:
        new_arg = float(param)
        return new_arg


def get_summary_stats(data, column_headers):
    """

    Background:
    This function will get some summary statistics about the original dataset being uploaded.

    Input:

    data: a dataframe with the data from the uploaded csv containing a dimension and metric
    column_headers: string of column names for the dimension and metric


    Output:

    sum_stats: a list containing the count of time units, the mean, std, min and max values of the metric. This data is rendered on step 2 of the UI.

    """

    # Set the dimension and metrics
    dimension = column_headers[0]
    metric = column_headers[1]

    time_unit_count = str(data[dimension].count())

    print(data[metric].mean())

    mean = str(round(data[metric].mean(), 2))
    print('string of the mean is ' + mean)

    std = str(round(data[metric].std(), 2))
    minimum = str(round(data[metric].min(), 2))
    maximum = str(round(data[metric].max(), 2))

    sum_stats = [time_unit_count, mean, std, minimum, maximum]
    print(sum_stats)

    return sum_stats


def preprocessing(data):
    """

    Background: This function will determine which columns are dimensions (time_unit) vs metrics, in addition to reviewing the metric data to see if there are any objects in that column.

    Input:

        data (df): A dataframe of the parsed data that was uploaded.

    Output:

        [time_unit,metric_unit]: the appropriate column header names for the dataset.

    """

    # Get list of column headers
    column_headers = list(data)

    # Let's determine the column with a date

    col1 = column_headers[0]
    col2 = column_headers[1]
    print('the first column is ' + col1)

    # Get the first value in column 1, which is what is going to be checked.
    col1_val = data[col1][0]
    print(type(col1_val))

    """

    TO DO: Pre-processing around the dtypes of both columns. If both are objects, I'll need to determine which is the column.

    TO DO: Emit any error messaging


    print('The data type of this metric column is: ' + str(data[metric].dtype))
    print(data[metric].head())

    data[metric] = data[metric].apply(lambda x: float(x))

    print(data[metric].dtype)


    """

    # Check to see if the data has any null values

    print('Is there any null values in this data? ' + str(data.isnull().values.any()))

    # If there is a null value in the dataset, locate it and emit the location of the null value back to the client, else continue:

    print(data.tail())

    do_nulls_exist = data.isnull().values.any()

    if do_nulls_exist == True:
        print('found a null value')
        null_rows = pd.isnull(data).any(1).nonzero()[0]
        print('######### ORIGINAL ROWS THAT NEED UPDATING ##############')
        print(null_rows)
        # Need to add 2 to each value in null_rows because there

        print('######### ROWS + 2 = ACTUAL ROW NUMBERS IN CSV ##############')
        update_these_rows = []
        for x in null_rows:
            update_these_rows.append(int(x) + 2)

        print(update_these_rows)

        emit('error', {'data': update_these_rows})






    else:
        print('no nulls found')

    if isinstance(col1_val, (int, np.integer)) or isinstance(col1_val, float):
        print(str(col1_val) + ' this is a metric')
        print('Setting time_unit as the second column')
        time_unit = column_headers[1]
        metric_unit = column_headers[0]
        return [time_unit, metric_unit]
    else:
        print('Setting time_unit as the first column')
        time_unit = column_headers[0]
        metric_unit = column_headers[1]
        return [time_unit, metric_unit]


def determine_timeframe(data, time_unit):
    """

    Background:

    This function determines whether the data is daily, weekly, monthly or yearly by checking the delta between the first and second date in the df.

    Input:

    data: a df containg a dimension and a metric
    time_unit: is the dimension name for the date.


    Output:

    time_list: a list of strings to be used within the UI (time, desc) and when using the function future = m.make_future_dataframe(periods=fs_period, freq=freq_val)



    """

    # Determine whether the data is daily, weekly, monthly or yearly
    date1 = data[time_unit][0]
    date2 = data[time_unit][1]

    first_date = pd.Timestamp(data[time_unit][0])
    second_date = pd.Timestamp(data[time_unit][1])
    time_delta = second_date - first_date

    time_delta = int(str(time_delta).split(' ')[0])

    print([data[time_unit][0], data[time_unit][1]])
    print([second_date, first_date, time_delta])

    if time_delta == 1:
        time = 'days'
        freq = 'D'
        desc = 'daily'
    elif 7 <= time_delta <= 27:
        time = 'weeks'
        freq = 'W'
        desc = 'weekly'
    elif 28 <= time_delta <= 31:
        time = 'months'
        freq = 'M'
        desc = 'monthly'
    elif time_delta >= 364:
        time = 'years'
        freq = 'Y'
        desc = 'yearly'
    else:
        print('error?')

    time_list = [time, freq, desc]
    # print(time_list)

    return time_list
