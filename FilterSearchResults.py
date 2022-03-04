def filter_search_results(humble_dict, libgen_dict):
    """

    :param humble_dict:
    :param libgen_dict:
    :return:

        filter criteria:
            - all words in humble title must be in libgen title
            - at least one match in author words
    """
    humble_author_words = list(filter(lambda x: len(x) > 2, humble_dict['author'].lower().split()))
    humble_title_words = list(filter(lambda x: len(x) > 2, humble_dict['name'].lower().split()))
    filtered_dict = {}
    for libgen_item in libgen_dict:
        libgen_title = libgen_dict[libgen_item]['title'].lower()
        title_match = True
        for word in humble_title_words:
            title_match &= (libgen_title.find(word) >= 0)
        # TODO sometimes humble author may be empty
        libgen_author = libgen_dict[libgen_item]['author'].lower()
        author_match = False
        for word in humble_author_words:
            author_match |= (libgen_author.find(word) >= 0)
        if title_match and author_match:
            filtered_dict[libgen_item] = libgen_dict[libgen_item]
    return filtered_dict
