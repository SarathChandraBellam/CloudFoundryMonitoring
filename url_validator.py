from splinter import Browser
import os, sys
import time
import logging
import requests, zipfile, io
from urllib.parse import urlparse
from msvcrt import getch


def validate_url(url_data):
    if urlparse(url_data['appUrl']).scheme != "https":
        url_data['appUrl'] = "https://" + url_data['appUrl']
    boolean_status = True
    if url_data['isUserInterface'] is True:
        if requests.get(url_data['appUrl'], verify=False).status_code == 200:
            browser = Browser('chrome', headless=True)
            browser.visit(url_data['appUrl'])
            if url_data['authEnabled'] is True:
                try:
                    logging.info("::::::::::::::::::::::::: Going to sleep for 30seconds :::::::::::::::::::::::::")
                    time.sleep(30)
                    logging.info("::::::::::::::::::::::::: Awake!! logging into application :::::::::::::::::::::::::")
                    browser.find_by_id("username").fill(url_data['app_user'])
                    browser.find_by_id("password").fill(url_data['app_key'])
                    button = browser.find_by_id('submitFrm')
                    button.click()
                    if browser.status_code != 200:
                        boolean_status = False
                    else:
                        boolean_status = True
                except Exception as error_url:
                    logging.info(error_url)
                    boolean_status = False
            else:
                if browser.status_code != 200:
                    boolean_status = False
                else:
                    boolean_status = True
            #browser.quit()

    return boolean_status


def chrome_exe_download():
    """
    Method to download the Zipped chrome executable and Unzip to desired location
    """

    if getattr(sys, 'frozen', False) :
        destination_directory = os.path.dirname(sys.executable)
    else:
        destination_directory = os.path.dirname(__file__)

    logging.info('::::::::::::::::::::::::: Checking for Chrome driver plugin :::::::::::::::::::::::::')
    chrome_file_path = os.path.join(destination_directory, 'chromedriver.exe')
    if not os.path.isfile(chrome_file_path):
        logging.info('::::::::::::::::::::::::: Chrome driver plugin is not available, Downloading Chrome driver V2.33 :::::::::::::::::::::::::')
        logging.info(': Chrome download path::::' + chrome_file_path)
        r = requests.get('https://chromedriver.storage.googleapis.com/2.33/chromedriver_win32.zip', verify=False)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(destination_directory)
    else:
        logging.info('::::::::::::::::::::::::: Chrome driver plugin is available, skipping download :::::::::::::::::::::::::')

def exit_program():
    """
    exit from code when the user press any key
    """
    print("Press any key to Exit")
    junk = getch()
    if junk:
        sys.exit()

