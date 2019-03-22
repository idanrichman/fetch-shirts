# Environment Setup
import requests
import pandas as pd
from bs4 import BeautifulSoup
from random import randint
import re
import time
import shutil
import os
import glob
import pickle

from settings import settings
from helper import check_response, ConnectionBlockedError


def get_review_color(review):
    # BUG: FOR SOME REASON IT NOT ALWAYS HAS THE COLOR TAG (ALTHOUGH IN THE BROWSER IT DOES SHOW)
    review_color = 'unknown'
    review_color_tag = review.find('a', attrs={'data-hook': "format-strip"})
    if review_color_tag is not None:
        color_text = [item for item in list(review_color_tag.children) if 'Color:' in item]
        if len(color_text) > 0:
            review_color = color_text[0].strip('Color: ')
    return review_color


def extract_hires_url(orig_url):
    """Take an image url and removes the resolution suffix that is before the .jpg ending"""
    url = None
    url_matchs = re.match('(.+/images/I/)(.+?)\..*(jpg)', orig_url)
    if url_matchs is not None:
        url = url_matchs.group(1) + url_matchs.group(2) + '.' + url_matchs.group(3)
    return url


def get_review_images_urls(review):
    urls = []
    review_images_tags = review.find_all('img', alt="review image")
    for tag in review_images_tags:
        # enforcing jpg  to avoid getting any movies urls
        url = extract_hires_url(tag.get('src'))
        if url is not None:
            urls.append(url)
    return urls


def get_total_reviews_count(reviews_html):
    # len(reviews_html.find_all('div', attrs={'data-hook': "review"}))
    # should be 8. if less than 8 then this is the last page in the pagination.

    # another approach for pagination (and to avoid unnessacery page reading) is to check the total number of returned search queries and see if we reached the maximum
    total_count_text = reviews_html.find('span', attrs={'data-hook': "cr-filter-info-review-count"}).text
    total_media_reviews = int(re.match('.+of (\d+) reviews', total_count_text).group(1))
    return total_media_reviews

def get_reviews_images_urls(s, asin):
    pagenumber = 1
    reached_last_page = False
    review_i = 0
    results = {}

    while reached_last_page is False:
        r = s.get('https://www.amazon.com/product-reviews/%s/?reviewerType=all_reviews&mediaType=media_reviews_only&pageNumber=%i' % (asin, pagenumber))
        check_response(r)
        reviews_html = BeautifulSoup(r.content, 'lxml')
        if pagenumber==1:  # only checking in the first page, because amazon makes mistake and sometimes doesn't show the count line
            tot_reviews_count = get_total_reviews_count(reviews_html)

        ## find the color and the image of the review
        reviews = reviews_html.find_all('div', attrs={'data-hook': "review"})

        for review in reviews:
            review_i += 1
            color = get_review_color(review)
            urls = get_review_images_urls(review)

            if color in results.keys():
                results[color] = results[color] + urls
            else:
                results[color] = urls

        if review_i == tot_reviews_count:
            reached_last_page = True

        pagenumber += 1
    return results


def summarize_asin(s, asin):
    asin_summary = pd.DataFrame()
    pickle_path = os.path.join(settings['jsons_folder'], asin + '.pkl')
    # check if product asin was already scraped. if it was, then return its has_customer_images_reviews result saved before
    if os.path.exists(pickle_path):
        with open(pickle_path, "rb") as f:
            data_json = pickle.load(f)

        reviews_images_urls = {key: '|'.join(value) for key, value in get_reviews_images_urls(s, asin).items()}
        color_list = list(reviews_images_urls.keys())
        for color in color_list:
            if color not in data_json['colorToAsin'].keys():
                reviews_images_urls.pop(color)

        colors_asin = {color: data_json['colorToAsin'][color]['asin'] for color in reviews_images_urls.keys()}

        # use large / hiRes
        #colors_images = {color: data_json['colorImages'][color][0]['hiRes'] for color in reviews_images_urls.keys() if color != 'unknown'}
        colors_images = dict()
        for color in reviews_images_urls.keys():
            color_urls = data_json['colorImages'][color][0]
            if 'hiRes' in color_urls.keys():
                colors_images[color] = color_urls['hiRes']
            elif 'large' in color_urls.keys():
                colors_images[color] = color_urls['large']
        asin_summary = pd.DataFrame([reviews_images_urls, colors_asin, colors_images],
                                    index=['reviews_images_urls', 'asin', 'image']) \
                                    .T.reset_index().set_index('asin').rename(columns={'index': 'color'}).assign(master_asin=asin)
    else:
        print('Error: Cannot find:', pickle_path)

    return asin_summary


def download_jpg(session, image_url, image_filename):
    try:  # mainly to avoid connection error raised
        response = session.get(image_url, stream=True)
        if response.ok:
            with open(image_filename, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
    except ConnectionBlockedError as e:
        raise e
    except:  # i don't really care if i'm missing some products on the way
        None


def main():
    s = requests.Session()
    s.headers.update({"user-agent": settings['header']})

    os.makedirs(settings['data_folder'], exist_ok=True)

    products_sum_list = []
    products_paths = glob.glob(os.path.join(settings['search_results_folder'], '*.jpg'))
    for i, filepath in enumerate(products_paths):
        print('\rfetching product details %i/%i' % (i+1, len(products_paths)), end='')
        asin = os.path.split(filepath)[-1].replace('.jpg', '')  # get only the filename
        products_sum_list.append(summarize_asin(s, asin))
        time.sleep(randint(settings['min_delay'], settings['max_delay']))

    products_sum = pd.concat(products_sum_list)
    products_sum.to_csv(os.path.join(settings['tables_folder'],
                                              'products_summary.csv'))
    print('\nDone.')

    for asin_i, (asin, row) in enumerate(products_sum.iterrows()):
        print('\r%i/%i Fetching product reviews %s         ' % (asin_i+1, len(products_sum), asin), end='')
        asin_path = os.path.join(settings['data_folder'], asin)

        if settings['overwrite_data'] | (not os.path.exists(asin_path)):
            os.makedirs(asin_path, exist_ok=True)

            download_jpg(s, row['image'], os.path.join(asin_path, 'product.jpg'))
            for i, review_url in enumerate(row['reviews_images_urls'].split('|')):
                download_jpg(s, review_url, os.path.join(asin_path, '_%i.jpg' % i))

    print('\nDone.')

if __name__ == '__main__':
    main()
