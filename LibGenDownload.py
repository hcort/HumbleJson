"""
    Functions to extract the download links for the books in LibGen.
    Different LibGen mirrors may have different HTML structures, so we have to build custom selectors

    The actual downloads have been moved to Connections

"""
import os
import urllib
from urllib.parse import urlparse

from bs4 import Tag

from Connections import get_soup_from_page, get_book_requests, get_book_selenium, selenium_driver
from Pool import thread_pool


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
                if isinstance(mirror, Tag):
                    url_parts = urlparse(mirror.get('href', ''))
                    if url_parts.scheme.find('http') >= 0:
                        mirror_list.append(url_parts.hostname)
    return mirror_list


def get_download_link_from_library_lol(run_parameters, book_url, md5, path):
    # TODO if using the ipfs links we can get the filename from the "filename" parameter in the url
    url_parts = urlparse(book_url)
    if book_url.find('/fiction/') >= 0:
        download_page_url = f'{url_parts.scheme}://{run_parameters["libgen_mirrors"][0]}{url_parts.path}'
    else:
        download_page_url = f'{url_parts.scheme}://{run_parameters["libgen_mirrors"][0]}/main/{md5}'
    soup = get_soup_from_page(download_page_url)
    get_link = soup.select('#download a')
    if get_link:
        download_link = get_link[0].get('href', '')
        filename = urllib.parse.unquote(book_url[book_url.rfind('/') + 1:])
        get_book_requests(download_link, path, filename)


def get_download_link_from_cloudfare_mirror(run_parameters, bundle_data, bundle_item, book, md5, path):
    # book url              https://libgen.is/book/index.php?md5=8B010ACAD53B8D1228ABA81396F4BA04
    # download link         https://libgen.li/ads.php?md5=8B010ACAD53B8D1228ABA81396F4BA04
    # where i want to go    http://library.lol/main/8B010ACAD53B8D1228ABA81396F4BA04
    # document.querySelector("#download > ul > li:nth-child(1) > a")
    url_parts = urlparse(book['url'])
    # we need md5 and key parameters to generate a valid URL
    download_page_url = f'{url_parts.scheme}://{run_parameters["libgen_mirrors"][0]}/main/{md5}'
    soup = get_soup_from_page(download_page_url)
    if soup:
        css_path = '#download > ul > li:nth-child(1) > a'
        if selenium_driver.use_opera_vpn:
            download_click = get_book_selenium(css_path=css_path)
            if download_click:
                thread_pool.add_selenium_download(bundle_item, md5, selenium_driver.download_folder, path)
        else:
            get_link = soup.select(css_path)
            if get_link:
                download_link = f'{url_parts.scheme}://{run_parameters["libgen_mirrors"][1]}/{get_link[0]["href"]}'
                # this link doesn't have a filename
                return get_book_requests(download_link, path, filename='', extension=book['extension'], md5=md5)
    else:
        print(f'Unable to get {download_page_url}')
    return False


def get_download_link_from_libgen_rocks(run_parameters, bundle_data, bundle_item, book, md5, path):
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
    download_page_url = f'{url_parts.scheme}://{run_parameters["libgen_mirrors"][1]}/ads.php?md5={md5}'
    soup = get_soup_from_page(download_page_url)
    if soup:
        css_path = '#main td:nth-of-type(2) a'
        if selenium_driver.use_opera_vpn:
            download_click = get_book_selenium(css_path=css_path)
            if download_click:
                thread_pool.add_selenium_download(bundle_item, md5, selenium_driver.download_folder, path)
        else:
            get_link = soup.select(css_path)
            if get_link:
                download_link = f'{url_parts.scheme}://{run_parameters["libgen_mirrors"][1]}/{get_link[0]["href"]}'
                # this link doesn't have a filename
                return get_book_requests(download_link, path, filename='', extension=book['extension'], md5=md5)
    else:
        print(f'Unable to get {download_page_url}')
    return False


def get_file_from_url(run_parameters, bundle_data, bundle_item, book, md5):
    if (not run_parameters) or (not run_parameters['libgen_mirrors']) or \
            (not bundle_data) or (not book['url']) or (not md5):
        return
    path = get_output_path(run_parameters=run_parameters, bundle_name=bundle_data.get('machine_name', ''))
    selenium_driver.destination_path = path
    return get_download_link_from_cloudfare_mirror(run_parameters=run_parameters, bundle_data=bundle_data,
                                               bundle_item=bundle_item, book=book, md5=md5, path=path)
    # return get_download_link_from_libgen_rocks(run_parameters=run_parameters, bundle_data=bundle_data,
    #                                            bundle_item=bundle_item, book=book, md5=md5, path=path)
