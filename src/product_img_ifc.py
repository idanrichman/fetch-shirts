import dash
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pickle
from settings import settings

chosen_img = None


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
        variants_nameurl = [(variant['variant'], variant['large']) for variant in variants]
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
                        src=self.variants_nameurl[index-1][1],
                        style={'max-width': '%i%%' % (90 / min(self.num_of_subimages,
                                                               self.max_horz_images)),
                               'max-height': '30vh',
                               'border': '5px solid white',
                               'cursor': 'pointer'},
                        accessKey=str(index),
                        n_clicks_timestamp=0)

    def _init_sub_imgs(self):
        return [self._make_image_component(i+1) for i in range(self.num_of_subimages)]

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

    app.layout = html.Div([product.main_img_div,
                           html.Div(product.asin, id='asin_div', style={'textAlign': 'center', 'margin': '50px'}),
                           next_button_div,
                           product.sub_imgs_div,
                           ])

    make_img_callbacks(app, product)
    make_callbacks(app)
    return app


def make_img_callbacks(app, product):
    if not product.multi_selection:
        @app.callback([Output('image%i' % (index+1), 'style')
                       for index in range(product.num_of_subimages)],
                      [Input('image%i' % (index+1), 'n_clicks_timestamp')
                       for index in range(product.num_of_subimages)],
                      [State('image%i' % (index+1), 'style')
                       for index in range(product.num_of_subimages)])
        def image_single_select(*args):  # disable to allow multiple selection
            global chosen_img
            inputs = args[:product.num_of_subimages]
            states = args[product.num_of_subimages:]
            if max(inputs) > 0:
                _chosen_img = maxIndex(inputs)
                chosen_img = _chosen_img if _chosen_img != chosen_img else None  # to allow un-selection
            return [update_dict(states[i], {'border': states[i]['border'].replace('white', 'red')})
                    if (chosen_img == i)
                    else update_dict(states[i], {'border': states[i]['border'].replace('red', 'white')})
                    for i in range(len(states))]
    else:
        for index in range(product.num_of_subimages):
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
    @app.callback([Output('main_img', 'src'), Output('sub_div', 'children'), Output('asin_div', 'children')],
                  [Input('nextButton', 'n_clicks')],
                  [State('main_img', 'src'), State('sub_div', 'children'), State('asin_div', 'children')])
    def next_button_on_click(n_clicks, orig_src, orig_sub_div, orig_asin):
        if (n_clicks is not None):# & (chosen_img is not None):
            #return '%s; %s' % (image_filename, subimages_filenames[chosen_img][1])
            asin = next(asins, None)
            if asin is not None:
                product = ProductComponents(asin)
                return (product.main_img_url, product.sub_imgs_components, asin)
            else:
                return ('', '', '')
        else:
            return (orig_src, orig_sub_div, orig_asin)

    @app.callback(Output('asin_div', 'style'),
                  [Input('sub_div', 'children')],
                  [State('asin_div', 'children'), State('asin_div', 'style')])
    def on_sub_img_chg(asin, style):
        product = ProductComponents(asin)
        make_img_callbacks(app, product)
        return style


def list_generator(mylist):
    i = 0
    while i < len(mylist):
        yield mylist[i]
        i += 1


asins = list_generator(['B00AHXIC96', 'B00BZV0AN0', 'B00CC3LRVE', 'B00DPEY5E0'])

if __name__ == '__main__':
    app = init_dash(next(asins))
    app.run_server(debug=True)
