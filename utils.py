import getopt
import os
import sys

import requests
from bs4 import BeautifulSoup

base_url = "http://libgen.rs/"

run_parameters = {
    'bundles': [],
    'libgen_base': base_url,
    'libgen_mirrors': [],
    'output_dir': '',
    'archive': False
}


def generate_filename(path, filename, extension):
    name = os.path.join(path, filename)
    numbered_name = name
    if os.path.exists(name):
        name_without_ext = name[:name.rfind('.')]
        idx = 0
        while os.path.exists(numbered_name):
            idx += 1
            numbered_name = '{}_{}.{}'.format(name_without_ext, idx, extension)
    return numbered_name


def get_soup_from_page(current_url):
    req = requests.get(current_url)
    if req.status_code != requests.codes.ok:
        return None
    response = req.content
    soup = BeautifulSoup(response, 'html.parser', from_encoding='utf-8')
    return soup


def display_help():
    print('Humble Bundle Json Extracter\n'
          '\tParamenters: -h | -u "urls to parse" | -a | -o "output_dir" | -l "url to libgen"\n'
          '\tLong parameters: help | urls="" | archive | out="" | libgen=""\n'
          '-u Input URLs. It can be a single URL or a list of comma separated URLs\n'
          '-a Flag to archive the Humble Bundle page into the Wayback Machine\n'
          '-o Output dir for the files from Library Genesis\n'
          '-l Base URL for the Libgen mirror\t')


def parse_arguments():
    argument_list = sys.argv[1:]
    options = "hu:ao:l:"
    long_options = ["help", "urls=", "archive",  "out=", "libgen="]
    try:
        arguments, values = getopt.getopt(argument_list, options, long_options)
        for current_argument, current_value in arguments:
            if current_argument in ('-h', long_options[0]):
                display_help()
            elif current_argument in ('-u', long_options[1]):
                url = current_value
                url_list = url.split(',')
                run_parameters['bundles'] = url_list
            elif current_argument in ('-a', long_options[2]):
                run_parameters['archive'] = True
            elif current_argument in ('-o', long_options[3]):
                run_parameters['output_dir'] = current_value
            elif current_argument in ('-l', long_options[4]):
                run_parameters['libgen_base'] = current_value
    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))