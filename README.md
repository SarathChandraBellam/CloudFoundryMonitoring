# CloudMonitoring
CloudMonitoring is built using [Python 3](https://www.python.org/). CloudMonitoring code interacts with [Cloud Foundry Client](https://pypi.python.org/pypi/cloudfoundry-client) meaning it doesnt interact with the CF installed on your local machine. 

CloudMonitoring tool downloads the necessary dependencies automatically when you run the setup. CloudMonitoring tool uses [Chrome browser driver V2.33](https://sites.google.com/a/chromium.org/chromedriver/downloads) to test the web application urls using [Splinter V0.77](https://splinter.readthedocs.io/en/latest/index.html) in a headless mode and captures the HTTP States.

CloudMonitoring tool can be customized for your monitoring purposes, by default the tool is scheduled to run for every 15 minutes but this can be modified in the JSON which is explained in our [Wiki Page](https://github.build.ge.com/CloudMonitoring/CloudMonitoring/wiki). During each schedule CloudMonitoring tool checks the Summary & Stats of the apps, if any of the app which is set for monitoring is `STOPPED` it tries to bring back the servers to `RUNNING` state. 

# Email Notifications:
CloudMonitoring tool sends eMail notifications using SMTP client. Emails are sent in the below scenarios

* When a monitored app is `STOPPED`
* Whena a `STOPPED` app is successfully brought to `RUNNING` state
* When Cloud Monitor tool fails to bring the app to `RUNNING` state in 3 attempts

# Prerequisites to run the tool:
* Chrome Browser

# Download CloudMonitoring tool:
|Version|Release Date| Download Link|
|-------|-------|-------|
|1.0|15/11/2017|[Click to Download](https://ge.box.com/shared/static/69lsot95a7xo6835aqqykz9jgew6gje8.zip)

# Run CloudMonitoring tool:
Download the tool & configure `cloudmonitoring_config.json` with your application details. Once you are done with finalizing the JSON file double click on `CloudMonitoringTool.exe` to start the CloudMonitoring tool.

# Logs & Health data:
Logs are written to `monitor.log` and a CSV file is written with name `CloudMonitoring.csv` where you can find the health data of the application and status of the application during the monitor schedule time
Note: While the tool is running dont open the CSV file, copy the CSV & paste it now open the copied CSV file so that it doesnt interrupt the tool execution

**Project Contributors:** Thanks to Sarath Chandra Bellam, Sampath Kotra
