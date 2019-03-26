# forecastr
A flask web app that leverages Facebook Prophet to provide people with the ability to build simple baseline forecasts from within a guided user interface.

### Contents

What is forecastr?<br/>
How does this app work?<br/>
Data Collection on the User Experience<br/>
Requirements<br/>
References<br/>


### What is forecastr?

<a href='https://forecastr-io.herokuapp.com'>forecastr</a> is an experimental flask app I created as a proof of concept to see what it would take to create a UI on top of Facebook Prophet. It provides the user with a 3 step interface that guides them towards building a baseline forecast with Facebook Prophet.

Here is a screenshot of the app after the user has built a forecast:<br/>
<img src="https://raw.githubusercontent.com/garethcull/forecastr/master/static/img/app.png" width="1024" />


### How does this app work?

This app generates a forecast in 3 steps:

1. Upload your csv
2. Configure your initial forecast (choose forecast length and model type - linear or logistic)
3. View Forecast and Tweak settings

This app doesn't store any data about the contents of the uploaded csv within a database. This is a session based product. 

Once the csv has been uploaded to the app, the data is then stored within temporary variables in the client and data is then sent back and forth between to client and server until the forecast is generated. 

At a high level, data flows like this:<br/>
<img src="https://raw.githubusercontent.com/garethcull/forecastr/master/static/img/data-flow.png" width="1024" />

As an example, Let’s say a user is at Step 1. They’ve decided to try the app and click on the CTA “Browse File” and choose a CSV to upload. The app then parses this data and sends it server side to a python script that calculates some basic statistics about the data before sending it back and then forward to visualize on the second tab (ie. Step 2: Review Data + Setup Model).  


### Data Collection on the User Experience

Again, this app does not store any data about the contents of the uploaded csv. I also used the logging python library to suppress any logs echoed during transit between the client and the server.

There is data collected on how people use the app. This data is collected using Google Analytics via a Google Tag Manager implementation. 

At a high level, I use Google Analytics to understand:

1. Whether a user successfully creates a forecast during their session
2. Whether a user successfully uploads a csv
3. How a user interacts with different web elements (ie. buttons, links)
4. Whether a user has downloaded a sample csv.

You can view the forecastr_v4.js and behavioural_analytics.js files to see what data is being passed to Google Analytics via the dataLayer.push().

Example: 
This event is triggered when the pre-forecast chart is successfully rendered on Step 2 of the flow.
window.dataLayer.push({'event': 'step2-pre-forecast-chart-rendered'});  

I then use Google Tag Manager to create rules that listen for any ux events and then send that data to Google Analytics.


### Requirements<br/>

This app uses the following python libraries, which you will need to install:

- fbprophet
- pandas
- datetime
- flask
- flask_socketio
- requests
- numpy
- logging (to suppress)

On the client side:

- chartjs
- jquery
- bootstrap

#### How to run this locally. 

1. Clone this repo and make sure you install all of the above dependencies. 
2. Open forecastr_v4.js and make sure that this line contains http:// and not https:// (which is used in production on heroku)
https://github.com/garethcull/forecastr/blob/master/static/js/forecastr_v4.js#L13
3. $ python app.py
4. Open http://localhost:5000/

#### Blog Post on what I Learned Building a UI on top of Facebook Prophet
https://www.garethcull.com/2019/03/20/what-i-learned-building-a-ui-on-top-of-facebook-prophet/

### References

Here are some links that I found very useful:

- Facebook Prophet: https://facebook.github.io/prophet/docs/quick_start.html#python-api
- Flask: http://flask.pocoo.org/
- SocketIO: https://flask-socketio.readthedocs.io/en/latest/
- ChartJS: https://chartjs.org
- Stackoverflow: https://www.stackeroverflow.com
- How to export data as a csv in javascript: https://halistechnology.com/2015/05/28/use-javascript-to-export-your-data-as-csv/
- Implementing Facebook Prophet Efficiently: https://towardsdatascience.com/implementing-facebook-prophet-efficiently-c241305405a3


