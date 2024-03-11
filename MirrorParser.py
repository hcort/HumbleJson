"""
    Each libgen mirror is subtly different from the others in the way the
    pages are built and where each piece of data is stored
"""
import re
from urllib.parse import quote

from Connections import get_soup_from_page
from utils import run_parameters, libgen_search_libgen_rs, update_run_parameters, libgen_search_libgen_is, \
    libgen_search_libgen_li, build_url, libgen_search_libgen_rc


class LibgenIterator:
    """
        Iterates through a series of result pages
    """

    def __init__(self, last_page, url_pattern):
        self.__current_page = 1
        self.__url_pattern = url_pattern
        self.__last_page = last_page

    def __iter__(self):
        return self

    def __next__(self):
        if self.__current_page <= self.__last_page:
            item = f'{self.__url_pattern}&page={self.__current_page}'
            self.__current_page += 1
            return item
        else:
            raise StopIteration


def get_paginator_last_page(soup):
    last_page = 0
    # search for paginator script, if not found there are no results
    try:
        all_scripts = soup.select('script')
        for script in all_scripts:
            if (script.get('src', '').find('paginator') >= 0) or (script.text.find('paginator') >= 0):
                # "paginator_example_top", last_page, items_per_page, current_page
                m = re.search('\s+([0-9]+), //', script.text)
                if m:
                    last_page = int(m.group(1))
                    break
                else:
                    last_page = 1
    except Exception as err:
        print(err)
    return last_page


def get_paginator_last_page_one_line(soup):
    last_page = 0
    # search for paginator script, if not found there are no results
    try:
        all_scripts = soup.select('script')
        for script in all_scripts:
            if (script.get('src', '').find('paginator') >= 0) or (script.text.find('paginator') >= 0):
                m = re.search('"paginator_example_top", ([0-9]+)', script.text)
                if m:
                    last_page = int(m.group(1))
                    break
                else:
                    last_page = 1
    except Exception as err:
        print(err)
    return last_page


class LibGenParser:
    """
        Generic virtual class
    """

    def get_list_results_pages(self, soup, base_url):
        raise NotImplementedError

    def get_list_results_pages_fiction(self, soup, base_url):
        raise NotImplementedError

    def get_non_fiction(self, soup):
        raise NotImplementedError

    def get_fiction(self, soup):
        raise NotImplementedError

    def search_fiction_link(self, soup):
        raise NotImplementedError

    def get_fiction_link(self):
        raise NotImplementedError

    def restart_iterator(self):
        raise NotImplementedError


class LibGenParserRs(LibGenParser):
    """
        Parser for libgen.rs mirrors

        It also works for libgen.is
    """
    items_found_selector = 'body table:nth-of-type(2) td:nth-child(1) font'
    authors_selector = 'table:nth-of-type(3) tr:not(:first-child) td:nth-of-type(2)'
    titles_selector = 'table:nth-of-type(3) tr:not(:first-child) td:nth-of-type(3)'
    publisher_selector = 'table:nth-of-type(3) tr:not(:first-child) td:nth-of-type(4)'
    extension_selector = 'table:nth-of-type(3) tr:not(:first-child) td:nth-of-type(9)'
    regex_md5 = re.compile('md5=([A-F0-9]+)')

    authors_fiction_selector = 'table.catalog ul.catalog_authors'
    titles_fiction_selector = 'table.catalog tbody td:nth-of-type(3) a'
    extension_fiction_selector = 'table.catalog tbody td:nth-of-type(5)'
    regex_md5_fiction = re.compile('/fiction/([A-F0-9]+)')

    def __init__(self):
        self.__paginator = None
        self.__fiction_link = None

    def restart_iterator(self):
        self.__paginator = None

    def get_list_results_pages(self, soup, base_url):
        if not self.__paginator:
            self.__paginator = LibgenIterator(get_paginator_last_page(soup), base_url)
        return self.__paginator

    def get_list_results_pages_fiction(self, soup, base_url):
        if not self.__paginator:
            num = 1
            try:
                page_selector = soup.select_one('div.catalog_paginator select.page_selector')
                if page_selector:
                    num_last_page = re.search(r'\s*([0-9]+)', page_selector.text.split('/')[-1])
                    num = int(num_last_page.group(1))
            except Exception as err:
                print(err)
            self.__paginator = LibgenIterator(num, base_url)
        return self.__paginator

    def get_non_fiction(self, soup):
        all_authors = soup.select(self.authors_selector)
        all_titles = soup.select(self.titles_selector)
        all_publishers = soup.select(self.publisher_selector)
        all_extensions = soup.select(self.extension_selector)
        books_found = {}
        for a, t, p, e in zip(all_authors, all_titles, all_publishers, all_extensions):
            # in some results we have some data we don't want to parse, so I get rid of it
            links_in_title = t.select('a')
            link_to_book = None
            for l in links_in_title:
                if l.get('id', None):
                    link_to_book = l
                    fonts = link_to_book.select('font')
                    for f in fonts:
                        f.extract()
                    break
            if not link_to_book:
                continue
            book_url = link_to_book['href']
            book_id = self.regex_md5.search(book_url)
            if book_id:
                books_found[book_id.group(1)] = {
                    'title': t.text,
                    'author': a.text,
                    'publisher': p.text,
                    'extension': e.text.lower(),
                    'url': build_url(run_parameters['libgen_base'], book_url)
                }
            else:
                print(f'!!!!!!!!!!!! {book_url} - {t.text} - {a.text} - {p.text}')
        return books_found

    def get_fiction(self, soup):
        all_authors = soup.select(self.authors_fiction_selector)
        all_titles = soup.select(self.titles_fiction_selector)
        all_extensions = soup.select(self.extension_fiction_selector)
        books_found = {}
        for a, t, e in zip(all_authors, all_titles, all_extensions):
            book_url = t['href']
            book_id = self.regex_md5_fiction.search(book_url)
            if book_id:
                books_found[book_id.group(1)] = {
                    'title': t.text,
                    'author': a.text,
                    'publisher': '',
                    'extension': e.text.split('/')[0].strip().lower(),
                    'url': build_url(run_parameters['libgen_base'], book_url)
                }
            else:
                print(f'!!!!!!!!!!!! {book_url} - {t.text} - {a.text}')
        return books_found

    def search_fiction_link(self, soup):
        fiction = soup.select_one('body>table:nth-of-type(2) td:nth-of-type(3) a')
        if fiction:
            self.__fiction_link = fiction['href']

    def get_fiction_link(self):
        return self.__fiction_link


