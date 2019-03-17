# Fetch search results. returns the asin, title, images urls, num of reviews

# Environment Setup
import requests
import pandas as pd
from bs4 import BeautifulSoup
from random import randint
import re
import time
import os

from settings import settings


def check_response(r):
    # assert r.status_code==200, 'bad response'
    return True if r.ok else False


def extract_hires_url(orig_url):
    """Take an image url and removes the resolution suffix that is before the .jpg ending"""
    url = None
    url_matchs = re.match('(.+/images/I/)(.+?)\..*(jpg)', orig_url)
    if url_matchs is not None:
        url = url_matchs.group(1) + url_matchs.group(2) + '.' + url_matchs.group(3)
    return url


def get_search_results(s, search_term = settings['search_query'], search_cat = settings['search_category'], pagenumber = 1):
    try:
        result = pd.DataFrame()
        r = s.get('https://www.amazon.com/s?k=%s&i=%s&page=%i' % (search_term, search_cat, pagenumber))
        if check_response(r):
            search_html = BeautifulSoup(r.content, 'lxml')
            search_results_divs = (search_html.find('div', attrs={'class': 's-result-list sg-row'})
                                             .find_all(lambda tag: tag.has_attr('data-asin')))
            result = pd.DataFrame([(tag.get('data-asin'),
                                    tag.find('img').get('alt'),
                                    extract_hires_url(tag.find('img').get('src')),
                                    tag.find('img').get('src'),
                                    get_reviews_count_from_asin_tag(tag))
                                 for tag in search_results_divs], 
                                columns=['asin', 'title', 'image', 'image_thumb', 'reviews']).set_index('asin')
    except:
        None
    return result


def get_max_page_number(s, search_term = settings['search_query'], search_cat = settings['search_category']):
    try:
        r = s.get('https://www.amazon.com/s?k=%s&i=%s&page=1' % (search_term, search_cat))
        if check_response(r):
            search_html = BeautifulSoup(r.content, 'lxml')
            max_pages = int(search_html.select('ul.a-pagination li')[-2].text.replace(',', ''))
    except:
        max_pages = 0
    return max_pages


def get_reviews_count_from_asin_tag(tag):
    reviews_tag = tag.select('span[aria-label] span.a-size-base')
    reviews_count = int(reviews_tag[0].text.replace(',', '')) if reviews_tag != [] else 0
    return reviews_count


def main():
    os.makedirs(settings['tables_folder'], exist_ok=True)

    s = requests.Session()
    s.headers.update({"user-agent": settings['header']})

    search_results_list = []
    num_of_pages_to_fetch = get_max_page_number(s)  # take into account there are about 60 results per page
    for pagenumber in range(num_of_pages_to_fetch):
        print('\rfetching page %i/%i' % (pagenumber+1, num_of_pages_to_fetch), end='')
        search_results_list.append(get_search_results(s, pagenumber=pagenumber+1))
        time.sleep(randint(settings['min_delay'], settings['max_delay']))

    search_results = pd.concat(search_results_list)
    search_results = search_results[~search_results.index.duplicated()]  # drop duplicated asins
    search_results.to_csv(os.path.join(settings['tables_folder'], 'search_results_stage1.csv'))
    print('\nDone.')


if __name__ == '__main__':
    main()
