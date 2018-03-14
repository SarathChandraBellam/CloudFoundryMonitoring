"""
CloudMonitoring tool is built to monitor the Cloud Foundry application & also to monitor the HTTP states of
Non CloudFoundry applications.
"""
import base64
import csv
import datetime
import json
import logging
import os
import re
import smtplib
import time
import warnings
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import schedule
from cloudfoundry_client.client import CloudFoundryClient
from cloudfoundry_client.entities import InvalidStatusCode
from jinja2 import Environment, FileSystemLoader
from oauth2_client.credentials_manager import OAuthError

from url_validator import validate_url, chrome_exe_download, exit_program

# ignoring warnings
warnings.simplefilter('ignore')
# Writings logs to both console and file
HANDLERS = [logging.FileHandler('monitor.log', 'w'), logging.StreamHandler()]
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', handlers=HANDLERS)

# Setting Proxies
proxy_set = 'http://cis-india-pitc-bangalorez.proxy.corporate.ge.com:80'
os.environ['http_proxy'] = proxy_set
os.environ['HTTP_PROXY'] = proxy_set
os.environ['https_proxy'] = proxy_set
os.environ['HTTPS_PROXY'] = proxy_set


def connect_to_cloud(endpoint_credentials):
    """
    Connect to cloud foundry target api using the credentials
    """
    client_cf = None


    logging.info(': Using API Endpoint: %s', endpoint_credentials[0])
    proxy = {'http': 'http://cis-india-pitc-bangalorez.proxy.corporate.ge.com:80',
             'https': 'http://cis-india-pitc-bangalorez.proxy.corporate.ge.com:80'}
    client_cf = CloudFoundryClient(target_endpoint=endpoint_credentials[0],
                                   proxy=proxy, skip_verification=True)
    client_cf.init_with_user_credentials(endpoint_credentials[1], endpoint_credentials[2])
    logging.info(': %s user logged into CloudFoundry', endpoint_credentials[1])
    return client_cf


def json_file_parser():
    """
    Load and parse the config json file for login and app details
    """
    try:
        input_json_data = json.load(open('cloudmonitoring_config.json', 'r'))
        target_api_endpoint = input_json_data['apiEndPoint']
        username = input_json_data['userName']
        password = validate_base64(input_json_data['passkey'])
        schedule_duration = input_json_data['ScheduleDurationInMinutes']
        recipients = input_json_data['sendNotificationsTo']
        master_key_value = input_json_data['appMasterDetails']['useMasterKey']
        master_user = input_json_data['appMasterDetails']['appUserName']
        master_passkey = input_json_data['appMasterDetails']['appPasskey']
        app_details = input_json_data['appDetails']
        app_count = len(app_details)
        counter = 0
        cf_connect_bool = True
        if app_count != 0:
            for app in app_details:
                if app['isCloudFoundry'] is True:
                    counter += 1
            if counter == 0:
                cf_connect_bool = False
        else:
            logging.info(': No apps configured in json file ')
            exit_program()
        logging.info(': Data read from CloudMonitoring_Config.json file')
        return (schedule_duration, cf_connect_bool, [target_api_endpoint, username, password], recipients,
                master_key_value, master_user, master_passkey, app_details)
    except (FileNotFoundError, IndexError, KeyError) as json_error:
        logging.info(':%s While parsing the config json', json_error)
        exit_program()


def validate_base64(password):
    """
    validate the password and decode it if it is Base 64 encoded
    """
    # noinspection Annotator
    if len(password) % 4 == 0 and re.match('^[A-Za-z0-9+\/=]+\Z', password):
        decoded_pass_key = base64.b64decode(password).decode("utf-8")
    else:
        decoded_pass_key = password
    return decoded_pass_key


