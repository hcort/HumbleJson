"""
    Contains the class that wraps a selenium driver
"""
import datetime
import os
import shutil
import sys
import time

from selenium import webdriver
from selenium.webdriver.opera.options import Options

import json
from utils import run_parameters, move_file_download_folder

OPERA_PREFERENCES_FOLDER = 'C:\\Users\\Héctor\\Desktop\\compartido_msedge\\PyCharmProjects\\HumbleJson\\opera_prefs\\'


class OperaDriver:
    """
        Encapsulates a Selenium Opera driver

        We use Opera as a driver because we want to use the built-in VPN to by-pass some proxy or firewall
        restrictions.

        To use the built-in VPN it must be enabled in the Preferences file

        A new preferences folder is created in each run to start the browser from scratch, avoiding
        caches, browser history, etc

    """

    def __init__(self):
        self.__driver = None
        self.__download_folder = None
        self.__use_opera_vpn = False
        self.__opera_temp_prefs = None
        self.__opera_org_prefs = None
        self.__destination_path = None

    def __del__(self):
        print('close driver')
        if self.__driver:
            try:
                self.__driver.quit()
                time.sleep(1)
            except Exception as err:
                print(err)
        self._empty_downloads_folder()
        shutil.rmtree(self.__download_folder, ignore_errors=True)
        shutil.rmtree(self.__opera_temp_prefs, ignore_errors=True)
        print('driver closed')

    def get_driver_opera(self,
                         # opera_exe_location=r'\opera_bin\102.0.4880.78\opera.exe',
                         opera_exe_location='',
                         opera_preferences_location=None):   # pylint: disable=unused-argument
        if not opera_preferences_location:
            opera_preferences_location = OPERA_PREFERENCES_FOLDER
        self.__opera_org_prefs = opera_preferences_location
        self.copy_preferences_file()
        self._set_vpn_in_prefs()
        self.set_download_folder()
        opera_options = Options()
        opera_options.binary_location = opera_exe_location
        # use custom preferences file to change the download folder
        opera_options.add_argument(f'user-data-dir={self.__opera_temp_prefs}')
        try:
            if opera_exe_location:
                self.__driver = webdriver.Opera(options=opera_options, executable_path=opera_exe_location)
            else:
                self.__driver = webdriver.Opera(options=opera_options)
            time.sleep(15)
        except Exception as err:
            print(f'Error creating driver {err}', file=sys.stderr)
            self.__driver = None
        pass

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
    def destination_path(self):
        return self.__destination_path

    @destination_path.setter
    def destination_path(self, path):
        if not self.__destination_path:
            self.__destination_path = path
            os.makedirs(self.__destination_path, exist_ok=True)

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

    def _set_vpn_in_prefs(self):
        """
            I need this two elements in the preferences file

            The first enables the VPN, the second tells the browser to download PDFs, not try to open them

            "freedom": {
                "proxy_switcher": {
                    "automatic_connection": true,
                    "enabled": true,
                    "forbidden": false,
                    "local_searches": false,
                }
            }

            "plugins": {
                "always_open_pdf_externally": true
            },
        """
        with open(os.path.join(self.__opera_temp_prefs, 'Preferences'), 'r', encoding='utf-8') as file_org:
            prefs_dict = json.load(file_org)
            prefs_dict['freedom'] = dict(proxy_switcher={
                'automatic_connection': True,
                'enabled': True,
                'forbidden': False,
                'local_searches': False,
            })
            prefs_dict['plugins'] = {
                'always_open_pdf_externally': True
            }
        if prefs_dict:
            with open(os.path.join(self.__opera_temp_prefs, 'Preferences'), 'w', encoding='utf-8') as file_dst:
                json.dump(prefs_dict, file_dst)

    def _empty_downloads_folder(self):
        pending_files = os.listdir(self.__download_folder)
        for item in pending_files:
            _, file_downloading_extension = os.path.splitext(item)
            if file_downloading_extension != '.opdownload':
                move_file_download_folder(self.__download_folder, self.__destination_path, item)