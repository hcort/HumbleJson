"""
    Definition of class BundleInfo, that encapsulates the information from a Humble Bundle
"""
import sys
from threading import Lock

import json

from utils import get_backup_file


class BundleException(BaseException):

    def __init__(self, message):
        super().__init__(message)


class BundleInfo:
    """
    Encapsulates the data extracted from the Humble Bundle page

    Uses a mutex to prevent concurrent access in write operations

    {
        "name": ...,
        "machine_name": ...,
        "tier_item_data": {
            stores all the entries in the bundle
            Is a dictionary, which keys are the machine names of each book

            "bookmachinename": {
                "name": ...,
                "author": ...,
                "author_url": ...,
                "publisher": ...,
                "publisher_url": ...,
                "description": ...,
                "books_found": {},
                "downloaded": true/false
            }
            In the value of "books_found" we will store the books that we found in LibGen
            after searching for this book's title
        },
        "tier_order": [], -> a list of all the tier names
        "tier_display_data": {
            A dictionary with the info of each tier in the bundle.
            "tier name": {
                "tier_item_machine_names": [] ->  a list of the books in this tier
            },
        },
        "url": ..., -> The original URL of the bundle
        "from_backup": true/false -> to know if we read the dictionary from file or from the Humble Bundle page
    }
    """

    def __init__(self, whole_bundle_dict=None, backup_file=None, from_file=False):
        self.__bundle_dict_access_mutex = Lock()
        self.__backup_file = backup_file
        if whole_bundle_dict is None:
            whole_bundle_dict = {}
        if from_file:
            self.__dict = whole_bundle_dict
        else:
            if whole_bundle_dict:
                self.__dict = {
                    'name': whole_bundle_dict.get('bundleData', {}).get('basic_data', {}).get('human_name', ''),
                    'machine_name': whole_bundle_dict.get('bundleData', {}).get('machine_name', ''),
                    'tier_item_data': whole_bundle_dict.get('bundleData', {}).get('tier_item_data', {}),
                    'tier_order': whole_bundle_dict.get('bundleData', {}).get('tier_order', []),
                    'tier_display_data': whole_bundle_dict.get('bundleData', {}).get('tier_display_data', {})
                }
            self.build_bundle_dict()
            self.clean_upper_tiers()

    def __del__(self):
        if self.__bundle_dict_access_mutex.locked():
            print('bundle_dict_access_mutex - mutex bloqueado')

    @classmethod
    def from_file(cls, backup_file):
        with open(backup_file, 'r', encoding='utf-8') as content:
            return cls(whole_bundle_dict=json.load(content), backup_file=backup_file, from_file=True)

    def __getitem__(self, key):
        if (key == 'tier_display_data') and (key not in self.__dict.keys()):
            self.create_default_tiers()
        return self.__dict[key]

    def __setitem__(self, key, value):
        with self.__bundle_dict_access_mutex:
            self.__dict[key] = value

    def get(self, key, default=None):
        return self.__dict.get(key, default)

    def build_bundle_dict(self):
        humble_items = self.__dict['tier_item_data']
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
        self.__dict['tier_item_data'] = items_dict

    def clean_upper_tiers(self):
        # bigger tiers contain smaller tiers
        # tier content: tier_1 = ['a', 'b'], tier_2 = ['a', 'b', 'c', 'd'], tier_3 = ['a', 'b', 'c', 'd', 'e', ...]
        new_tiers = {}
        reversed_tier_order = list(reversed(self.__dict['tier_order']))
        new_tiers[reversed_tier_order[0]] = {
            'tier_item_machine_names': self.__dict['tier_display_data'][reversed_tier_order[0]][
                'tier_item_machine_names']
        }
        for tier in reversed(self.__dict['tier_order']):
            small_tier_items = self.__dict['tier_display_data'][tier]['tier_item_machine_names']
            reversed_tier_order.pop(0)
            for other_tier in reversed_tier_order:
                if tier != other_tier:
                    large_tier_list = self.__dict['tier_display_data'][other_tier]['tier_item_machine_names']
                    new_tiers[other_tier] = {
                        'tier_item_machine_names': [x for x in large_tier_list if x not in small_tier_items]
                    }
        self.set_tiers(new_tiers)

    @property
    def backup_file(self):
        if not self.__backup_file:
            self.__backup_file = get_backup_file(self.__dict['url'])
        return self.__backup_file

    @backup_file.setter
    def backup_file(self, backup_file=None):
        if not backup_file:
            self.__backup_file = get_backup_file(self.__dict['url'])
        else:
            self.__backup_file = backup_file

    def save_to_file(self, lock=True):
        if self.__backup_file:
            if lock:
                with self.__bundle_dict_access_mutex:
                    with open(self.__backup_file, 'w', encoding='utf-8') as file:
                        json.dump(self.__dict, file)
            else:
                with open(self.__backup_file, 'w', encoding='utf-8') as file:
                    json.dump(self.__dict, file)
        else:
            print('BundleInfo: file not defined')

    def set_books_found(self, key, books_found):
        with self.__bundle_dict_access_mutex:
            self.__dict['tier_item_data'][key]['books_found'] = books_found
            self.save_to_file(lock=False)

    def set_book_downloaded(self, key, book_md5):
        with self.__bundle_dict_access_mutex:
            self.__dict['tier_item_data'][key]['books_found'].pop(book_md5)
            if not self.__dict['tier_item_data'][key]['books_found']:
                self.__dict['tier_item_data'][key]['downloaded'] = True
            self.save_to_file(lock=False)

    def set_all_books_downloaded(self, key, downloaded=True):
        with self.__bundle_dict_access_mutex:
            self.__dict['tier_item_data'][key]['downloaded'] = downloaded
            self.save_to_file(lock=False)

    def set_tiers(self, new_tiers):
        with self.__bundle_dict_access_mutex:
            self.__dict['tier_display_data'] = new_tiers
            self.save_to_file(lock=False)

    def create_default_tiers(self):
        with self.__bundle_dict_access_mutex:
            self.__dict['tier_order'] = ['all']
            self.__dict['tier_display_data'] = {
                'all': {
                    'tier_item_machine_names': []
                }
            }
            for item in self.__dict['tier_item_data']:
                self.__dict['tier_display_data']['all']['tier_item_machine_names'].append(item)
            self.save_to_file(lock=False)
