import re
from functools import reduce
from urllib.parse import urlencode, quote

import requests
from bs4 import BeautifulSoup, Tag

base_url = "http://libgen.rs/"

titles_location_detailed_view = 'td:nth-child(3) b a'
authors_location_detailed_view = 'tr:nth-child(3) td+ td'
publisher_location_detailed_view = "tr:nth-child(5) td:nth-child(2)"
ids_location_detailed_view = 'tr:nth-child(8) td:last-child'

titles_location_fiction = 'table.catalog td:nth-of-type(3) a'
# TODO if more than one author they appear as a list
# authors_location_fiction = '.catalog_authors li a'
authors_location_fiction = '.catalog_authors'

items_found_selector = "body table:nth-of-type(2) td:nth-child(1) font"
items_found_selector_fiction = ".catalog_paginator div:first-child"
goto_fiction_selector = "body table:nth-of-type(2) td:nth-child(3) font a"
last_page_selector = '#paginator_example_top td span a'


def append_author_string(x, y):
    authors_str = x if type(x) is str else ''
    if type(x) is Tag:
        authors_str = '{0}; {1}'.format(authors_str, x.text) if authors_str != '' else x.text
    if type(y) is Tag:
        authors_str = '{0}; {1}'.format(authors_str, y.text) if authors_str != '' else y.text
    return authors_str


def build_url(libgen_url, title):
    if libgen_url[-1] == '/' and title[0] == '/':
        return libgen_url[:-1] + title
    else:
        return libgen_url + title


def expand_tuple_into_dict(title, author, publisher=None, is_fiction=True):
    if is_fiction:
        return {
            'title': title.text,
            'author': reduce(append_author_string, author.contents),
            'publisher': '',
            'url': build_url(base_url, title.get('href'))
        }
    else:
        return {
            'title': title.text,
            'author': author.text,
            'publisher': publisher.text if publisher else '',
            'url': title.get('href', '').replace('../', base_url, 1)
        }


def zip_tuple_to_dict(iterable, is_fiction=True):
    return expand_tuple_into_dict(*iterable, is_fiction)


def get_search_in_fiction_link(soup):
    goto_fiction_link = soup.select_one(goto_fiction_selector)
    if not goto_fiction_link:
        return ''
    return base_url + goto_fiction_link['href']


def generate_url_list(start_url, page_number):
    pending_pages = []
    if page_number > 1:
        for i in range(2, page_number + 1):
            pending_pages.append(start_url + "&page=" + str(i))
    return pending_pages


def get_page_count(soup, start_url, is_fiction=False):
    """
    #paginator_example_top is built in javascript
    This won't work
    > all_pages = soup.select_one('#paginator_example_top td span a')
    """
    pending_pages = []
    page_number = 0
    if is_fiction:
        last_page_link = soup.select('.catalog_paginator .page_selector')
    else:
        last_page_link = soup.select('body script:nth-of-type(1)')
    if not last_page_link:
        return pending_pages
    if is_fiction:
        num_last_page = re.match('page 1\s*/\s*([0-9]+)', last_page_link[0].text)
        next_page_link = soup.select('.catalog_paginator a')
        next_page_url = base_url[:-1] + re.sub('&page=([0-9]+)', '', next_page_link[0]['href'])
    else:
        lines_split = re.split('\r\n', last_page_link[0].string)
        num_last_page = re.match('\s+([0-9]+),', lines_split[3])
        next_page_url = start_url
    if num_last_page:
        page_number = int(num_last_page.group(1))
    return generate_url_list(next_page_url, page_number)


def get_found_items(soup, is_fiction=False):
    if is_fiction:
        items_found = soup.select_one(items_found_selector_fiction)
    else:
        items_found = soup.select_one(items_found_selector)
    if not items_found:
        return 0
    num_items = re.search('([0-9]+) files found', items_found.text)
    if not num_items:
        return 0
    return num_items.group(1)


def get_soup_from_page(current_url):
    req = requests.get(current_url)
    if req.status_code != requests.codes.ok:
        return None
    response = req.content
    soup = BeautifulSoup(response, 'html.parser', from_encoding='utf-8')
    return soup


def extract_md5_from_title(title, is_fiction=False):
    title_url = title.get('href', '')
    if not title_url:
        return ''
    if is_fiction:
        md5 = re.search('/fiction/([0-9A-F]+)', title_url)
    else:
        md5 = re.search('md5=([0-9A-F]+)', title_url)
    if not md5:
        return ''
    return md5.group(1)


def search_libgen(url, is_fiction=False):
    all_books = {}
    page_number = 1
    url_with_page = url + "&page=" + str(page_number)
    soup = get_soup_from_page(url_with_page)
    if not soup:
        return all_books
    num_items = get_found_items(soup, is_fiction)
    if not is_fiction:
        search_fiction_link = get_search_in_fiction_link(soup)
        fiction_dict = search_libgen(search_fiction_link, is_fiction=True)
        all_books.update(fiction_dict)
    if num_items != '0':
        pending_pages = [url_with_page] + get_page_count(soup, url, is_fiction)
        while pending_pages:
            current_url = pending_pages.pop(0)
            # print('--------------------' + current_url + '---------------------')
            if not soup:
                soup = get_soup_from_page(current_url)
            if not soup:
                return all_books
            if is_fiction:
                title_list = soup.select(titles_location_fiction)
                author_list = soup.select(authors_location_fiction)
                # no publishers or ids
                zipped = zip(title_list, author_list)
            else:
                title_list = soup.select(titles_location_detailed_view)
                author_list = soup.select(authors_location_detailed_view)
                publisher_list = soup.select(publisher_location_detailed_view)
                zipped = zip(title_list, author_list, publisher_list)
            new_dict = {extract_md5_from_title(z[0], is_fiction): zip_tuple_to_dict(z, is_fiction) for z in zipped}
            all_books.update(new_dict)
            soup = None
    return all_books


def search_libgen_by_title(title):
    page = '1'
    items_per_page = 100
    # query can be 'title', 'author', 'publisher'
    query = 'title'
    # language=English
    # format=mobi, format=epub
    urlencoded_query = quote(query.encode('utf-8'))
    searchUrl = base_url + "/search.php?&req=" + title + "&res=" + str(items_per_page) + \
                '&column=' + urlencoded_query + "&phrase=1&view=detailed"
    return search_libgen(searchUrl)
