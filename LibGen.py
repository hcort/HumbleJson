"""
    Search in Library Genesis

    The only search parameter used is the title of the book

    search_libgen_by_title returns a dictionary with all the search results

    key: the MD5 that identifies the book in libgen
    value: {
                'title': ...
                'author': ...
                'publisher': ...
                'extension': ...
                'url': ...
            }
    The "url" field in the value is the page where we can get the download link of the file

"""
from urllib.parse import quote

from Connections import get_soup_from_page
from MirrorParser import select_parser
from utils import run_parameters, update_run_parameters, libgen_search_libgen_li


def get_books_no_fiction(parser, search_parameter):
    items_per_page = 100
    # query can be 'title', 'author', 'publisher'
    query = 'title'
    urlencoded_query = quote(search_parameter.encode('utf-8'))
    # search_url = run_parameters['libgen_base'] + run_parameters['libgen_search_path'] +
    # ?&req=' + urlencoded_query + '&res=' + \
    #              str(items_per_page) + '&column=' + query + '&phrase=1&view=detailed'
    # &topics%5B%5D=l&topics%5B%5D=f > useful in libgen.li
    # detailed_view = 'view=detailed&'
    detailed_view = ''
    search_url = f'{run_parameters["libgen_base"]}{run_parameters["libgen_search_path"]}?&req={urlencoded_query}&' \
                 f'res={items_per_page}&column={query}&phrase=1&{detailed_view}topics%5B%5D=l&topics%5B%5D=f'

    search_url = parser.build_search_url(urlencoded_query, items_per_page, query, detailed_view)
    all_books = {}
    page_number = 1
    url_with_page = f'{search_url}&page={page_number}'
    soup = get_soup_from_page(url_with_page)
    all_books = {}
    for page in parser.get_list_results_pages(soup, search_url):
        print(page)
        current_url = page
        soup = get_soup_from_page(current_url)
        if not soup:
            print(f'Unable to connecto to LibGen {url_with_page}')
            continue
        books = parser.get_non_fiction(soup)
        all_books.update(books)
    # prepare the parser for the fiction loop
    parser.search_fiction_link(soup)
    parser.restart_iterator()
    return all_books


def get_books_fiction(parser):
    all_books = {}
    fiction_link = parser.get_fiction_link()
    if not fiction_link:
        return all_books
    search_url = f'{run_parameters["libgen_base"]}{fiction_link}'
    page_number = 1
    url_with_page = f'{search_url}&page={page_number}'
    soup = get_soup_from_page(url_with_page)
    for page in parser.get_list_results_pages_fiction(soup, search_url):
        print(page)
        current_url = page
        soup = get_soup_from_page(current_url)
        if not soup:
            print(f'Unable to connect to to LibGen {url_with_page}')
            continue
        books = parser.get_fiction(soup)
        all_books.update(books)
    return all_books


def get_all_books(title):
    parser = select_parser()
    all_books = get_books_no_fiction(parser, title)
    all_books.update(get_books_fiction(parser))
    return all_books


def search_libgen_by_title(title):
    if not run_parameters:
        return {}
    return get_all_books(title)