class Monitoring:
    """
    class to monitor the working state and status of cloud foundry and non cloud foundry applications.
    whenever the application is stopped or down, it restarts the application and trigger a mail to the application user.
    It writes the application details to CSV file which will act as temporary data bas
    """

    def __init__(self, json_data, csv_writer, cf_client):
        self.input_json_data = json_data
        self.csv_writer = csv_writer
        self.url_data = None
        self.user_input_apps = []
        self.strings_list = []
        self.client = cf_client
        self.predix_app_details = None
        self.app_stats = {}
        self.guid = None
        self.app_info = {}
        self.apps_in_cloud = []
        self.recipients = []

    def get_user_apps_info(self):
        """
        Read the json file values and initiates the url validation for non cloud foundry applications
        """

        self.recipients = self.input_json_data[3]
        master_key_value = self.input_json_data[4]
        master_user = self.input_json_data[5]
        master_passkey = validate_base64(self.input_json_data[6])
        app_details = self.input_json_data[7]
        for each_app in app_details:
            is_cloud_foundry = each_app['isCloudFoundry']
            if is_cloud_foundry is True:
                self.manage_credentials(each_app, master_user, master_passkey, master_key_value)
                self.user_input_apps.append(self.predix_app_details)
            else:
                self.manage_credentials(each_app, master_user, master_passkey, master_key_value)
                logging.info(': Validating the URL of : %s', self.predix_app_details['appName'])
                self.app_info = {'Timestamp': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'), 'Remarks': 'None',
                                 'UsedMemory': '', 'DiskUsage': '', 'CPUUsage': '',
                                 'ApplicationName': self.predix_app_details['appName'],
                                 'AllocatedMemory': '', 'Instances': '', 'Status': 'UNKNOWN'}

                self.write_csv()
                if validate_url(self.predix_app_details) is True:
                    logging.info(': %s application URL is resolving', self.predix_app_details['appName'])
                    self.app_info = {'Timestamp': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                                     'Remarks': '', 'UsedMemory': '', 'DiskUsage': '', 'CPUUsage': '',
                                     'ApplicationName': self.predix_app_details['appName'],
                                     'AllocatedMemory': '', 'Instances': '', 'Status': 'WORKING'}
                    self.write_csv()
                else:
                    logging.info(':Unable to resolve the URL of the application %s ',
                                 self.predix_app_details['appName'])
                    self.app_info = {'Timestamp': datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                                     'Remarks': '', 'UsedMemory': '', 'DiskUsage': '', 'CPUUsage': '',
                                     'ApplicationName': self.predix_app_details['appName'],
                                     'AllocatedMemory': '', 'Instances': '', 'Status': 'NOT WORKING'}
                    self.write_csv()
                    self.send_mail()

    def manage_credentials(self, app_details, user, passkey, master_key_value):
        """
        Getting the user provided credentials and details of each application
        """
        self.predix_app_details = {}
        if master_key_value is True:
            self.predix_app_details['app_user'] = user
            self.predix_app_details['app_key'] = passkey
        else:
            self.predix_app_details['app_user'] = app_details['appUserName']
            self.predix_app_details['app_key'] = validate_base64(app_details['appPasskey'])
        self.predix_app_details['appName'] = app_details['appName']
        self.predix_app_details['appUrl'] = app_details['appUrl']
        self.predix_app_details['isUserInterface'] = app_details['isUserInterface']
        self.predix_app_details['authEnabled'] = app_details['authEnabled']

    def write_csv(self):
        """
        writes or update the app info( name, guid, timestamp, running_instances, instances, remarks ) to CSV
        """
        self.csv_writer.writerow(self.app_info)

    def get_cloud_apps_info(self):
        """
        connects to api end point and login to cloud foundry with user credentials
        """

        # Collecting application names from cloud
        self.client._refresh_token()
        for app in self.client.apps:
            application_guid = app.summary()['guid']
            self.apps_in_cloud.append(application_guid)

    def validate_apps(self):
        """
        Initiates the application monitor for the user provided apps and intimate the user if the user provided
        application names are not matched with cloud application names.
        :return:
        """
        aps_list = {}
        self.get_user_apps_info()
        app_count = len(self.user_input_apps)
        if app_count != 0:
            self.get_cloud_apps_info()
            counter = 0
            for guid in self.apps_in_cloud:
                summary = self.client.apps.get_summary(guid)
                application_name = summary['name']
                aps_list[guid] = application_name
                self.guid = guid
                for each_app_name in self.user_input_apps:
                    if application_name == each_app_name['appName']:
                        self.url_data = {}
                        counter += 1
                        self.url_data = each_app_name
                        logging.info(': Monitoring initiated for application %s', application_name)
                        self.get_app_summary(summary)
                        self.app_info['Remarks'] = 'None'
                        self.write_csv()
                        self.check_summary()
            if counter == 0 and app_count > 0:
                logging.info(': User provided App names doesnt match with cloud apps, Re-run the CloudMonitoring Tool')
                exit_program()

    def check_summary(self):
        """
        check the application summary details. It try to restart the application if it is stopped and trigger a mail
        to the user about the same
        """
        logging.info(': Application Name:%s ::: Status:%s', self.app_info['ApplicationName'], self.app_info['Status'])
        # Checking the application summary state
        if self.app_info['Status'] == 'STARTED':
            self.check_stats()
        elif self.app_info['Status'] == 'STOPPED':
            try:
                self.app_info['Remarks'] = 'Application Stopped'
                self.send_mail()
                logging.info(': Application: %s :: is with Status: %s', self.app_info['ApplicationName'],
                             self.app_info['Status'])
                logging.info(': Force Start Initiated by CloudMonitoring tool')

                # Restarting the app
                self.client.apps.start(self.guid)
                summary_data = self.client.apps.get_summary(self.guid)
                self.get_app_summary(summary_data)
                logging.info(': Application: %s :: is now with Status: %s after Force Start',
                             self.app_info['ApplicationName'], self.app_info['Status'])
                self.app_info['Remarks'] = 'Application Restarted'
                self.send_mail()
                self.write_csv()
                # summary_data = self.client.apps.get_summary(self.app_info['guid'])
                # self.get_app_summary(summary_data)
                self.check_stats()
            except InvalidStatusCode as status_error:
                logging.info(': Unable to start the application: %s :: Application Status: %s :: Error code read: %s',
                             self.app_info['ApplicationName'],
                             self.app_info['Status'], status_error)
                # Unable to restart the application. Trigger a mail and writes to csv
                self.app_info['Remarks'] = 'Failed to Start/restart the app.'
                self.send_mail()
                self.write_csv()

    def check_stats(self):
        """
        Check the stats of started application whether it Running or Down. Try to restart if the app is down and will
        will trigger a mail to user.
        """
        stats = self.client.apps.get_stats(self.guid)
        # Stats of started application
        try:
            state = stats['0']['stats']['state']
        except KeyError:
            state = stats['0']['state']
        # mode = True
        logging.info(': %s application current Status: %s, State: %s', self.app_info['ApplicationName'],
                     self.app_info['Status'], state)
        if state == 'RUNNING':
            uri = "https://" + stats['0']['stats']['uris'][0]
            self.url_data['appUrl'] = uri
            logging.info(' :Checking the URL HTTP State for application %s', self.app_info['ApplicationName'])
            # validating the url
            url_boolean = validate_url(self.url_data)
            if url_boolean is True:
                logging.info(': %s application URL is resolving', self.app_info['ApplicationName'])
            else:
                logging.info(': URL isn\'t resolving for the application %s ', self.app_info['ApplicationName'])
                self.app_info['Remarks'] = 'Url is not resolving though the app is RUNNING state'
                self.write_csv()
                self.send_mail()
            # mode = False
        else:
            try:
                self.app_info['Remarks'] = 'Application Stopped'
                self.send_mail()
                logging.info(': %s application is in STOPPED state, Initiating force START',
                             self.app_info['ApplicationName'])
                # restarting the down app
                self.client.apps.start(self.guid, timeout=10)
                summary_data = self.client.apps.get_summary(self.guid)
                self.get_app_summary(summary_data)
                self.app_info['Remarks'] = 'Application Restarted'
                # triggering a mail
                self.write_csv()
                self.send_mail()
                self.check_summary()
            except AssertionError as assert_error:
                logging.info(': Unable to start the application:%s, Error Code Read:%s',
                             self.app_info['ApplicationName'], assert_error)
                self.app_info['Remarks'] = 'Application is in STOPPED State. FAILED to START the app.'
                self.send_mail()
                self.write_csv()
            # mode = False

    def get_app_summary(self, summary):
        """
        Getting the app info from application summary data. Summary data format varies for the restarted app.
        """
        self.app_info['ApplicationName'] = summary['name']
        self.app_info['Status'] = summary['state']
        self.app_info['Instances'] = (str(summary['instances']) + '//' + str(summary['running_instances']))
        self.app_info['Timestamp'] = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        if summary['state'] == 'STARTED':
            self.app_stats = self.client.apps.get_stats(summary['guid'])
            try:
                state = self.app_stats['0']['stats']['state']
            except KeyError:
                state = self.app_stats['0']['state']
            if state == 'RUNNING':
                self.app_info['AllocatedMemory'] = float(self.app_stats['0']['stats']['mem_quota']) / 1048576
                self.app_info['UsedMemory'] = float(self.app_stats['0']['stats']['usage']['mem']) / 1048576
                self.app_info['CPUUsage'] = "{:.2%}".format(float(self.app_stats['0']['stats']['usage']['cpu']))
                self.app_info['DiskUsage'] = float(self.app_stats['0']['stats']['usage']['disk']) / 1048576
            else:
                self.write_empty_stats()
        else:
            self.write_empty_stats()

    def write_empty_stats(self):
        """

        """
        stat_key_list = ['AllocatedMemory', 'UsedMemory', 'CPUUsage', 'DiskUsage']
        for each in stat_key_list:
            self.app_info[each] = 'None'

    def send_mail(self):
        """
        Connects to a GE mail server and send mail to all the recipients.
        """

        template_env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
        mail_text = template_env.get_template('email_template.html')
        content = mail_text.render(self.app_info)
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(content, 'html'))
        # appending mail tag
        mail_tag = '@mail.ad.ge.com'
        logging.info(': eMail notifications triggered to %s', self.recipients)
        self.recipients = [str(each_user) + mail_tag for each_user in self.recipients]
        # Mail Subject
        msg['Subject'] = 'Application Name:' + self.app_info['ApplicationName'] + '  Status:' + self.app_info['Status']
        # Send the message via SMTP server.
        s = smtplib.SMTP('mail.ad.ge.com')
        s.sendmail('CloudMonitoringTool@mail.ad.ge.com', self.recipients, msg.as_string())
        logging.info(': eMail notifications sent to %s', self.recipients)
        self.recipients = self.input_json_data[3]
        s.quit()


