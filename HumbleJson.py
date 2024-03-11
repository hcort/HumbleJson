""""

    Extract Humble Bundle info from the HTML code in the page:

        <script id="webpack-bundle-data" type="application/json">
          {"bundleVars": ...}
        </script>

    Once extracted we can search for the books in LibGen and extract the download links
    Then we can download each book in the bundle

"""
import os
import sys

from waybackpy import Url

import json
from BundleInfo import BundleInfo, BundleException
from Connections import get_soup_from_page
from FilterSearchResults import filter_search_results
from LibGen import search_libgen_by_title
from LibGenDownload import get_mirror_list, get_file_from_url
from json import loads
from resources import humble_resources
from utils import parse_arguments, run_parameters, get_backup_file


def generate_author_publisher_string(list_of_names, key1, key2):
    return ','.join(map(lambda item_in_list:
                        f'{item_in_list.get(key1, "")} ({item_in_list.get(key2, "")})',
                        list_of_names))


def extract_humble_dict_from_soup(soup):
    json_node_name = 'webpack-bundle-page-data'
    bundle_vars = soup.find('script', {'id': json_node_name})
    if bundle_vars:
        whole_bundle_dict = loads(bundle_vars.string)
        return BundleInfo(whole_bundle_dict)
    else:
        raise BundleException(f'JSON info in {json_node_name} not found')


def get_bundle_dict(humble_url, is_file):
    if is_file:
        # leo el JSON desde un fichero
        return BundleInfo.from_file(humble_url)
    else:
        backup_file = get_backup_file(humble_url)
        if not os.path.isfile(backup_file):
            soup = get_soup_from_page(humble_url, use_opera_vpn=False)
            if not soup:
                raise BundleException(f'Failed to get {humble_url}')
            # tiers no longer present in HTML code
            bundle_dict = extract_humble_dict_from_soup(soup)
            bundle_dict.backup_file = backup_file
            items_dict = build_bundle_dict(bundle_dict['tier_item_data'])
            bundle_dict['tier_item_data'] = items_dict
            bundle_dict['url'] = humble_url
            bundle_dict['from_backup'] = True
            bundle_dict.save_to_file()
        else:
            return BundleInfo.from_file(backup_file)
    return bundle_dict


def build_bundle_dict(humble_items):
    items_dict = {}
    for key in humble_items:
        try:
            item = humble_items[key]
            items_dict[key] = {
                'name': item['human_name'],
                'author': item['developers'][0].get('developer-name', '') if item['developers'] else '',
                'author_url': item['developers'][0].get('developer-url', '') if item['developers'] else '',
                'publisher': item['publishers'][0].get('publisher-name', '') if item['publishers'] else '',
                'publisher_url': item['publishers'][0].get('publisher-url', '') if item['publishers'] else '',
                'description': item['description_text']
            }
        except Exception as e:
            print(f'Error en display_items: {e}', file=sys.stderr)
            pass
    return items_dict


def item_in_bundle_dict_to_str(item, print_desc=False):
    if not item:
        return '***************ITEM DOES NOT EXIST***************'
    return f"{item['name']} - {item['author']}. [{item.get('publisher', '')}]\n{item.get('description', '') if print_desc else ''}"


def search_books_to_bundle_item(bundle_dict=None, key=None, index_str=''):
    item = bundle_dict['tier_item_data'].get(key, None)
    if not item:
        return
    if item.get('downloaded', False):
        return
    print(f'{index_str} - {item_in_bundle_dict_to_str(item)}')
    try:
        if not item.get('books_found', {}):
            books_found = search_libgen_by_title(item['name'])
            filtered_books = filter_search_results(item, books_found)
            bundle_dict.set_books_found(key, dict(filtered_books))
            bundle_dict.save_to_file()
        else:
            filtered_books = dict(item['books_found'])
        print(filtered_books)
        if not item.get('books_found', {}):
            bundle_dict.set_all_books_downloaded(key)
    except Exception as err:
        print(f'Error searching book: {item["name"]} - {err}', file=sys.stderr)
    bundle_dict.save_to_file()
    print('--------------------------------------------')


