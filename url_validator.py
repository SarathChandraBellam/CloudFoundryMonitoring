from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os, sys
import time
import logging
import requests, zipfile, io
from urllib.parse import urlparse
from msvcrt import getch


def validate_url(url_data):
    logging.info("::::::::::::::::::::::::: Validating the url :::::::::::::::::::::::::")
    if urlparse(url_data['appUrl']).scheme != "https":
        url_data['appUrl'] = "https://" + url_data['appUrl']
    boolean_status = True
    if url_data['isUserInterface'] is True:
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('disable-gpu')
            options.add_argument('window-size=1200,1100')
            options.add_argument('log-level=3')
            driver = webdriver.Chrome(executable_path='chromedriver.exe', options=options)
            driver.get(url_data['appUrl'])
            if url_data['authEnabled'] is True:
                logging.info("::::::::::::::::::::::::: logging into application :::::::::::::::::::::::::")
                wait = WebDriverWait(driver, 20)
                element_user = wait.until(EC.presence_of_element_located((By.ID, 'username')))
                element_user.send_keys(url_data['app_user'])
                element_password = driver.find_element_by_id('password')
                element_password.send_keys(url_data['app_key'])
                submit = driver.find_element_by_id('submitFrm')
                submit.click()
            driver.quit()
            logging.info("::::::::::::::::::::::::: Success :::::::::::::::::::::::::")
        except Exception as error_url:
            logging.info(error_url)
            boolean_status = False
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
        r = requests.get('https://chromedriver.storage.googleapis.com/2.36/chromedriver_win32.zip', verify=False)
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

