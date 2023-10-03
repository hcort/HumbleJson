import datetime
import os

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from slugify import slugify
from tqdm import tqdm
from requests import codes

import json
from utils import generate_filename, run_parameters, delete_all_files, wait_for_file_download_complete

OPERA_PREFS = "C:\\Users\\Héctor\\Desktop\\compartido_msedge\\PyCharmProjects\\HumbleJson\\opera_prefs\\"


def get_driver_opera(
        # opera_exe_location="C:\\Users\\Héctor\\AppData\\Local\\Programs\\Opera\\opera.exe",
        opera_exe_location='',
        opera_preferences_location=OPERA_PREFS):
    # use custom preferences file to change the download folder
    from selenium.webdriver.opera.options import Options
    opera_options = Options()
    opera_options.binary_location = opera_exe_location
    opera_options.add_argument(f'user-data-dir={opera_preferences_location}')
    return webdriver.Opera(options=opera_options)


class OperaDriver:

    def __init__(self):
        self.__driver = None
        self.__download_folder = None
        self.__use_opera_vpn = False

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
            self.set_download_folder()
            self.__driver = get_driver_opera()
            self.__use_opera_vpn = True
        return self.__driver

    def set_download_folder(self):
        time_str = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        self.__download_folder = os.path.join(run_parameters['output_dir'], time_str)
        os.makedirs(self.__download_folder, exist_ok=True)
        with open(os.path.join(OPERA_PREFS, 'Preferences_custom.txt'), 'r') as file:
            prefs_dict = json.load(file)
            prefs_dict['download']['default_directory'] = self.__download_folder
            with open(os.path.join(OPERA_PREFS, 'Preferences'), 'w') as output_file:
                json.dump(prefs_dict, output_file)


selenium_driver = OperaDriver()


def get_soup_from_page(current_url, use_opera_vpn=True):
    if use_opera_vpn:
        return get_soup_from_page_selenium(current_url)
    else:
        return get_soup_from_page_requests(current_url)


def get_soup_from_page_requests(current_url):
    soup = None
    req = requests.get(current_url)
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


def get_book(book_url, path, filename, extension='', md5=''):
    if selenium_driver.use_opera_vpn:
        return get_book_selenium(book_url, path, filename, extension, md5)
    else:
        return get_book_requests(book_url, path, filename, extension, md5)


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
        print('Requesting book from {}'.format(book_url))
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
                        desc="Progress",
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024
                ) as progress:
                    for chunk in file_req.iter_content(chunk_size=chunk_size):
                        data_size = f.write(chunk)
                        progress.update(data_size)
            print('Book downloaded successfully from {} to {}'.format(book_url, os.path.join(path, filename)))


def get_book_selenium(css_path, book_url, path, filename, extension, md5):
    download_url = selenium_driver.driver.current_url
    try:
        link = selenium_driver.driver.find_element(By.CSS_SELECTOR, css_path)
        delete_all_files(selenium_driver.download_folder)
        link.click()
        # TODO control for Bad Gateway info
        wait_for_file_download_complete(selenium_driver.download_folder)
        download_filename = os.listdir(selenium_driver.download_folder)[0]
        filename, file_extension = os.path.splitext(download_filename)
        valid_filename = f'{slugify(filename, max_length=100)}.{file_extension}'
        os.rename(
            os.path.join(selenium_driver.download_folder, download_filename),
            os.path.join(selenium_driver.download_folder, valid_filename)
        )
        os.replace(
            os.path.join(selenium_driver.download_folder, valid_filename),
            os.path.join(path, valid_filename)
        )
        return True
    except Exception as ex:
        print(f'Unable to download {download_url} - {ex}')
    return False


def test_opera():
    driver = get_driver_opera()
    driver.get("https://libgen.is")
    import time
    time.sleep(50000)


# Lanzamos la función principal
if __name__ == "__main__":
    test_opera()
