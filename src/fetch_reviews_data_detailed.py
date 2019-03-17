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


def check_response(r):
    # assert r.status_code==200, 'bad response'
    return True if r.ok else False


def is_cust_images(product_html_bs):
    return len(product_html_bs.find_all('img', alt='Customer image')) > 0


def extract_hires_url(orig_url):
    """Take an image url and removes the resolution suffix that is before the .jpg ending"""
    url = None
    url_matchs = re.match('(.+/images/I/)(.+?)\..*(jpg)', orig_url)
    if url_matchs is not None:
        url = url_matchs.group(1) + url_matchs.group(2) + '.' + url_matchs.group(3)
    return url


def fetch_asin_data(s, asin):
    try:
        r = s.get('http://www.amazon.com/dp/%s' % asin)
        check_response(r)
    except:
        return None

    html = BeautifulSoup(r.content.decode(), 'lxml')

    for tag in html.find_all('script', type='text/javascript'):
        if 'colorToAsin' in tag.text:  # there's a second jquery match, without the colorToAsin substring
            data = re.search('jQuery.parseJSON\(\'(.+)\'\);\n', tag.text)
            if data is not None:
                data_json = json.loads(data.group(1).replace("\\\'", "\'"))  # the replace just escapes to avoid a common problem
                with open(os.path.join(settings['jsons_folder'], asin + '.pkl'), "wb") as f:
                    pickle.dump(data_json, f)

    has_customer_images_reviews = 1 if is_cust_images(html) else 0
    return has_customer_images_reviews


def main():
    # start_from - for a warm start to continue if stuck
    s = requests.Session()
    s.headers.update({"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"})

    search_results = pd.read_csv(os.path.join(settings['tables_folder'],
                                              'search_results_stage1.csv'), index_col='asin')
    search_results = search_results[search_results['reviews'] >= settings['min_reviews']]
    search_results['has_image_reviews'] = None  # create a column

    os.makedirs(settings['jsons_folder'], exist_ok=True)

# FIX THE [0:5] BELOW - REMOVE IT
    max_cycles = 10
    i_cycle = 0

    while search_results['has_image_reviews'].isna().any() & (i_cycle < max_cycles):
        i_cycle += 1
        print('Cycle %i:' % i_cycle)
        fetch_queue = search_results[search_results['has_image_reviews'].isna()]
        for i, (asin, asin_data) in enumerate(fetch_queue.iterrows()):
            print('\rFetching %i/%i' % (i+1, len(fetch_queue)), end='')
            search_results.loc[asin, 'has_image_reviews'] = fetch_asin_data(s, asin)
            time.sleep(randint(settings['min_delay'], settings['max_delay']))

    print('\nDone.')
    search_results.to_csv(os.path.join(settings['tables_folder'], 'search_results_stage2.csv'))


if __name__ == '__main__':
    main()
