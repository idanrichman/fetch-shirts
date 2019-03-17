# Takes the search results data table and downloads the product images

# Environment Setup
import requests
import pandas as pd
from random import randint
import time
import shutil
import os

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
        success = True
    except:  # i don't really care if i'm missing some products on the way
        success = False

    return success


def main():
    # start_from - for a warm start to continue if stuck
    s = requests.Session()
    s.headers.update({"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"})

    os.makedirs(settings['search_results_folder'], exist_ok=True)
    search_results = pd.read_csv(os.path.join(settings['tables_folder'],
                                              'search_results_stage2.csv'), index_col='asin')

    # no use of downloading products with no reviews
    search_results = search_results[search_results['reviews'] >= settings['min_reviews']]
    # no use of downloading products with no images reviews
    search_results = search_results[search_results['has_image_reviews'] == 1]
    search_results = search_results[:settings['max_products']]  # if max_products is larger than the dataframe, it'll return all of the df

    max_cycles = 10
    i_cycle = 0
    fetch_queue = list(search_results.index)

    while (len(fetch_queue) > 0) & (i_cycle < max_cycles):
        i_cycle += 1
        print('Cycle %i:' % i_cycle)
        loop_queue = search_results.loc[fetch_queue]

        for i, (asin, asin_data) in enumerate(loop_queue.iterrows()):
            print('\rDownloading %i/%i: %s' % (i+1, len(loop_queue), asin), end='')
            image_filename = os.path.join(settings['search_results_folder'], asin + '.jpg')
            image_url = asin_data['image']
            if not os.path.exists(image_filename):  # avoid double downloading
                if download_jpg(s, image_url, image_filename):
                    fetch_queue.remove(asin)
                time.sleep(randint(settings['min_delay'], settings['max_delay']))
            else:
                fetch_queue.remove(asin)

    print('\nDone.')

if __name__ == '__main__':
    main()
