import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import pickle
import os
import time
from settings import settings
import dash_auth
import shutil
import requests
import pandas as pd

max_sub_imgs = 10
chosen_img = None
counter = 0
tot_count = 0


class ProductComponents:
    """Dash components of a specific asin.

    :param asin: the asin code of the Product
    """

    def __init__(self, asin, max_horz_images=4, multi_selection=False):
        self.asin = asin
        self.max_horz_images = max_horz_images
        self.multi_selection = multi_selection
        self.variants_nameurl = self._load_asin_images(asin)
        self.num_of_subimages = len(self.variants_nameurl)
        self.main_img_url = self.variants_nameurl[0][1]
        self.main_img_div = self._init_main_img()
        self.sub_imgs_components = self._init_sub_imgs()
        self.sub_imgs_div = self._init_sub_imgs_div()

    def _load_asin_images(self, asin):
        """Load the product variant images for a given asin code."""
        with open('%s/%s.pkl' % (settings['jsons_folder'], asin), 'rb') as f:
            asin_data = pickle.load(f)
        landingAsinColor = asin_data['landingAsinColor']
        variants = asin_data['colorImages'][landingAsinColor]
        variants_nameurl = [(variant['variant'],
                             variant['large'],
                             variant['hiRes'] if 'hiRes' in variant.keys() else variant['large']  # not all variants has hiRes version
                             ) for variant in variants]
        return variants_nameurl

    def _init_main_img(self):
        main_image_elem = html.Div([
                                    html.Img(id='main_img', src=self.main_img_url,
                                             alt='no more images',
                                             style={'height': '30vh'})
                                    ],
                                   style={'textAlign': 'center', 'margin': '50px'},
                                   id='main_div')
        return main_image_elem

    def _make_image_component(self, index):
        return html.Img(id='image%i' % index,
                        src=self.variants_nameurl[index-1][1] if index <= self.num_of_subimages else '',
                        title=self.variants_nameurl[index-1][0] if index <= self.num_of_subimages else '',
                        alt=self.variants_nameurl[index-1][2] if index <= self.num_of_subimages else '',
                        style={'max-width': '%i%%' % (90 / min(self.num_of_subimages,
                                                               self.max_horz_images)),
                               'max-height': '30vh',
                               'border': '5px solid white',
                               'cursor': 'pointer'},
                        accessKey=str(index),
                        n_clicks_timestamp=0,
                        hidden=0 if index <= self.num_of_subimages else 1)

    def _init_sub_imgs(self):
        return [self._make_image_component(i+1) for i in range(max_sub_imgs)]

    def _init_sub_imgs_div(self):
        return html.Div(
                        self.sub_imgs_components,
                        style={'textAlign': 'center'},
                        id='sub_div')


def maxIndex(lst):
    """Return the index of the maximum value in list."""
    return max(range(len(lst)), key=lst.__getitem__)


def update_dict(d, key_value_dict):
    d.update(key_value_dict)
    return d


def init_dash(asin):
    app = dash.Dash()
    next_button = html.Button('Next ->', id='nextButton', style={'font-size': 30, 'cursor': 'pointer'})
    next_button_div = html.Div([next_button], style={'textAlign': 'center', 'margin': '50px'})
    product = ProductComponents(asin)

    app.layout = html.Div([html.Span(id='counter'), html.Span(' '*10),
                           dcc.Input(id='jump', debounce=True, type='number', min=1, max=tot_count),
                           html.Span(' '*10), html.Span(product.asin, id='asin_div', style={'textAlign': 'center', 'margin': '50px'}),
                           product.main_img_div,
                           next_button_div,
                           product.sub_imgs_div,
                           ])

    make_img_callbacks(app, product)
    make_callbacks(app)
    return app


def make_img_callbacks(app, product):
    if not product.multi_selection:
        @app.callback([Output('image%i' % (index+1), 'style')
                       for index in range(max_sub_imgs)],
                      [Input('image%i' % (index+1), 'n_clicks_timestamp')
                       for index in range(max_sub_imgs)],
                      [State('image%i' % (index+1), 'style')
                       for index in range(max_sub_imgs)])
        def image_single_select(*args):
            global chosen_img
            inputs = args[:max_sub_imgs]
            states = args[max_sub_imgs:]
            if max(inputs) > 0:
                _chosen_img = maxIndex(inputs)
                chosen_img = _chosen_img if _chosen_img != chosen_img else None  # to allow un-selection
            return [update_dict(states[i], {'border': states[i]['border'].replace('white', 'red')})
                    if (chosen_img == i)
                    else update_dict(states[i], {'border': states[i]['border'].replace('red', 'white')})
                    for i in range(len(states))]
    else:
        for index in range(max_sub_imgs):
            @app.callback(Output('image%i' % index+1, 'style'),
                          [Input('image%i' % index+1, 'n_clicks')],
                          [State('image%i' % index+1, 'style')])
            def image_multi_select(n_clicks, style):
                if n_clicks is not None:
                    if 'red' in style['border']:  # if its already selected
                        style['border'] = style['border'].replace('red', 'white')
                    else:
                        style['border'] = style['border'].replace('white', 'red')
                return style