def download_books_from_bundle_item(bundle_dict=None, key=None, index_str=''):
    item = bundle_dict['tier_item_data'].get(key, None)
    if not item:
        return
    if item.get('downloaded', False):
        return
    if not item.get('books_found', {}):
        return
    print(f'{index_str} - {item_in_bundle_dict_to_str(item)}')
    # start thread pool
    humble_resources.pool.bundle_dict = bundle_dict
    filtered_books = dict(item['books_found'])
    print(json.dumps(filtered_books, sort_keys=True, indent=4))
    for idx, md5 in enumerate(filtered_books):
        try:
            all_mirrors = get_mirror_list(filtered_books[md5]['url'])
            filtered_books[md5]['mirrors'] = all_mirrors
            print(f'{idx + 1}/{len(filtered_books)}')
            get_file_from_url(run_parameters=run_parameters,
                              bundle_data=bundle_dict, bundle_item=key, book=filtered_books[md5], md5=md5)
        except Exception as err:
            print(f'Error downloading {item["name"]} - {err}', file=sys.stderr)
    if not item.get('books_found', {}):
        bundle_dict.set_all_books_downloaded(key)
    bundle_dict.save_to_file()
    print('------------------------------------------------')


def clean_upper_tiers(bundle_dict):
    # bigger tiers contain smaller tiers
    # tier content: tier_1 = ['a', 'b'], tier_2 = ['a', 'b', 'c', 'd'], tier_3 = ['a', 'b', 'c', 'd', 'e', ...]
    new_tiers = {}
    reversed_tier_order = list(reversed(bundle_dict['tier_order']))
    new_tiers[reversed_tier_order[0]] = {
        'tier_item_machine_names': bundle_dict['tier_display_data'][reversed_tier_order[0]]['tier_item_machine_names']
    }
    for tier in reversed(bundle_dict['tier_order']):
        small_tier_items = bundle_dict['tier_display_data'][tier]['tier_item_machine_names']
        reversed_tier_order.pop(0)
        for other_tier in reversed_tier_order:
            if tier != other_tier:
                large_tier_list = bundle_dict['tier_display_data'][other_tier]['tier_item_machine_names']
                new_tiers[other_tier] = {
                    'tier_item_machine_names': [x for x in large_tier_list if x not in small_tier_items]
                }
    bundle_dict.set_tiers(new_tiers)


def get_tiers(bundle_dict):
    # if the bundle is not tiered i create a fake tier with all the elements in the bundle
    if not bundle_dict.get('tier_display_data', None):
        bundle_dict.create_default_tiers()
    return bundle_dict['tier_display_data']


def search_books_by_tier(bundle_dict):
    tiers = get_tiers(bundle_dict)
    for idx, tier in enumerate(reversed(bundle_dict['tier_order'])):
        tier_components = tiers[tier].get('tier_item_machine_names', [])
        print(f'\n\n\n\nTIER {idx + 1}/{len(bundle_dict["tier_order"])}\n\n')
        for tier_idx, name in enumerate(tier_components):
            search_books_to_bundle_item(bundle_dict=bundle_dict, key=name,
                                        index_str=f'{tier_idx + 1}/{len(tier_components)}')


def download_books_by_tier(bundle_dict):
    tiers = get_tiers(bundle_dict)
    for idx, tier in enumerate(reversed(bundle_dict['tier_order'])):
        tier_components = tiers[tier].get('tier_item_machine_names', [])
        print(f'\n\n\n\nTIER {idx + 1}/{len(bundle_dict["tier_order"])}\n\n')
        for tier_idx, name in enumerate(tier_components):
            download_books_from_bundle_item(bundle_dict=bundle_dict, key=name,
                                            index_str=f'{tier_idx + 1}/{len(tier_components)}')


def print_bundle_dict(bundle_dict):
    print(f'{bundle_dict.get("name", "")}\t{bundle_dict.get("url", "")}')
    clean_upper_tiers(bundle_dict)
    search_books_by_tier(bundle_dict)
    download_books_by_tier(bundle_dict)
    bundle_dict.save_to_file()


def archive_bundle(url):
    try:
        # archive using archive.org
        user_agent = 'Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T)' \
                     'AppleWebKit/537.36 (KHTML, like Gecko) ' \
                     'Chrome/90.0.4430.93 Mobile Safari/537.36'  # determined the user-agent.
        wayback = Url(url, user_agent)  # created the waybackpy instance.
        archive = wayback.save()  # saved the link to the internet archive
        print(f'Bundle {url} archived in {archive.archive_url}')  # printed the URL.
    except Exception as e:
        print(f'Error saving URL to archive {e}', file=sys.stderr)


def main():
    parse_arguments()
    json_from_file = len(run_parameters['files']) > 0
    all_data_sources = run_parameters['files'] if json_from_file else run_parameters['bundles']
    for url in all_data_sources:
        print('\n\n\n\n\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\n\n\n\n')
        if run_parameters['archive']:
            archive_bundle(url)
        print_bundle_dict(get_bundle_dict(url, is_file=json_from_file))
        print('\n\n\n\n\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\n\n\n\n')


# Lanzamos la función principal
if __name__ == '__main__':
    main()
    print('done')
