"""
    Handles the connections to different URLs.

    Access to Humble Bundle is done using Requests
    Access to LibGen is usually done with Opera webdriver because it's sometimes blocked by ISP

"""
import datetime
import os
import shutil

import requests
from bs4 import BeautifulSoup
from requests import codes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.opera.options import Options
from tqdm import tqdm

import json
from Pool import max_download_limit
from utils import generate_filename, run_parameters

OPERA_PREFERENCES_FOLDER = 'C:\\Users\\Héctor\\Desktop\\compartido_msedge\\PyCharmProjects\\HumbleJson\\opera_prefs\\'


class OperaDriver:
    """
        Encapsulates a Selenium Opera driver

        We use Opera as a driver because we want to use the built-in VPN to by-pass some proxy or firewall
        restrictions.

        To use the built-in VPN it must be enabled in the Preferences file

        A new preferences folder is created in each run to start the browser from scratch, avoiding
        caches, browser history, etc

        Its shutdown is blocked by pool_running_mutex, so it waits to the pool to complete all downloads
    """

    def __init__(self):
        self.__driver = None
        self.__download_folder = None
        self.__use_opera_vpn = False
        self.__opera_temp_prefs = None
        self.__opera_org_prefs = None

    def __del__(self):
        print('close driver')
        if self.__driver:
            self.__driver.close()
        shutil.rmtree(self.__download_folder, ignore_errors=True)
        shutil.rmtree(self.__opera_temp_prefs, ignore_errors=True)

    def get_driver_opera(self,
                         opera_exe_location='',
                         opera_preferences_location=None):   # pylint: disable=unused-argument
        if not opera_preferences_location:
            opera_preferences_location = OPERA_PREFERENCES_FOLDER
        self.__opera_org_prefs = opera_preferences_location
        self.copy_preferences_file()
        self.set_download_folder()
        opera_options = Options()
        opera_options.binary_location = opera_exe_location
        # use custom preferences file to change the download folder
        opera_options.add_argument(f'user-data-dir={self.__opera_temp_prefs}')
        self.__driver = webdriver.Opera(options=opera_options)

    def copy_preferences_file(self):
        self.__opera_temp_prefs = os.path.join(os.getcwd(), 'opera_prefs_temp')
        shutil.rmtree(self.__opera_temp_prefs, ignore_errors=True)
        os.mkdir(self.__opera_temp_prefs)
        shutil.copyfile(os.path.join(self.__opera_org_prefs, 'Preferences_custom.txt'),
                        os.path.join(self.__opera_temp_prefs, 'Preferences'))

    @property
    def download_folder(self):
        if not self.__download_folder:
            self.set_download_folder()
        return self.__download_folder

    @property
    def use_opera_vpn(self):
        return self.__use_opera_vpn

    @property
    def driver(self):
        if not self.__driver:
            self.get_driver_opera()
            self.__use_opera_vpn = True
        return self.__driver

    def set_download_folder(self):
        time_str = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        self.__download_folder = os.path.join(run_parameters['output_dir'], time_str)
        os.makedirs(self.__download_folder, exist_ok=True)
        with open(os.path.join(self.__opera_temp_prefs, 'Preferences'), 'r', encoding='utf-8') as file_org:
            prefs_dict = json.load(file_org)
            prefs_dict['download']['default_directory'] = self.__download_folder
        if prefs_dict:
            with open(os.path.join(self.__opera_temp_prefs, 'Preferences'), 'w', encoding='utf-8') as file_dst:
                json.dump(prefs_dict, file_dst)


selenium_driver = OperaDriver()


def get_soup_from_page(current_url, use_opera_vpn=True):
    if use_opera_vpn:
        return get_soup_from_page_selenium(current_url)
    else:
        return get_soup_from_page_requests(current_url)


def get_soup_from_page_requests(current_url):
    soup = None
    req = requests.get(current_url, timeout=30)
    if req.status_code != requests.codes.ok:
        return None
    response = req.content
    soup = BeautifulSoup(response, 'html.parser', from_encoding='utf-8')
    return soup


def get_soup_from_page_selenium(current_url):
    soup = None
    selenium_driver.driver.set_page_load_timeout(30)
    selenium_driver.driver.get(current_url)
    soup = BeautifulSoup(selenium_driver.driver.page_source, 'html.parser', from_encoding='utf-8')
    return soup


def get_filename_from_header(request, md5):
    # this works in the library_lol mirror
    header = request.headers.get('Content-Disposition', '')
    if header:
        if header[22] == ' ':
            filename = header[23:-1]
        else:
            filename = header[22:-1]
    else:
        filename = md5
    return filename


def get_book_requests(book_url, path, filename, extension='', md5=''):
    if book_url:
        print(f'Requesting book from {book_url}')
        file_req = requests.get(book_url, book_url, timeout=60 * 5, stream=True)
        if not filename:
            filename = get_filename_from_header(file_req, md5)
        total_size = int(file_req.headers.get('content-length', 0))
        if file_req.status_code == codes.ok:
            full_filename = generate_filename(path, filename, extension)
            chunk_size = 5 * 1024
            with open(full_filename, 'wb') as f:
                with tqdm(
                        total=total_size,
                        desc='Progress',
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024
                ) as progress:
                    for chunk in file_req.iter_content(chunk_size=chunk_size):
                        data_size = f.write(chunk)
                        progress.update(data_size)
            print(f'Book downloaded successfully from {book_url} to {os.path.join(path, filename)}')


def get_book_selenium(css_path):
    download_url = selenium_driver.driver.current_url
    try:
        link = selenium_driver.driver.find_element(By.CSS_SELECTOR, css_path)
        # delete_all_files(selenium_driver.download_folder)
        print(f'Acquiring semaphore {max_download_limit}')
        max_download_limit.acquire()
        link.click()
        return True
    except Exception as ex:
        print(f'Unable to download {download_url} - {ex}')
    return False
