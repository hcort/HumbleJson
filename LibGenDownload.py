import os
import urllib
from urllib.parse import urlparse
from bs4 import Tag

from Connections import get_soup_from_page, get_book_requests, get_book_selenium, selenium_driver


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
        get_book_requests(download_link, path, filename)


def get_download_link_from_libgen_rocks(run_parameters, book, md5, path):
    """
        Every libgen mirror has minor differences.

        In libgen_rocks, libgen.is, etc, the css path to the download link is "#main td:nth-of-type(2) a"

        The file name of the book is in the GET url, so we can take it from there

    :param run_parameters:
    :param book:
    :param md5:
    :param path:
    :return:
    """
    url_parts = urlparse(book['url'])
    # we need md5 and key parameters to generate a valid URL
    download_page_url = '{}://{}/ads.php?md5={}'.format(url_parts.scheme, run_parameters['libgen_mirrors'][1], md5)
    soup = get_soup_from_page(download_page_url)
    if soup:
        css_path = '#main td:nth-of-type(2) a'
        if selenium_driver.use_opera_vpn:
            return get_book_selenium(css_path=css_path, book_url='', path=path,
                              filename='', extension=book['extension'], md5=md5)
        else:
            get_link = soup.select(css_path)
            if get_link:
                download_link = '{}://{}/{}'.format(url_parts.scheme,
                                                    run_parameters['libgen_mirrors'][1], get_link[0]['href'])
                # this link doesn't have a filename
                return get_book_requests(download_link, path, filename='', extension=book['extension'], md5=md5)
    else:
        print(f'Unable to get {download_page_url}')
    return False


def get_file_from_url(run_parameters, bundle_data, book, md5):
    if (not run_parameters) or (not run_parameters['libgen_mirrors']) or \
            (not bundle_data) or (not book['url']) or (not md5):
        return
    path = get_output_path(run_parameters=run_parameters, bundle_name=bundle_data.get('machine_name', ''))
    return get_download_link_from_libgen_rocks(run_parameters=run_parameters, book=book, md5=md5, path=path)