def execute(config_data):
    try:
        if config_data[1] is True:
            cf_endpoint_and_credentials = config_data[2]
            cf_client_obj = connect_to_cloud(cf_endpoint_and_credentials)
        else:
            cf_client_obj = None
        csv_file_path = Path("CloudMonitoring.csv")
        # As CSV acts as temporary date store, tool appends the data to CSV if it exists or create a new file to write.
        if csv_file_path.is_file():
            csv_file = open(str(csv_file_path), "a", newline='', encoding='utf-8')
            csv_writer = csv.DictWriter(csv_file, fieldnames=['ApplicationName', 'Status', 'Instances',
                                                              'Timestamp', 'AllocatedMemory', 'UsedMemory', 'CPUUsage',
                                                              'DiskUsage', 'Remarks'], dialect=csv.excel)
        else:
            csv_file = open(str(csv_file_path), "w", newline='', encoding='utf-8')
            csv_writer = csv.DictWriter(csv_file, fieldnames=['ApplicationName', 'Status', 'Instances',
                                                              'Timestamp', 'AllocatedMemory', 'UsedMemory', 'CPUUsage',
                                                              'DiskUsage', 'Remarks'], dialect=csv.excel)

            csv_writer.writeheader()
        # Initiating the monitor class
        monitor = Monitoring(json_data=config_data, csv_writer=csv_writer, cf_client=cf_client_obj)
        monitor.validate_apps()
        csv_file.close()
    except(FileNotFoundError, KeyError, IndexError, ConnectionResetError,
           ConnectionRefusedError, ConnectionAbortedError, OAuthError) as error_execute:
        logging.info('Error occurred in execute method %s', error_execute)
        pass


if __name__ == '__main__':
    logging.info("::::::::::::::::::::::::: Build Version: 12.0 :::::::::::::::::::::::::")
    logging.info("::::::::::::::::::::::::: Release Version: 1.1 :::::::::::::::::::::::::")
    logging.info("::::::::::::::::::::::::: Release Date: 17 / 11 / 2017 :::::::::::::::::::::::::")
    logging.info(
        '::::::::::::::::::::::::: Initiated monitoring on :::::::::::::::::::::::::' + str(datetime.datetime.now()))
    try:
        chrome_exe_download()
    except OSError as os_error:
        logging.info('Error occurred while downloading the chrome.exe %s', os_error)
        exit_program()
    json_file_data = json_file_parser()

    execute(json_file_data)
    schedule.every(json_file_data[0]).minutes.do(execute, json_file_data)
    var_date = datetime.datetime.now()
    while True:
        idle_seconds = round(schedule.idle_seconds() / 60, 1)
        if idle_seconds >= 0:
            logging.info('::::::::::::::::::::::::: Next CloudMonitor schedule in %s minutes :::::::::::::::::::::::::',
                         str(idle_seconds))
        schedule.run_pending()
        time.sleep(60)
