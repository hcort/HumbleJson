""""

Al leer una página de Humble Bundle los datos de cada producto están en el siguiente nodo:

<script id="webpack-bundle-data" type="application/json">
  {"bundleVars": ...}
</script>

"""
import os

from waybackpy import Url

import json
from FilterSearchResults import filter_search_results
from LibGen import search_libgen_by_title
from LibGenDownload import get_mirror_list, get_file_from_url, get_output_path
from json import load, loads
from utils import get_soup_from_page, parse_arguments, run_parameters


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
    bundle_dict = {}
    if is_file:
        # leo el JSON desde un fichero
        with open(humble_url, "r") as content:
            bundle_dict = load(content)
    else:
        soup = get_soup_from_page(humble_url)
        if not soup:
            print('Failed to get {}'.format(humble_url))
            return bundle_dict
        # tiers no longer present in HTML code
        bundle_dict = extract_humble_dict_from_soup(soup)
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
    print('{} - {}'.format(index_str, item_in_bundle_dict_to_str(item)))
    books_found = search_libgen_by_title(item['name'])
    filtered_books = filter_search_results(item, books_found)
    print(filtered_books)
    for idx, md5 in enumerate(filtered_books):
        if not run_parameters['libgen_mirrors']:
            run_parameters['libgen_mirrors'] = get_mirror_list(filtered_books[md5]['url'])
        print('{}/{}'.format(idx+1, len(filtered_books)))
        get_file_from_url(run_parameters=run_parameters, bundle_data=bundle_data, book=filtered_books[md5], md5=md5)
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
    if not bundle_dict['tier_display_data']:
        bundle_dict['tier_order'] = ['all']
        bundle_dict['tier_display_data'] = {
            'all': {
                'tier_item_machine_names': []
            }
        }
        for item in bundle_dict['tier_item_data']:
            bundle_dict['tier_display_data']['all']['tier_item_machine_names'].append(item)
    return bundle_dict['tier_display_data']


def save_bundle_json(bundle_dict):
    path = get_output_path(run_parameters, bundle_dict['machine_name'])
    path = os.path.join(path, bundle_dict['machine_name'] + '.json')
    with open(path, 'w') as f:
        f.write(json.dumps(bundle_dict))


def print_bundle_dict(bundle_dict):
    tiers = get_tiers(bundle_dict)
    clean_upper_tiers(bundle_dict)
    for idx, tier in enumerate(reversed(bundle_dict['tier_order'])):
        tier_components = tiers[tier].get('tier_item_machine_names', [])
        print('\n\n\n\nTIER {}/{}\n\n'.format(idx+1, len(bundle_dict['tier_order'])))
        for tier_idx, name in enumerate(tier_components):
            item = bundle_dict['tier_item_data'].get(name, None)
            print_bundle_item(bundle_data=bundle_dict, item=item,
                              index_str='{}/{}'.format(tier_idx+1, len(tier_components)))
    save_bundle_json(bundle_dict)


def get_humble(humble_url, is_file=False):
    url = True
    title_tiers = None
    bundle_dict = get_bundle_dict(humble_url, is_file)
    try:
        print(bundle_dict['name'] + '\t(' + humble_url + ')')
        items_dict = build_bundle_dict(bundle_dict['tier_item_data'])
        bundle_dict['tier_item_data'] = items_dict
        return bundle_dict
    except Exception as e:
        print('Exception in get_humble: ' + str(e))
    return {}


def main():
    parse_arguments()
    for url in run_parameters['bundles']:
        print('\n\n\n\n\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\n\n\n\n')
        if run_parameters['archive']:
            try:
                # archive usign archive.org
                user_agent = "Mozilla/5.0 (Linux; Android 5.0; SM-G900P Build/LRX21T)" \
                             "AppleWebKit/537.36 (KHTML, like Gecko) " \
                             "Chrome/90.0.4430.93 Mobile Safari/537.36"  # determined the user-agent.
                wayback = Url(url, user_agent)  # created the waybackpy instance.
                archive = wayback.save()  # saved the link to the internet archive
                print(archive.archive_url)  # printed the URL.
            except Exception as e:
                print('Error saving URL to archive ' + str(e))
        print_bundle_dict(get_humble(url))
        print('\n\n\n\n\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n\n\n\n\n')


# Lanzamos la función principal
if __name__ == "__main__":
    main()
