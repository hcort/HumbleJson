""""

Al leer una página de Humble Bundle los datos de cada producto están en el siguiente nodo:

<script id="webpack-bundle-data" type="application/json">
  {"bundleVars": ...}
</script>

"""
import json

import requests
from bs4 import BeautifulSoup


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


def main():
    # https://www.humblebundle.com/books/diy-maker-school-make-co-books
    # https://www.humblebundle.com/books/fall-for-crafting-open-road-media-books
    # https://www.humblebundle.com/books/raspberry-pi-press-gaming-books
    # https://www.humblebundle.com/books/learn-to-code-the-fun-way-no-starch-press-books
    # https://www.humblebundle.com/books/start-something-new-chronicle-books
    # https://www.humblebundle.com/books/home-sweet-home-quarto-books
    url = True
    title_tiers = None
    if url:
        current_url = "https://www.humblebundle.com/books/home-sweet-home-quarto-books"
        session = requests.Session()
        current_page = session.get(current_url)
        if current_page.status_code != requests.codes.ok:
            exit(-1)
        soup = BeautifulSoup(current_page.text, features="html.parser")
        title_tiers = order_humble_items(soup)
        bundle_vars = soup.find('script', {'id': 'webpack-bundle-data'})
        bundle_dict = json.loads(bundle_vars.string)
    else:
        # leo el JSON desde un fichero
        current_url = 'json/raspberry.txt'
        with open(current_url, "r") as content:
            bundle_dict = json.load(content)
    try:
        humble_name = bundle_dict['bundleVars']['product_human_name']
        humble_items = bundle_dict['bundleVars']['slideout_data']['display_items']
        print(humble_name + '\t(' + current_url + ')')
        items_dict = {}
        for item in humble_items.values():
            try:
                machine_name = item['machine_name']
                name = item['human_name']
                devs = item['developers']
                author = ''
                for dev in devs:
                    author = author + "{sep}{name} ({url})".format(sep=(', ' if author else ''),
                                                                   name=dev['developer_name'],
                                                                   url=dev['developer_url'])
                pubs = item['publishers']
                publisher = ''
                for pub in pubs:
                    publisher = publisher + "{sep}{name} ({url})".format(sep=(', ' if publisher else ''),
                                                                         name=pub['publisher_name'],
                                                                         url=pub['publisher_url'])
                description = item['description_text']
                items_dict[machine_name] = {
                    'name': name,
                    'author': author,
                    'publisher': publisher,
                    'description': description
                }
            except Exception as e:
                # print('Error en display_items: ' + str(e))
                pass
        if title_tiers:
            for idx, tier in enumerate(title_tiers):
                print('\n\n\n\nTIER ' + str(idx) + '\n\n')
                for name in tier:
                    item = items_dict[name]
                    print(item['name'])
                    print(item['author'])
                    print(item['publisher'])
                    print(item['description'])
                    print('------------------------------------------------')
        else:
            for item in items_dict.values():
                print(item['name'])
                print(item['author'])
                print(item['publisher'])
                print(item['description'])
                print('------------------------------------------------')
    except Exception as e:
        print(str(e))


# Lanzamos la función principal
if __name__ == "__main__":
    main()
