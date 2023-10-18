import datetime
import getopt
import os
import sys

from slugify import slugify

# base_url = "http://libgen.rs/"
libgen_search = {
    'base_url': "https://libgen.is/",
    'search_path': "search.php"
}
# libgen_search = {
#     'base_url': "https://libgen.li/",
#     'search_path': "index.php"
# }

run_parameters = {
    'bundles': [],
    'files': [],
    'libgen_base': libgen_search['base_url'],
    'libgen_search_path': libgen_search['search_path'],
    'libgen_mirrors': [],
    'output_dir': '',
    'archive': False
}


def delete_all_files(folder):
    for item in os.listdir(folder):
        os.remove(os.path.join(folder, item))


def wait_for_file_download_complete(folder, path):
    download_complete = False
    last_size = -1
    init_time = datetime.datetime.now()
    file_exists_retries = 10
    size_change_retries = 200
    while not download_complete:
        from time import sleep
        sleep(3)
        files = os.listdir(folder)
        if files:
            current_size = os.path.getsize(os.path.join(folder, files[0]))
            download_complete = not (files[0].endswith('opdownload')) and (last_size == current_size)
            if last_size == current_size:
                size_change_retries -= 1
            else:
                size_change_retries = 200
            last_size = current_size
        else:
            file_exists_retries -= 1
        if (not download_complete) and ((size_change_retries < 0) or (file_exists_retries < 0)):
            raise TimeoutError('Max number of retries downloading')
    move_file_download_folder(folder, path)


def move_file_download_folder(dl_folder, destination_folder):
    download_filename = os.listdir(dl_folder)[0]
    filename, file_extension = os.path.splitext(download_filename)
    valid_filename = f'{slugify(filename, max_length=100)}.{file_extension}'
    os.rename(
        os.path.join(dl_folder, download_filename),
        os.path.join(dl_folder, valid_filename)
    )
    os.replace(
        os.path.join(dl_folder, valid_filename),
        os.path.join(destination_folder, valid_filename)
    )


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


def get_backup_file(humble_url):
    url_path = humble_url.split('/')[-1]
    return os.path.join(run_parameters['output_dir'], url_path)


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
    long_options = ["help", "urls=", "archive",  "out=", "libgen=", "file="]
    try:
        arguments, values = getopt.getopt(argument_list, options, long_options)
        for current_argument, current_value in arguments:
            if current_argument in ('-h', long_options[0]):
                display_help()
            elif current_argument in ('-u', long_options[1]):
                run_parameters['bundles'] = current_value.split(',')
            elif current_argument in ('-f', long_options[5]):
                run_parameters['files'] = current_value.split(',')
            elif current_argument in ('-a', long_options[2]):
                run_parameters['archive'] = True
            elif current_argument in ('-o', long_options[3]):
                run_parameters['output_dir'] = current_value
            elif current_argument in ('-l', long_options[4]):
                run_parameters['libgen_base'] = current_value
    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))