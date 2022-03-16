import os
import urllib
from urllib.parse import urlparse

import requests
from bs4 import Tag
from requests import codes

from LibGen import base_url, get_soup_from_page


def create_dir(path):
    try:
        os.makedir(path)
    except FileExistsError:
        pass


def get_output_path(run_parameters, bundle_name):
    """
        Checks if a proper output build exists, creates it if not and
        returns the final path

        final_path = output_path\\humble_name
    :return: The full path
    """
    out_dir = run_parameters['output_dir']
    if not out_dir:
        out_dir = os.path.join(os.path.expanduser('~'), 'HumbleJsonBooks')
    out_dir = os.path.join(out_dir, bundle_name)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def get_mirror_list(libgen_md5_url=''):
    mirror_list = []
    if libgen_md5_url:
        soup = get_soup_from_page(libgen_md5_url)
        if soup:
            if libgen_md5_url.find('/fiction/') >= 0:
                mirror_location = '.record_mirrors li a'
            else:
                mirror_location = 'tr:nth-child(18) td a'
            mirrors = soup.select(mirror_location)
            for mirror in mirrors:
                if type(mirror) is Tag:
                    url_parts = urlparse(mirror.get('href', ''))
                    if url_parts.scheme.find('http') >= 0:
                        mirror_list.append(url_parts.hostname)
    return mirror_list


def get_download_link_from_library_lol(run_parameters, book_url, md5, path):
    # TODO if using the ipfs links we can get the filename from the "filename" parameter in the url
    url_parts = urlparse(book_url)
    if book_url.find('/fiction/') >= 0:
        download_page_url = '{}://{}{}'.format(url_parts.scheme, run_parameters['libgen_mirrors'][0], url_parts.path)
    else:
        download_page_url = '{}://{}/main/{}'.format(url_parts.scheme, run_parameters['libgen_mirrors'][0], md5)
    soup = get_soup_from_page(download_page_url)
    get_link = soup.select('#download a')
    if get_link:
        download_link = get_link[0].get('href', '')
        filename = urllib.parse.unquote(book_url[book_url.rfind('/') + 1:])
        get_book(download_link, path, filename)


def get_download_link_from_libgen_rocks(run_parameters, book, md5, path):
    url_parts = urlparse(book['url'])
    # we need md5 and key parameters to generate a valid URL
    download_page_url = '{}://{}/ads.php?md5={}'.format(url_parts.scheme, run_parameters['libgen_mirrors'][1], md5)
    soup = get_soup_from_page(download_page_url)
    get_link = soup.select('#main td:nth-of-type(2) a')
    if get_link:
        download_link = '{}://{}/{}'.format(url_parts.scheme, run_parameters['libgen_mirrors'][1], get_link[0]['href'])
        # this link doesn't have a filename
        get_book(download_link, path, filename='', extension=book['extension'], md5=md5)


def get_filename_from_header(request, md5):
    # this works in the library_lol mirror
    header = request.headers.get('Content-Disposition', '')
    if header:
        if header[22] == ' ':
            return header[23:-1]
        else:
            return header[22:-1]
    return md5


def generate_filename(path, filename, extension):
    name = os.path.join(path, filename)
    numbered_name = name
    if os.path.exists(name):
        name_without_ext = name[:name.rfind('.')]
        idx = 0
        while os.path.exists(numbered_name):
            idx += 1
            numbered_name = '{}_{}.{}'.format(name_without_ext, idx, extension)
    return numbered_name


def get_book(book_url, path, filename, extension, md5):
    if book_url:
        print('Requesting book from {}'.format(book_url))
        file_req = requests.get(book_url, timeout=60 * 5)
        if not filename:
            filename = get_filename_from_header(file_req, md5)
        if file_req.status_code == codes.ok:
            full_filename = generate_filename(path, filename, extension)
            with open(full_filename, 'wb') as f:
                f.write(file_req.content)
            print('Book downloaded successfully from {} to {}'.format(book_url, os.path.join(path, filename)))


def get_file_from_url(run_parameters, bundle_data, book, md5):
    if (not run_parameters) or (not run_parameters['libgen_mirrors']) or \
            (not bundle_data) or (not book['url']) or (not md5):
        return
    path = get_output_path(run_parameters=run_parameters, bundle_name=bundle_data.get('machine_name', ''))
    get_download_link_from_libgen_rocks(run_parameters=run_parameters, book=book, md5=md5, path=path)
