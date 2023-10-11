""""

Al leer una página de Humble Bundle los datos de cada producto están en el siguiente nodo:

<script id="webpack-bundle-data" type="application/json">
  {"bundleVars": ...}
</script>

"""
import os

from waybackpy import Url

import json
from Connections import get_soup_from_page
from FilterSearchResults import filter_search_results
from LibGen import search_libgen_by_title
from LibGenDownload import get_mirror_list, get_file_from_url, get_output_path
from json import load, loads
from utils import parse_arguments, run_parameters, get_backup_file, save_to_backup_file, save_bundle_json


def generate_author_publisher_string(list_of_names, key1, key2):
    return ','.join(map(lambda item_in_list: "{key1} ({key2})".format(
        key1=item_in_list.get(key1, ''),
        key2=item_in_list.get(key2, '')), list_of_names))


def extract_humble_dict_from_soup(soup):
    json_node_name = 'webpack-bundle-page-data'
    bundle_vars = soup.find('script', {'id': json_node_name})
    if bundle_vars:
        whole_bundle_dict = loads(bundle_vars.string)
        return {
            'name': whole_bundle_dict.get('bundleData', {}).get('basic_data', {}).get('human_name', ''),
            'machine_name': whole_bundle_dict.get('bundleData', {}).get('machine_name', ''),
            'tier_item_data': whole_bundle_dict.get('bundleData', {}).get('tier_item_data', {}),
            'tier_order': whole_bundle_dict.get('bundleData', {}).get('tier_order', []),
            'tier_display_data': whole_bundle_dict.get('bundleData', {}).get('tier_display_data', {})
        }
    else:
        print('JSON info in {} not found.'.format(json_node_name))
        return {}


def get_bundle_dict(humble_url, is_file):
    if is_file:
        # leo el JSON desde un fichero
        with open(humble_url, "r") as content:
            return load(content)
    else:
        backup_file = get_backup_file(humble_url)
        if not os.path.isfile(backup_file):
            soup = get_soup_from_page(humble_url, use_opera_vpn=False)
            if not soup:
                print('Failed to get {}'.format(humble_url))
                return {}
            # tiers no longer present in HTML code
            bundle_dict = extract_humble_dict_from_soup(soup)
            items_dict = build_bundle_dict(bundle_dict['tier_item_data'])
            bundle_dict['tier_item_data'] = items_dict
            bundle_dict['url'] = humble_url
            bundle_dict['from_backup'] = True
            save_to_backup_file(backup_file, bundle_dict)
        else:
            with open(backup_file, 'r') as content:
                return load(content)
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
            print('Error en display_items: ' + str(e))
            pass
    return items_dict


def item_in_bundle_dict_to_str(item, print_desc=False):
    if not item:
        return '***************ITEM DOES NOT EXIST***************'
    return "{name} - {author}. [{pub}]\n{desc}".format(
        name=item['name'],
        author=item['author'],
        pub=item['publisher'],
        desc=item['description'] if print_desc else '')


def print_bundle_item(bundle_data=None, item=None, index_str=''):
    if not item:
        return
    if item.get('downloaded', False):
        return
    print('{} - {}'.format(index_str, item_in_bundle_dict_to_str(item)))
    try:
        if not item.get('books_found', {}):
            books_found = search_libgen_by_title(item['name'])
            filtered_books = filter_search_results(item, books_found)
            item['books_found'] = dict(filtered_books)
            save_bundle_json(bundle_data)
        else:
            filtered_books = dict(item['books_found'])
        print(filtered_books)
        for idx, md5 in enumerate(filtered_books):
            if not run_parameters['libgen_mirrors']:
                run_parameters['libgen_mirrors'] = get_mirror_list(filtered_books[md5]['url'])
            print('{}/{}'.format(idx + 1, len(filtered_books)))
            book_downloaded = get_file_from_url(run_parameters=run_parameters,
                                                   bundle_data=bundle_data, book=filtered_books[md5], md5=md5)
            if book_downloaded:
                item['books_found'].pop(md5)
                save_bundle_json(bundle_data)
        if not item.get('books_found', {}):
            item['downloaded'] = True
    except Exception as err:
        print(f'Error downloading {item["name"]} - {err}')
    save_bundle_json(bundle_data)
    print('------------------------------------------------')


def clean_upper_tiers(bundle_dict):
    # bigger tiers contain smaller tiers
    # tier content: tier_1 = ['a', 'b'], tier_2 = ['a', 'b', 'c', 'd'], tier_3 = ['a', 'b', 'c', 'd', 'e', ...]
    for tier in reversed(bundle_dict['tier_order']):
        small_tier_items = bundle_dict['tier_display_data'][tier]['tier_item_machine_names']
        for other_tier in bundle_dict['tier_display_data']:
            if tier != other_tier:
                large_tier_list = bundle_dict['tier_display_data'][other_tier]['tier_item_machine_names']
                bundle_dict['tier_display_data'][other_tier]['tier_item_machine_names'] = list(
                    filter(lambda x: x not in small_tier_items, large_tier_list))


def get_tiers(bundle_dict):
    # if the bundle is not tiered i create a fake tier with all the elements in the bundle
    if not bundle_dict.get('tier_display_data', None):
        bundle_dict['tier_order'] = ['all']
        bundle_dict['tier_display_data'] = {
            'all': {
                'tier_item_machine_names': []
            }
        }
        for item in bundle_dict['tier_item_data']:
            bundle_dict['tier_display_data']['all']['tier_item_machine_names'].append(item)
    return bundle_dict['tier_display_data']


def print_bundle_dict(bundle_dict):
    print(f'{bundle_dict.get("name", "")}\t{bundle_dict.get("url", "")}')
    tiers = get_tiers(bundle_dict)
    clean_upper_tiers(bundle_dict)
    for idx, tier in enumerate(reversed(bundle_dict['tier_order'])):
        tier_components = tiers[tier].get('tier_item_machine_names', [])
        print('\n\n\n\nTIER {}/{}\n\n'.format(idx + 1, len(bundle_dict['tier_order'])))
        for tier_idx, name in enumerate(tier_components):
            item = bundle_dict['tier_item_data'].get(name, None)
            print_bundle_item(bundle_data=bundle_dict, item=item,
                              index_str='{}/{}'.format(tier_idx + 1, len(tier_components)))
    save_bundle_json(bundle_dict)


def get_humble(humble_url, is_file=False):
    bundle_dict = get_bundle_dict(humble_url, is_file)
    return bundle_dict


def archive_bundle(url):
    try:
        # archive using archive.org
        user_agent = "Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T)" \
                     "AppleWebKit/537.36 (KHTML, like Gecko) " \
                     "Chrome/90.0.4430.93 Mobile Safari/537.36"  # determined the user-agent.
        wayback = Url(url, user_agent)  # created the waybackpy instance.
        archive = wayback.save()  # saved the link to the internet archive
        print(f'Bundle {url} archived in {archive.archive_url}')  # printed the URL.
    except Exception as e:
        print('Error saving URL to archive ' + str(e))


def main():
    parse_arguments()
    json_from_file = run_parameters['files'] != []
    all_data_sources = run_parameters['files'] if json_from_file else run_parameters['bundles']
    for url in all_data_sources:
        print('\n\n\n\n\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\n\n\n\n')
        if run_parameters['archive']:
            archive_bundle(url)
        print_bundle_dict(get_humble(url, is_file=json_from_file))
        print('\n\n\n\n\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\n\n\n\n')


# Lanzamos la función principal
if __name__ == "__main__":
    main()
