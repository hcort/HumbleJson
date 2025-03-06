"""
    Handles the connections to different URLs.

    Access to Humble Bundle is done using Requests
    Access to LibGen is usually done with Opera webdriver because it's sometimes blocked by ISP

"""
import os
import sys
import time

import requests
from bs4 import BeautifulSoup
from requests import codes
import selenium
if selenium.__version__ == '3.141.0':
    from selenium.webdriver.common.keys import Keys
else:
    from selenium.webdriver import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from tqdm import tqdm

from resources import humble_resources
from utils import generate_filename, libgen_search


def scroll_to_end():
    if not libgen_search.get('do_scroll', False):
        return
    keep_scrolling = True
    i = 3
    while keep_scrolling:
        try:
            humble_resources.driver.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
            time.sleep(1)
            i -= 1
            keep_scrolling = i >= 0
        except NoSuchElementException:
            keep_scrolling = False


def get_soup_from_page(current_url, use_opera_vpn=True):
    if use_opera_vpn:
        return get_soup_from_page_selenium(current_url)
    else:
        return get_soup_from_page_requests(current_url)


def get_soup_from_page_requests(current_url):
    req = requests.get(current_url, timeout=30)
    if req.status_code != requests.codes.ok:
        return None
    response = req.content
    soup = BeautifulSoup(response, 'html.parser', from_encoding='utf-8')
    return soup


def get_soup_from_page_selenium(current_url):
    humble_resources.driver.driver.set_page_load_timeout(3000)
    humble_resources.driver.driver.get(current_url)
    # FIXME anna's archive -> necesita scroll
    scroll_to_end()
    soup = BeautifulSoup(humble_resources.driver.driver.page_source, 'html.parser', from_encoding='utf-8')
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
    download_url = humble_resources.driver.driver.current_url
    try:
        link = humble_resources.driver.driver.find_element(By.CSS_SELECTOR, css_path)
        # delete_all_files(humble_resources.download_folder)
        print(f'Acquiring semaphore {humble_resources.pool.max_download_limit}')
        humble_resources.pool.max_download_limit.acquire()
        link.click()
        # espero para comprobar si no me redirecciona a página de error
        time.sleep(1)
        if humble_resources.driver.driver.current_url != download_url:
            raise ConnectionError(humble_resources.driver.driver.find_element(By.TAG_NAME, 'body').text)
        return True
    except Exception as ex:
        print(f'Unable to download {download_url} - {ex}', file=sys.stderr)
        humble_resources.pool.max_download_limit.release()
    return False


def get_book_selenium_by_url(url):
    download_url = humble_resources.driver.driver.current_url
    try:
        print(f'Acquiring semaphore {humble_resources.pool.max_download_limit}')
        humble_resources.pool.max_download_limit.acquire()
        humble_resources.driver.driver.get(url)
        # espero para comprobar si no me redirecciona a página de error
        time.sleep(1)
        try:
            humble_resources.driver.driver.find_element(By.CSS_SELECTOR, 'body.neterror')
            raise ConnectionError(humble_resources.driver.driver.find_element(By.TAG_NAME, 'body').text)
        except NoSuchElementException:
            pass
        return True
    except Exception as ex:
        print(f'Unable to download {download_url} - {ex}', file=sys.stderr)
        humble_resources.pool.release()
    return False
