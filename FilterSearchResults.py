"""
    filter_search_results is used to reduce the noise from the LibGen search results.

    We take all the books found using the title as the keywords and discard the ones that
    don't match enough words in the title or author fields
"""
import re


def sanitize_word(x):
    x = re.sub(r'\W+', '', x)
    if x.isdigit():
        return ''
    return x


def filter_search_results(humble_dict, libgen_dict):
    """

    :param humble_dict:
    :param libgen_dict:
    :return:

        filter criteria:
            - all words in humble title must be in libgen title
            - at least one match in author words
    """
    match_author = False
    humble_author_words = list(filter(lambda x: len(x) > 2, humble_dict['author'].lower().split()))
    humble_title_words = list(filter(lambda x: len(x) > 2, humble_dict['name'].lower().split()))
    humble_author_words = list(map(sanitize_word, humble_author_words))
    humble_title_words = list(map(sanitize_word, humble_title_words))
    filtered_dict = {}
    for libgen_item in libgen_dict:
        if libgen_dict[libgen_item]['extension'] and libgen_dict[libgen_item]['extension'] in ('epub', 'mobi', 'pdf'):
            libgen_title = list(filter(lambda x: len(x) > 2, libgen_dict[libgen_item]['title'].lower().split()))
            libgen_title = set(map(sanitize_word, libgen_title))
            title_match = True
            mismatchs = 3
            for word in humble_title_words:
                if word in libgen_title:
                    continue
                mismatchs -= 1
                if mismatchs == 0:
                    title_match = False
                    break
            # TODO sometimes humble author may be empty
            author_match = not match_author
            if match_author:
                libgen_author = list(filter(lambda x: len(x) > 2, libgen_dict[libgen_item]['author'].lower().split()))
                libgen_author = set(map(sanitize_word, libgen_author))
                # if author is empty then I don't filter
                author_match = (len(humble_author_words) == 0)
            if title_match and author_match:
                filtered_dict[libgen_item] = libgen_dict[libgen_item]
    return filtered_dict
