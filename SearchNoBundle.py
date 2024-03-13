"""

    This is used to search without using a Humble Bundle json

"""
import datetime
import json
import os.path

from slugify import slugify

from BundleInfo import BundleInfo
from FilterSearchResults import filter_search_results
from HumbleJson import iterate_tiers, search_books_to_bundle_item, \
    download_books_from_bundle_item
from LibGen import search_libgen_by_title
from utils import run_parameters


def create_bundle_dict_mockup():
    time_str = datetime.datetime.now().strftime('%Y%m%d_%H%M')
    bundle_name = f'Not a bundle - {time_str}'
    return {
        'name': bundle_name,
        'machine_name': slugify(bundle_name),
        'tier_item_data': {},
        'tier_order': ['all'],
        'tier_display_data': {
            'all': {
                'tier_item_machine_names': []
            }
        },
        'from_backup': False
    }


def search_without_bundle(search_items):
    bundle_mockup = create_bundle_dict_mockup()
    for search in search_items:
        item_machine_name = slugify(f'{search["title"]}_{search["author"]}')
        bundle_mockup['tier_display_data']['all']['tier_item_machine_names'].append(item_machine_name)
    # save to file so it can be reprocessed another time
    backup_file = os.path.join(run_parameters['output_dir'], f'{bundle_mockup["machine_name"]}.json')
    print(f'search results saved to {backup_file}')
    with open(backup_file, 'w', encoding='utf-8') as file:
        json.dump(bundle_mockup, file)
    # we recover the file into a BundleInfo object
    bundle_object = BundleInfo.from_file(backup_file)
    iterate_tiers(bundle_object, functor=search_books_to_bundle_item)
    iterate_tiers(bundle_object, functor=download_books_from_bundle_item)
    bundle_object.save_to_file()


def search_in_libgen(title, author):
    item = {
        'name': title,
        'author': author
    }
    books_found = search_libgen_by_title(item['name'])
    filtered_books = filter_search_results(item, books_found)
    item['books_found'] = filtered_books
    return item


# Lanzamos la función principal
if __name__ == '__main__':
    run_parameters['output_dir'] = r'F:\bkp\libros\bundles'
    list_of_searches = [
        {'title': 'consider the lobster', 'author': 'Foster Wallace'}
    ]
    search_without_bundle(search_items=list_of_searches)
