"""
    Functions to extract the download links for the books in LibGen.
    Different LibGen mirrors may have different HTML structures, so we have to build custom selectors

    The actual downloads have been moved to Connections

"""
import os
import urllib
from urllib.parse import urlparse

from bs4 import Tag

from Connections import get_soup_from_page, get_book_requests, get_book_selenium, get_book_selenium_by_url
from resources import humble_resources
from utils import run_parameters, libgen_search_libgen_rs, libgen_search_libgen_li, libgen_search_libgen_is, \
    libgen_search_libgen_rc


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
    """
        Get all the mirrors that are links to a webpage (avoid torrents, etc.)
    :param libgen_md5_url:
    :return:
    """
    mirror_list = []
    if libgen_md5_url:
        soup = get_soup_from_page(libgen_md5_url)
        if soup:
            url_part = urlparse(libgen_md5_url)
            mirror_host = f'{url_part.scheme}://{url_part.hostname}/'
            mirrors = []
            if ((mirror_host == libgen_search_libgen_rs['base_url']) or
                    (mirror_host == libgen_search_libgen_is['base_url'])):
                if libgen_md5_url.find('/fiction/') >= 0:
                    mirror_location = '.record_mirrors li a'
                else:
                    mirror_location = 'tr:nth-child(18) td a'
                mirrors = soup.select(mirror_location)
            if ((mirror_host == libgen_search_libgen_li['base_url']) or
                    (mirror_host == libgen_search_libgen_rc['base_url'])):
                mirrors = soup.select('table#tablelibgen a')

            for mirror in mirrors:
                if isinstance(mirror, Tag):
                    mirror_link = mirror.get('href', '')
                    url_parts = urlparse(mirror_link)
                    if url_parts.scheme.find('http') >= 0:
                        mirror_list.append(mirror_link)
                    if not url_parts.scheme:
                        mirror_list.append(f'{mirror_host}{mirror_link}')
    return mirror_list


def get_download_link_from_library_lol(url, run_parameters, bundle_data, bundle_item, book, md5, path):
    """
        I can also start a download from cloudflare from here
    :param run_parameters:
    :param book_url:
    :param md5:
    :param path:
    :return:
    """
    soup = get_soup_from_page(url)

    if run_parameters.get('libgen_download', '') == 'cloudflare':
        css_path = 'div#download>ul>li>a'
    else:
        css_path = 'div#download>h2>a'
    if humble_resources.driver.use_opera_vpn:
        download_click = get_book_selenium(css_path=css_path)
        if download_click:
            humble_resources.pool.add_selenium_download(bundle_item, md5,
                                                        humble_resources.driver.download_folder, path)
    else:
        get_link = soup.select_one(css_path)
        if get_link:
            download_link = get_link.get('href', '')
            filename = urllib.parse.unquote(url[url.rfind('/') + 1:])
            get_book_requests(download_link, path, filename)


def get_download_link_from_cloudfare_mirror(url, run_parameters, bundle_data, bundle_item, book, md5, path):
    if humble_resources.driver.use_opera_vpn:
        # TODO download using selenium but not by clicking
        download_click = get_book_selenium_by_url(url=url)
        if download_click:
            humble_resources.pool.add_selenium_download(bundle_item, md5, humble_resources.driver.download_folder, path)
    else:
        return get_book_requests(url, path, filename='', extension=book['extension'], md5=md5)


def get_download_link_from_libgen_rocks(url, run_parameters, bundle_data, bundle_item, book, md5, path):
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
    # url_parts = urlparse(book['url'])
    # we need md5 and key parameters to generate a valid URL
    # download_page_url = f'{url_parts.scheme}://{run_parameters["libgen_mirrors"][1]}/ads.php?md5={md5}'
    soup = get_soup_from_page(url)
    if soup:
        css_path = 'table#main td:nth-of-type(2) a'
        if humble_resources.driver.use_opera_vpn:
            download_click = get_book_selenium(css_path=css_path)
            if download_click:
                humble_resources.pool.add_selenium_download(bundle_item, md5,
                                                            humble_resources.driver.download_folder, path)
        else:
            get_link = soup.select_one(css_path)
            if get_link:
                # download_link = f'{url_parts.scheme}://{run_parameters["libgen_mirrors"][1]}/{get_link[0]["href"]}'
                # this link doesn't have a filename
                # return get_book_requests(download_link, path, filename='', extension=book['extension'], md5=md5)
                return get_book_requests(get_link['href'], path, filename='', extension=book['extension'], md5=md5)
    else:
        print(f'Unable to get {url}')
    return False


def choose_mirror(mirror_list, preferred_mirror=None):
    if preferred_mirror:
        # search mirror according to preferred download methods
        for mirror in mirror_list:
            if mirror.find(run_parameters['libgen_download']) >= 0:
                return mirror
    return mirror_list[0]


def get_file_from_url(run_parameters, bundle_data, bundle_item, book, md5):
    if (not run_parameters) or \
            (not bundle_data) or (not book['url']) or (not book['mirrors']) or (not md5):
        return

    mirror_list = book['mirrors']

    path = get_output_path(run_parameters=run_parameters, bundle_name=bundle_data.get('machine_name', ''))
    humble_resources.driver.destination_path = path

    mirror_link = choose_mirror(mirror_list, preferred_mirror=run_parameters.get('libgen_download', ''))

    if (run_parameters.get('libgen_download', '') == 'cloudflare') and (mirror_link.find('cloudflare') < 0):
        # i want to download from cloudflare but I don't have a mirror link, go to library.lol
        mirror_link = choose_mirror(mirror_list, preferred_mirror='library.lol')

    #
    #     return get_download_link_from_cloudfare_mirror(run_parameters=run_parameters, bundle_data=bundle_data,
    #                                                    bundle_item=bundle_item, book=book, md5=md5, path=path)
    # else:

    # https://libgen.rocks/ads6a49723ef4957e8e8db6dc84c5cf86f310X9VFYC
    # https://libgen.rocks/ads 6a49723ef4957e8e8db6dc84c5cf86f310X9VFYC
    if mirror_link.find('libgen.rocks') >= 0:
        return get_download_link_from_libgen_rocks(url=mirror_link,
                                                   run_parameters=run_parameters, bundle_data=bundle_data,
                                                   bundle_item=bundle_item, book=book, md5=md5, path=path)
    # https://libgen.li/ads.php?md5=6a49723ef4957e8e8db6dc84c5cf86f3
    if mirror_link.find('libgen.li') >= 0:
        # libgen.li has the same structure as libgen.rocks
        return get_download_link_from_libgen_rocks(url=mirror_link,
                                                   run_parameters=run_parameters, bundle_data=bundle_data,
                                                   bundle_item=bundle_item, book=book, md5=md5, path=path)
    if mirror_link.find('library.lol') >= 0:
        return get_download_link_from_library_lol(url=mirror_link,
                                                   run_parameters=run_parameters, bundle_data=bundle_data,
                                                   bundle_item=bundle_item, book=book, md5=md5, path=path)
    if mirror_link.find('cloudflare') >= 0:
        return get_download_link_from_cloudfare_mirror(url=mirror_link,
                                                   run_parameters=run_parameters, bundle_data=bundle_data,
                                                   bundle_item=bundle_item, book=book, md5=md5, path=path)


