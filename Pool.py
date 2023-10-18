from multiprocessing.pool import ThreadPool
from threading import Lock


class LibgenDownloadPool:

    def __init__(self):
        self.__pool = ThreadPool(processes=4)

    def __del__(self):
        # wait for threads to end
        self.__pool.close()
        self.__pool.join()


mutex = Lock()
