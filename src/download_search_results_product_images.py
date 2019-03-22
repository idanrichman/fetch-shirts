# Takes the search results data table and downloads the product images

# Environment Setup
import requests
import pandas as pd
from random import randint
import time
import os
import shutil

from settings import settings
from helper import check_response, ConnectionBlockedError


def download_jpg(session, image_url, image_filename):
    try:  # mainly to avoid connection error raised
        response = session.get(image_url, stream=True)
        if response.ok:  # not using check_response becuase it will ruin the stream=True and create a zero byte files
            with open(image_filename, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
        success = True
    except ConnectionBlockedError as e:
        raise e
    except:  # i don't really care if i'm missing some products on the way
        success = False

    return success


def main():
    s = requests.Session()
    s.headers.update({"user-agent": settings['header']})
    
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
