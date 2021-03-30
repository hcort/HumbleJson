""""

Al leer una página de Humble Bundle los datos de cada producto están en el siguiente nodo:

<script id="webpack-bundle-data" type="application/json">
  {"bundleVars": ...}
</script>

"""
import json

import requests
from bs4 import BeautifulSoup


# https://www.humblebundle.com/books/diy-maker-school-make-co-books
# https://www.humblebundle.com/books/fall-for-crafting-open-road-media-books
# https://www.humblebundle.com/books/raspberry-pi-press-gaming-books
# https://www.humblebundle.com/books/learn-to-code-the-fun-way-no-starch-press-books
# https://www.humblebundle.com/books/start-something-new-chronicle-books
# https://www.humblebundle.com/books/home-sweet-home-quarto-books
# https://www.humblebundle.com/books/multilanguage-tales-warhammer-2021-black-library-books
# https://www.humblebundle.com/books/make-your-own-magic-inventions-make-co-books


def order_humble_items(soup):
    # div class="main-content-row dd-game-row js-nav-row"
    # div class="dd-image-box-list js-slideout-items-row"
    # <div class="dd-image-box-figure u-lazy-load s-loaded" data-slideout="...">
    # titles = [[], [], []]
    layer_divs = soup.find_all("div", class_="main-content-row dd-game-row js-nav-row", recursive=True)
    # titles = [[]] * len(layer_divs) # esto hace que todos los elementos de la lista sean "punteros" a la misma lista
    titles = [[] for _ in range(len(layer_divs))]
    for idx, layer in enumerate(layer_divs):
        inner_divs = layer.find_all('div', class_="dd-image-box-figure u-lazy-load", recursive=True)
        for inner_div in inner_divs:
            item_name = inner_div['data-slideout']
            titles[idx].append(item_name)
    return titles


def generate_author_publisher_string(list_of_names, key1, key2):
    return ','.join(map(lambda item_in_list: "{key1} ({key2})".format(
        key1=item_in_list.get(key1, ''),
        key2=item_in_list.get(key2, '')), list_of_names))


def get_bundle_dict(humble_url, is_file):
    if is_file:
        # leo el JSON desde un fichero
        with open(humble_url, "r") as content:
            bundle_dict = json.load(content)
    else:
        session = requests.Session()
        current_page = session.get(humble_url)
        if current_page.status_code != requests.codes.ok:
            exit(-1)
        soup = BeautifulSoup(current_page.text, features="html.parser")
        title_tiers = order_humble_items(soup)
        bundle_vars = soup.find('script', {'id': 'webpack-bundle-data'})
        bundle_dict = json.loads(bundle_vars.string)
        bundle_dict['title_tiers'] = title_tiers
    return bundle_dict


def build_bundle_dict(humble_items):
    items_dict = {}
    for item in humble_items:
        try:
            items_dict[item['machine_name']] = {
                'name': item['human_name'],
                'author': generate_author_publisher_string(item['developers'], 'developer_name', 'developer_url'),
                'publisher': generate_author_publisher_string(item['publishers'], 'publisher_name',
                                                              'publisher_url'),
                'description': item['description_text']
            }
        except Exception as e:
            # print('Error en display_items: ' + str(e))
            pass
    return items_dict


def item_in_bundle_dict_to_str(item):
    return "{name} - {author}. [{pub}]\n{desc}".format(
        name=item['name'],
        author=item['author'],
        pub=item['publisher'],
        desc=item['description'])


def print_bundle_dict(bundle_dict):
    title_tiers = bundle_dict['title_tiers']
    if title_tiers:
        for idx, tier in enumerate(title_tiers):
            print('\n\n\n\nTIER ' + str(idx) + '\n\n')
            for name in tier:
                item = bundle_dict[name]
                print(item_in_bundle_dict_to_str(item))
                print('------------------------------------------------')
    else:
        for item in bundle_dict.values():
            print(item_in_bundle_dict_to_str(item))
            print('------------------------------------------------')


def get_humble(humble_url, is_file=False):
    url = True
    title_tiers = None
    bundle_dict = get_bundle_dict(humble_url, is_file)
    try:
        humble_name = bundle_dict['bundleVars']['product_human_name']
        humble_items = bundle_dict['bundleVars']['slideout_data']['display_items']
        print(humble_name + '\t(' + humble_url + ')')
        items_dict = build_bundle_dict(humble_items.values())
        print_bundle_dict(items_dict)
    except Exception as e:
        print(str(e))


def main():
    list_of_urls = [
        'https://www.humblebundle.com/books/stuff-that-kids-love-adams-media-books',
        'https://www.humblebundle.com/books/lets-cook-together-books',
        'https://www.humblebundle.com/books/learn-you-more-code-no-starch-press-books'
    ]
    for url in list_of_urls:
        get_humble(url)


# Lanzamos la función principal
if __name__ == "__main__":
    main()
