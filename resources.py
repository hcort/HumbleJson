"""
    This file is here to contain the several resources I need to keep under control


"""
from OperaDriver import OperaDriver
from Pool import LibgenDownloadPool


class HumbleResources:

    def __init__(self):
        self.__pool = LibgenDownloadPool()
        self.__selenium_driver = OperaDriver()

    def __del__(self):
        self.__pool.wait_for_all_threads()
        pass

    @property
    def driver(self):
        return self.__selenium_driver

    @property
    def pool(self):
        return self.__pool


humble_resources = HumbleResources()
