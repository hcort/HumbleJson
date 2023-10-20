import json
import os

from Pool import mutex
from utils import run_parameters, get_backup_file


class BundleException(BaseException):

    def __init__(self, message):
        super().__init__(message)


class BundleInfo:

    def __init__(self, whole_bundle_dict={}, backup_file=None, from_file=False):
        if from_file:
            self.__dict = whole_bundle_dict
        else:
            self.__dict = {
                'name': whole_bundle_dict.get('bundleData', {}).get('basic_data', {}).get('human_name', ''),
                'machine_name': whole_bundle_dict.get('bundleData', {}).get('machine_name', ''),
                'tier_item_data': whole_bundle_dict.get('bundleData', {}).get('tier_item_data', {}),
                'tier_order': whole_bundle_dict.get('bundleData', {}).get('tier_order', []),
                'tier_display_data': whole_bundle_dict.get('bundleData', {}).get('tier_display_data', {})
            }
        self.__backup_file = backup_file

    @classmethod
    def from_file(cls, backup_file):
        with open(backup_file, 'r') as content:
            return cls(whole_bundle_dict=json.load(content), backup_file=backup_file, from_file=True)

    def __getitem__(self, key):
        return self.__dict[key]

    def __setitem__(self, key, value):
        with mutex:
            self.__dict[key] = value

    def get(self, key, default=None):
        return self.__dict.get(key, default)

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
        if lock:
            with mutex:
                with open(self.__backup_file, 'w') as file:
                    json.dump(self.__dict, file)
        else:
            with open(self.__backup_file, 'w') as file:
                json.dump(self.__dict, file)

    def set_books_found(self, key, books_found):
        with mutex:
            self.__dict['tier_item_data'][key]['books_found'] = books_found
            self.save_to_file(lock=False)

    def set_book_downloaded(self, key, book_md5):
        with mutex:
            self.__dict['tier_item_data'][key]['books_found'].pop(book_md5)
            if not self.__dict['tier_item_data'][key]['books_found']:
                self.__dict['tier_item_data'][key]['downloaded'] = True
            self.save_to_file(lock=False)

    def set_all_books_downloaded(self, key, downloaded=True):
        with mutex:
            self.__dict['tier_item_data'][key]['downloaded'] = downloaded
            self.save_to_file(lock=False)

    def set_tiers(self, new_tiers):
        with mutex:
            self.__dict['tier_display_data'] = new_tiers
            self.save_to_file(lock=False)

    def create_default_tiers(self):
        with mutex:
            self.__dict['tier_order'] = ['all']
            self.__dict['tier_display_data'] = {
                'all': {
                    'tier_item_machine_names': []
                }
            }
            for item in self.__dict['tier_item_data']:
                self.__dict['tier_display_data']['all']['tier_item_machine_names'].append(item)
            self.save_to_file(lock=False)
