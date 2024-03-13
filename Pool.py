"""
    Thread pool to handle several simultaneous downloads

    Initial version only works using the Opera driver.
    In Opera, the browser handles the download and we only have to wait for it to finish. This is the
    process done in each thread

    Use MAX_SIMULTANEOUS_DOWNLOADS to create a semaphore that limits the number of downloads

    The process of downloading is done sequentially:
     - get_book_selenium (Connections) navigates to the download page and clicks on the download link
     - add_selenium_download starts the waiting thread

    To start a download we need that the driver clicks on the download link

    There are two mutexes:
     - bundle_dict_access_mutex protects the bundle data from concurrent write operations
     - pool_running_mutex protects the webdriver to be closed before all the downloads have ended

"""
import os
import sys
import time
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
    with LibgenDownloadPool.thread_id_mutex:
        thread_id += 1
        return thread_id


def wait_and_retry(retries):
    sleep(3)
    if retries == 0:
        raise TimeoutError('Max number of retries downloading - Download not started')
    return retries - 1


def check_for_new_file(folder):
    time.sleep(3)
    with LibgenDownloadPool.pending_files_mutex:
        retries = 10
        with LibgenDownloadPool.download_folder_mutex:
            while (len(os.listdir(folder)) == len(wait_for_download_files)) and (retries >= 0):
                retries = wait_and_retry(retries)
            retries = 10
            while retries > 0:
                # the download starts with a mangled filename with tmp extension before renaming to final name
                # opdownload is only used in files bigger than some threshold, small files are downloaded with
                # their own name
                non_pending_files = [x for x in os.listdir(folder) if x not in wait_for_download_files]
                print('Files in download folder not in list: ' + '\n'.join(non_pending_files))
                print('Files in pending list: ' + '\n'.join(wait_for_download_files))
                if not non_pending_files:
                    wait_and_retry(retries)
                else:
                    for pending_file in non_pending_files:
                        # if the file doesn't end with opdownload it might be a just finished download
                        if pending_file.endswith('.opdownload') or (
                                (not pending_file.endswith('.opdownload')) and (
                                not (pending_file + '.opdownload') in wait_for_download_files)):
                            wait_for_download_files.add(pending_file)
                            print(f'Waiting for file: {pending_file}')
                            return pending_file
                retries -= 1
    return None


def remove_file_from_waiting_list_and_move(file_downloading, file_downloading_base, folder, path):
    with LibgenDownloadPool.pending_files_mutex:
        wait_for_download_files.remove(file_downloading)
        move_file_download_folder(folder, path, file_downloading_base)


def wait_for_file_download_complete(folder, path):
    wait_thread_id = get_thread_sequential_id()
    print(f'wait_for_file_download_complete - Starting thread {wait_thread_id}')
    download_complete = False
    last_size = -1
    file_exists_retries = 10
    size_change_retries = 200
    file_downloading = check_for_new_file(folder)
    print(f'wait_for_file_download_complete - {wait_thread_id} Wait for {file_downloading}')
    if not file_downloading:
        return False
    # remove the .opdownload to get the final filename
    file_downloading_base, file_downloading_extension = os.path.splitext(file_downloading)
    if file_downloading_extension != '.opdownload':
        # not temporary file (?)
        file_downloading_base = file_downloading
    current_size = -1
    while not download_complete:
        print(f'wait_for_file_download_complete - {wait_thread_id} loop {size_change_retries} - {file_exists_retries}')
        time.sleep(3)
        if os.path.isfile(os.path.join(folder, file_downloading)):
            current_size = os.path.getsize(os.path.join(folder, file_downloading))
        else:
            file_exists_retries -= 1
        is_file = os.path.isfile(os.path.join(folder, file_downloading_base))
        size_not_changed = last_size == current_size
        download_complete = is_file and size_not_changed
        if last_size == current_size:
            size_change_retries -= 1
        else:
            size_change_retries = 200
        last_size = current_size
        if (not download_complete) and ((size_change_retries < 0) or (file_exists_retries < 0)):
            break
    if (not download_complete) and ((size_change_retries < 0) or (file_exists_retries < 0)):
        raise TimeoutError(f'Max number of retries downloading {file_downloading_base}')
    remove_file_from_waiting_list_and_move(file_downloading, file_downloading_base, folder, path)
    print(f'wait_for_file_download_complete - {wait_thread_id} file moved {file_downloading} -> {folder}')
    return True


def thread_file_download(download_folder, path, bundle_dict, bundle_item, md5):
    try:
        if wait_for_file_download_complete(download_folder, path):
            bundle_dict.set_book_downloaded(bundle_item, md5)
            print(f'Download finished {bundle_item} - {md5}')
        else:
            print(f'Unable to download {bundle_item} - {md5}')
    except Exception as err:
        print(f'Error downloading {bundle_item} - {md5} - {err}', file=sys.stderr)
    print(f'Releasing semaphore {max_download_limit}')
    max_download_limit.release()


class LibgenDownloadPool:
    """
        LibgenDownloadPool encapsulates a thread pool.

        It also has access to the BundleInfo dictionary to update the download status of each
        book found.
    """

    thread_id_mutex = Lock()
    download_folder_mutex = Lock()
    pending_files_mutex = Lock()

    def __init__(self):
        self.__pool = ThreadPool(processes=4)
        self.__bundle_dict = None
        self.__pending_results = {}

    def __del__(self):
        print('close pool')
        # wait for threads to end
        self.__pool.close()
        self.__pool.join()
        print('pool closed')

    @property
    def bundle_dict(self):
        return self.__bundle_dict

    @bundle_dict.setter
    def bundle_dict(self, bundle_dict):
        self.__bundle_dict = bundle_dict

    def add_selenium_download(self, bundle_item, md5, download_folder, path):
        async_res = self.__pool.apply_async(thread_file_download,
                                            args=(download_folder, path, self.__bundle_dict, bundle_item, md5))
        if bundle_item not in self.__pending_results:
            self.__pending_results[bundle_item] = {}
        self.__pending_results[bundle_item][md5] = async_res

    def wait_for_all_threads(self):
        print('wait_for_all_threads')
        for bundle_item, threads_waiting in self.__pending_results.items():
            for md5_wait in threads_waiting:
                print(f'waiting for {md5_wait}')
                self.__pending_results[bundle_item][md5_wait].wait()