class LibGenParserLi(LibGenParser):
    """
        In this mirror the non-fiction and fiction results appear on the same search

        All the fiction-related methods do nothing
    """
    authors_selector = 'table#tablelibgen tbody td:nth-of-type(2)'
    titles_selector = 'table#tablelibgen tbody td:nth-of-type(1)>a:nth-of-type(1)'
    publisher_selector = 'table#tablelibgen tbody td:nth-of-type(3)'
    extension_selector = 'table#tablelibgen tbody td:nth-of-type(8)'
    link_selector = 'table#tablelibgen tbody td:nth-of-type(9) a:nth-of-type(1)'
    regex_id = re.compile('id=([A-F0-9]+)')

    def __init__(self):
        self.__paginator = None

    def restart_iterator(self):
        self.__paginator = None

    def get_list_results_pages(self, soup, base_url):
        if not self.__paginator:
            self.__paginator = LibgenIterator(get_paginator_last_page_one_line(soup), base_url)
        return self.__paginator

    def get_list_results_pages_fiction(self, soup, base_url):
        if not self.__paginator:
            self.__paginator = LibgenIterator(0, base_url)
        return self.__paginator

    def get_non_fiction(self, soup):
        all_authors = soup.select(self.authors_selector)
        all_titles = soup.select(self.titles_selector)
        all_publishers = soup.select(self.publisher_selector)
        all_extensions = soup.select(self.extension_selector)
        # all_links = soup.select(self.link_selector)
        books_found = {}
        for a, t, p, e in zip(all_authors, all_titles, all_publishers, all_extensions):
            book_url = t['href']
            book_id_m = self.regex_id.search(book_url)
            if book_id_m:
                book_id = book_id_m.group(1)
                books_found[book_id] = {
                    'title': t.text,
                    'author': a.text,
                    'publisher': p.text,
                    'extension': e.text.lower(),
                    'url': build_url(run_parameters['libgen_base'], book_url)
                }
            else:
                print(f'!!!!!!!!!!!! {book_url} - {t.text} - {a.text} - {p.text}')
        return books_found

    def get_fiction(self, soup):
        return {}

    def search_fiction_link(self, soup):
        pass

    def get_fiction_link(self):
        return None


def select_parser():
    if run_parameters['libgen_base'] == libgen_search_libgen_rs['base_url']:
        return LibGenParserRs()
    if run_parameters['libgen_base'] == libgen_search_libgen_is['base_url']:
        return LibGenParserRs()
    if run_parameters['libgen_base'] == libgen_search_libgen_li['base_url']:
        return LibGenParserLi()
    if run_parameters['libgen_base'] == libgen_search_libgen_rc['base_url']:
        return LibGenParserLi()
    return None
