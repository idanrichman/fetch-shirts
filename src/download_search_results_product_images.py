# Takes the search results data table and downloads the product images

# Environment Setup
import requests
import pandas as pd
from random import randint
import time
import shutil
import os
import sys

from settings import settings


def check_response(r):
    # assert r.status_code==200, 'bad response'
    return True if r.ok else False


def download_jpg(session, image_url, image_filename):
    try:  # mainly to avoid connection error raised
        response = session.get(image_url, stream=True)
        if check_response(response):
            with open(image_filename, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
    except:  # i don't really care if i'm missing some products on the way
        None


def main(start_from=0):
    # start_from - for a warm start to continue if stuck
    s = requests.Session()
    s.headers.update({"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"})

    os.makedirs(settings['search_results_folder'], exist_ok=True)
    search_results = pd.read_csv(os.path.join(settings['tables_folder'],
                                              'search_results.csv'))

    # no use of downloading products with no reviews
    search_results = search_results[search_results['reviews'] >= settings['min_reviews']]
    search_results = search_results[:settings['max_products']]  # if max_products is larger than the dataframe, it'll return all of the df

    for i, (asin, asin_data) in enumerate(search_results[start_from:].iterrows()):
        print('\rDownloading %i/%i' % (i+start_from, len(search_results)), end='')
        image_filename = os.path.join(settings['search_results_folder'], asin + '.jpg')
        image_url = asin_data['image']
        download_jpg(s, image_url, image_filename)
        time.sleep(randint(settings['min_delay'], settings['max_delay']))
    print('\nDone.')


if __name__ == '__main__':
    start_from = 0
    if len(sys.argv) > 1:
        start_from = sys.argv[1]
    main(start_from)
