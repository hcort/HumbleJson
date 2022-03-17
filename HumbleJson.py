""""

Al leer una página de Humble Bundle los datos de cada producto están en el siguiente nodo:

<script id="webpack-bundle-data" type="application/json">
  {"bundleVars": ...}
</script>

"""
import getopt
import sys

from FilterSearchResults import filter_search_results
from LibGen import search_libgen_by_title, base_url
from LibGenDownload import get_mirror_list, get_file_from_url
from json import load, loads
from sys import argv
from requests import Session, codes
from bs4 import BeautifulSoup
from waybackpy import Url


# https://www.humblebundle.com/books/diy-maker-school-make-co-books
# https://www.humblebundle.com/books/fall-for-crafting-open-road-media-books
# https://www.humblebundle.com/books/raspberry-pi-press-gaming-books
# https://www.humblebundle.com/books/learn-to-code-the-fun-way-no-starch-press-books
# https://www.humblebundle.com/books/start-something-new-chronicle-books
# https://www.humblebundle.com/books/home-sweet-home-quarto-books
# https://www.humblebundle.com/books/multilanguage-tales-warhammer-2021-black-library-books
# https://www.humblebundle.com/books/make-your-own-magic-inventions-make-co-books
# https://www.humblebundle.com/humble-heal-covid-19-bundle
# https://www.humblebundle.com/books/grilling-and-gardening-quarto-books
# https://www.humblebundle.com/books/learn-you-more-python-books
# https://www.humblebundle.com/books/life-hacks-adams-books
# https://www.humblebundle.com/books/creative-cooking-open-road-media-books

run_parameters = {
    'bundles': [],
    'libgen_base': base_url,
    'libgen_mirrors': [],
    'output_dir': '',
    'archive': False
}


def generate_author_publisher_string(list_of_names, key1, key2):
    return ','.join(map(lambda item_in_list: "{key1} ({key2})".format(
        key1=item_in_list.get(key1, ''),
        key2=item_in_list.get(key2, '')), list_of_names))


def get_bundle_dict(humble_url, is_file):
    bundle_dict = {}
    if is_file:
        # leo el JSON desde un fichero
        with open(humble_url, "r") as content:
            bundle_dict = load(content)
    else:
        session = Session()
        current_page = session.get(humble_url)
        if current_page.status_code != codes.ok:
            print('Failed to get {}'.format(humble_url))
            exit(-1)
        soup = BeautifulSoup(current_page.text, features="html.parser")
        if not soup:
            print('Failed to get {}'.format(humble_url))
            return bundle_dict
        # tiers no longer present in HTML code
        # title_tiers = order_humble_items(soup)
        json_node_name = 'webpack-bundle-page-data'
        bundle_vars = soup.find('script', {'id': json_node_name})
        if bundle_vars:
            whole_bundle_dict = loads(bundle_vars.string)
            bundle_dict = {
                'name': whole_bundle_dict.get('bundleData', {}).get('basic_data', {}).get('human_name', ''),
                'machine_name': whole_bundle_dict.get('bundleData', {}).get('machine_name', ''),
                'tier_item_data': whole_bundle_dict.get('bundleData', {}).get('tier_item_data', {}),
                'tier_order': whole_bundle_dict.get('bundleData', {}).get('tier_order', []),
                'tier_display_data': whole_bundle_dict.get('bundleData', {}).get('tier_display_data', {})
            }
        else:
            print('JSON info in {} not found.'.format(json_node_name))
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


def print_bundle_item(bundle_data=None, item=None):
    if not item:
        return
    print(item_in_bundle_dict_to_str(item))
    books_found = search_libgen_by_title(item['name'])
    filtered_books = filter_search_results(item, books_found)
    print(filtered_books)
    for md5 in filtered_books:
        if not run_parameters['libgen_mirrors']:
            run_parameters['libgen_mirrors'] = get_mirror_list(filtered_books[md5]['url'])
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


def print_bundle_dict(bundle_dict):
    tiers = get_tiers(bundle_dict)
    clean_upper_tiers(bundle_dict)
    for idx, tier in enumerate(reversed(bundle_dict['tier_order'])):
        tier_components = tiers[tier].get('tier_item_machine_names', [])
        print('\n\n\n\nTIER ' + str(idx) + '\n\n')
        for name in tier_components:
            item = bundle_dict['tier_item_data'].get(name, None)
            print_bundle_item(bundle_data=bundle_dict, item=item)


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


def parse_arguments():
    argumentList = sys.argv[1:]
    options = "hu:ao:l:"
    long_options = ["help", "urls=", "archive",  "out=", "libgen="]
    try:
        arguments, values = getopt.getopt(argumentList, options, long_options)
        for currentArgument, currentValue in arguments:
            if currentArgument in ('-h', long_options[0]):
                print("Displaying Help")
            elif currentArgument in ('-u', long_options[1]):
                url = currentValue
                url_list = url.split(',')
                run_parameters['bundles'] = url_list
            elif currentArgument in ('-a', long_options[2]):
                run_parameters['archive'] = True
            elif currentArgument in ('-o', long_options[3]):
                run_parameters['output_dir'] = currentValue
            elif currentArgument in ('-l', long_options[4]):
                run_parameters['libgen_base'] = currentValue
    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))


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
