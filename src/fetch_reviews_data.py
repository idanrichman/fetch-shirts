#%%
# Variables
data_folder = 'data'
search_results_folder = 'search_results'

# Environment Setup
import requests
import pandas as pd
from bs4 import BeautifulSoup
from random import randint
import re
import json
import time
import shutil
import os
import glob

#%%
# Functions definitions

def check_response(r):
    #assert r.status_code==200, 'bad response'
    return True if r.ok else False

def is_cust_images(product_html_bs):
    return len(product_html_bs.find_all('img', alt='Customer image')) > 0

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
    #len(reviews_html.find_all('div', attrs={'data-hook': "review"}))
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
    try:
        r = s.get('http://www.amazon.com/dp/%s' % asin)
        is_ok = check_response(r)
    except:
        is_ok = False

    asin_summary = pd.DataFrame()
    if is_ok:
        html = BeautifulSoup(r.content.decode(), 'lxml')
        for tag in html.find_all('script', type='text/javascript'):
            if 'colorToAsin' in tag.text:  # there's a second jquery match, without the colorToAsin substring
                data = re.search('jQuery.parseJSON\(\'(.+)\'\);\n', tag.text)
                if data is not None:
                    data_json = json.loads(data.group(1).replace("\\\'", "\'"))  # the replace just escapes to avoid a common problem
       
        if is_cust_images(html):
            reviews_images_urls = {key: '|'.join(value) for key, value in get_reviews_images_urls(s, asin).items()}

            colors_asin = {color: data_json['colorToAsin'][color]['asin'] for color in reviews_images_urls.keys() if color != 'unknown'}

            # use large / hiRes
            #colors_images = {color: data_json['colorImages'][color][0]['hiRes'] for color in reviews_images_urls.keys() if color != 'unknown'}
            colors_images = dict()
            for color in reviews_images_urls.keys():
                if color=='unknown':
                    continue
                color_urls = data_json['colorImages'][color][0]
                if 'hiRes' in color_urls.keys():
                    colors_images[color] = color_urls['hiRes']
                elif 'large' in color_urls.keys():
                    colors_images[color] = color_urls['large']
            asin_summary = pd.DataFrame([reviews_images_urls, colors_asin, colors_images], 
                                        index=['reviews_images_urls', 'asin', 'image']) \
                                        .T.reset_index().set_index('asin').rename(columns={'index': 'color'}).assign(master_asin=asin).query('color != "unknown"')
    return asin_summary
    

def get_search_results(search_term = 'shirt', search_cat = 'fashion-womens-clothing', pagenumber = 1):
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
                                  tag.find('img').get('src')) 
                                 for tag in search_results_divs], 
                                columns=['asin', 'title', 'image', 'image_thumb']).set_index('asin')
    except:
        None
    return result

def download_jpg(session, image_url, image_filename):
    try:  # mainly to avoid connection error raised
        response = session.get(image_url, stream=True)
        if response.ok:
            with open(image_filename, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
    except:  # i don't really care if i'm missing some products on the way
        None

#%%

def main():
    s = requests.Session()
    s.headers.update({"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"})

    os.makedirs(data_folder, exist_ok=True)

    products_sum_list = []
    products_paths = glob.glob(os.path.join(search_results_folder, '*.jpg'))
    for i, filepath in enumerate(products_paths):
        print('\rfetching product details %i/%i' % (i+1, len(products_paths)), end='')
        asin = os.path.split(filepath)[-1].replace('.jpg', '')  # get only the filename
        products_sum_list.append(summarize_asin(s, asin))
        time.sleep(randint(2,5))

    products_sum = pd.concat(products_sum_list)
    products_sum.to_csv('products_summary.csv')
    print('\nDone.')

    for asin_i, (asin, row) in enumerate(products_sum.iterrows()):
        print('\r%i/%i Fetching product reviews %s         ' % (asin_i+1, len(products_sum), asin), end='')
        asin_path = os.path.join(data_folder, asin)
        os.makedirs(asin_path, exist_ok=True)
        download_jpg(s, row['image'], os.path.join(asin_path, 'product.jpg'))
        for i, review_url in enumerate(row['reviews_images_urls'].split('|')):
            download_jpg(s, review_url, os.path.join(asin_path, '_%i.jpg' % i))

    print('\nDone.')

#%%
if __name__ == '__main__':
    main()

#%%
# s = requests.Session()
# s.headers.update({"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"})

# summ = summarize_asin(s, 'B01N53IXD6')
# summ


#%%
