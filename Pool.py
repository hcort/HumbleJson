import datetime
import os
from multiprocessing.pool import ThreadPool
from threading import Lock, Semaphore
from time import sleep

from utils import move_file_download_folder

wait_for_download_files = set()
# limit the amount of simultaneous downloads
MAX_SIMULTANEOUS_DOWNLOADS = 2
max_download_limit = Semaphore(MAX_SIMULTANEOUS_DOWNLOADS)


thread_id = 0


def get_thread_sequential_id():
    global thread_id
    with mutex:
        thread_id += 1
        return thread_id


def wait_and_retry(retries):
    sleep(3)
    if retries == 0:
        return TimeoutError('Max number of retries downloading - Download not started')
    return retries - 1


def check_for_new_file(folder):
    retries = 10
    with mutex:
        while len(os.listdir(folder)) == len(wait_for_download_files):
            retries = wait_and_retry(retries)
        retries = 10
        while retries > 0:
            # the download starts with a mangled filename with tmp extension before renaming to final name
            for file in os.listdir(folder):
                if (not file.endswith('.tmp')) and (file.endswith('.opdownload')) and (not (file in wait_for_download_files)):
                    wait_for_download_files.add(file)
                    print(f'Waiting for file: {file}')
                    return file
            retries = wait_and_retry(retries)
    return None


def remove_file_from_waiting_list(file):
    with mutex:
        wait_for_download_files.remove(file)


def wait_for_file_download_complete(folder, path):
    wait_thread_id = get_thread_sequential_id()
    print(f'Starting thread {wait_thread_id}')
    download_complete = False
    last_size = -1
    init_time = datetime.datetime.now()
    file_exists_retries = 10
    size_change_retries = 200
    file_downloading = check_for_new_file(folder)
    if not file_downloading:
        return False
    # remove the .opdownload to get the final filename
    file_downloading_base, file_downloading_extension = os.path.splitext(file_downloading)
    if file_downloading_extension != '.opdownload':
        # not temporary file (?)
        file_downloading_base = file_downloading
    while not download_complete:
        from time import sleep
        sleep(3)
        if os.path.isfile(os.path.join(folder, file_downloading)):
            current_size = os.path.getsize(os.path.join(folder, file_downloading))
        else:
            file_exists_retries -= 1
        is_file = os.path.isfile(os.path.join(folder, file_downloading_base))
        size_not_changed = (last_size == current_size)
        download_complete = is_file and size_not_changed
        if last_size == current_size:
            size_change_retries -= 1
        else:
            size_change_retries = 200
        last_size = current_size
        if (not download_complete) and ((size_change_retries < 0) or (file_exists_retries < 0)):
            break
    remove_file_from_waiting_list(file_downloading)
    if (not download_complete) and ((size_change_retries < 0) or (file_exists_retries < 0)):
        raise TimeoutError('Max number of retries downloading')
    move_file_download_folder(folder, path, file_downloading_base)
    return True


def thread_file_download(download_folder, path, bundle_dict, bundle_item, md5):
    try:
        if wait_for_file_download_complete(download_folder, path):
            bundle_dict.set_book_downloaded(bundle_item, md5)
            print(f'Download finished {bundle_item} - {md5}')
        else:
            print(f'Unable to download {bundle_item} - {md5}')
    except Exception as err:
        print(f'Error downloading {bundle_item} - {md5} - {err}')
    print('Releasing semaphore' + max_download_limit.__str__())
    max_download_limit.release()


class LibgenDownloadPool:

    def __init__(self):
        self.__pool = ThreadPool(processes=4)
        self.__bundle_dict = None
        self.__pending_results = {}

    def __del__(self):
        # wait for threads to end
        for bundle_item in self.__pending_results:
            for md5_wait in bundle_item:
                self.__pending_results[bundle_item][md5_wait].wait()
        self.__pool.close()
        self.__pool.join()

    @property
    def bundle_dict(self):
        return self.__bundle_dict

    @bundle_dict.setter
    def bundle_dict(self, bundle_dict):
        self.__bundle_dict = bundle_dict

    def add_selenium_download(self, bundle_item, md5, download_folder, path):
        async_res = self.__pool.apply_async(thread_file_download,
                                            args=(download_folder, path, self.__bundle_dict, bundle_item, md5))
        if not (bundle_item in self.__pending_results):
            self.__pending_results[bundle_item] = {}
        self.__pending_results[bundle_item][md5] = async_res


mutex = Lock()

thread_pool = LibgenDownloadPool()