def make_callbacks(app):
    @app.callback([Output('main_img', 'src'), Output('sub_div', 'children'), Output('asin_div', 'children'),
                   Output('counter', 'children')],
                  [Input('nextButton', 'n_clicks'), Input('jump', 'value')],
                  [State('main_img', 'src'), State('sub_div', 'children'), State('asin_div', 'children'),
                   State('nextButton', 'n_clicks_timestamp'), State('jump', 'n_submit_timestamp')])
    def next_button_on_click(n_clicks, override_counter, orig_src, orig_sub_div, orig_asin, next_ts, jump_ts):
        global chosen_img
        global counter

        if (jump_ts is not None) & (next_ts is not None):
            next_ts_str = pd.Timestamp(next_ts*1e6).strftime('%Y-%m-%dT%H:%M:%S.%fz')
            if jump_ts > next_ts_str:
                counter = override_counter - 2

        if (n_clicks is not None):
            counter += 1
            counter_str = '%i / %i' % (counter+1, tot_count)

            log_results(orig_asin, orig_sub_div)
            chosen_img = None  # reset the choice

            # initialize next product
            try:
                asin = asins[counter]
            except IndexError:  # if reached the end of counter
                asin = None
            if asin is not None:
                product = ProductComponents(asin)
                return (product.main_img_url, product.sub_imgs_components, asin, counter_str)
            else:
                return ('', '', '', counter_str)
        else:
            return (orig_src, orig_sub_div, orig_asin, '%i / %i' % (counter+1, tot_count))


def log_results(asin, sub_div):
    """Saves the user decision."""
    csv_path = os.path.join(settings['tables_folder'], 'alternative_product_imgs.csv')
    if not os.path.exists(csv_path):
        with open(csv_path, "w") as myfile:
            myfile.write(','.join(['time', 'counter', 'asin', 'chosen_img', 'title', 'url'])+'\n')

    if chosen_img is not None:
        # log choice to file
        title = sub_div[chosen_img]['props']['title']
        url = sub_div[chosen_img]['props']['src']
        hires_url = sub_div[chosen_img]['props']['alt']
        with open(csv_path, "a") as myfile:
            myfile.write(','.join([time.strftime("%Y-%m-%d %H:%M:%S"), str(counter), asin, str(chosen_img), title, url])+'\n')
        # save new image as the asin jpeg
        download_jpg(s, hires_url, os.path.join(settings['alternative_product_imgs'], asin + '.jpg'))


def load_asins_list(folders):
    """folders is a list of strings."""
    all_files = []
    for folder in folders:
        all_files.extend(os.listdir(folder))
    asins_list = [asin.replace('.jpg', '') for asin in all_files if '.jpg' in asin]
    global tot_count
    tot_count = len(asins_list)
    return asins_list


def download_jpg(session, image_url, image_filename):
    try:  # mainly to avoid connection error raised
        response = session.get(image_url, stream=True)
        if response.ok:  # not using check_response becuase it will ruin the stream=True and create a zero byte files
            with open(image_filename, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
        success = True
    except:  # i don't really care if i'm missing some products on the way
        success = False

    return success


if __name__ == '__main__':
    os.makedirs(settings['alternative_product_imgs'], exist_ok=True)

    s = requests.Session()
    s.headers.update({"user-agent": settings['header']})

    asins = load_asins_list([settings['faces_folder'], settings['half_face_folder'], settings['filtered_out_folder']])
    #asins = load_asins_list([settings['search_results_folder']])
    app = init_dash(asins[counter])

    # Keep this out of source code repository - save in a file or a database
    if os.path.exists('../auth_cred'):
        with open('../auth_cred', 'r') as credfile:
            VALID_USERNAME_PASSWORD_PAIRS = eval(credfile.read())

        auth = dash_auth.BasicAuth(
            app,
            VALID_USERNAME_PASSWORD_PAIRS
        )

        app.run_server(debug=True, host='0.0.0.0')
    else:
        print("Error: can't find auth_cred file. it should contain authenticatin details as [['username', 'password']]")
