# Takes already fetched search results and query product by product to
# determine if it has costumer reviews with images
# it will also save a pickle file with the products images urls inside
# the jsons_folder as defined in config.yaml

# Environment Setup
import requests
import pandas as pd
from bs4 import BeautifulSoup
from random import randint
import re
import json
import time
import os
import pickle

from settings import settings
from helper import check_response, ConnectionBlockedError, PageNotFoundError


def is_cust_images(product_html_bs):
    return len(product_html_bs.find_all('img', alt='Customer image')) > 0


def fetch_asin_data(s, asin):
    has_customer_images_reviews = None
    pickle_path = os.path.join(settings['jsons_folder'], asin + '.pkl')
    # check if product asin was already scraped. if it was, then return its has_customer_images_reviews result saved before
    if os.path.exists(pickle_path):
        with open(pickle_path, "rb") as f:
            has_customer_images_reviews = pickle.load(f)['has_customer_images_reviews']
    else:
        try:
            time.sleep(randint(settings['min_delay'], settings['max_delay']))
            r = s.get('https://www.amazon.com/dp/%s' % asin)
            check_response(r)
        except ConnectionBlockedError as e:
            print('\nFailed asin: %s' % asin)
            raise e
        except Exception as e:
            print('\n', e)

        html = BeautifulSoup(r.content.decode(), 'lxml')

        for tag in html.find_all('script', type='text/javascript'):
            if 'colorToAsin' in tag.text:  # there's a second jquery match, without the colorToAsin substring
                data = re.search('jQuery.parseJSON\(\'(.+)\'\);\n', tag.text)
                if data is not None:
                    data_json = json.loads(data.group(1).replace("\\\'", "\'"))  # the replace just escapes to avoid a common problem
                    has_customer_images_reviews = 1 if is_cust_images(html) else 0
                    data_json['has_customer_images_reviews'] = has_customer_images_reviews
                    with open(pickle_path, "wb") as f:
                        pickle.dump(data_json, f)

    return has_customer_images_reviews


def main():
    s = requests.Session()
    s.headers.update({"user-agent": settings['header']})

    # assuming tables folder already exists with a stage1 table in it.
    search_results = pd.read_csv(os.path.join(settings['tables_folder'],
                                              'search_results_stage1.csv'), index_col='asin')
    search_results = search_results[search_results['reviews'] >= settings['min_reviews']]
    search_results['has_image_reviews'] = None  # create a column

    os.makedirs(settings['jsons_folder'], exist_ok=True)

    max_cycles = 10
    i_cycle = 0

    while search_results['has_image_reviews'].isna().any() & (i_cycle < max_cycles):
        i_cycle += 1
        print('Cycle %i:' % i_cycle)
        fetch_queue = search_results[search_results['has_image_reviews'].isna()]
        for i, (asin, asin_data) in enumerate(fetch_queue.iterrows()):
            print('\rFetching %i/%i' % (i+1, len(fetch_queue)), end='')
            search_results.loc[asin, 'has_image_reviews'] = fetch_asin_data(s, asin)
            

    print('\nDone.')
    if search_results['has_image_reviews'].isna().any():
        print('Failed to fetch %i products data' % search_results['has_image_reviews'].isna().sum())
    search_results.to_csv(os.path.join(settings['tables_folder'], 'search_results_stage2.csv'))


if __name__ == '__main__':
    main()
