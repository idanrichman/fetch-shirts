import yaml
import os

with open(os.path.join('..', 'config.yaml'), 'r') as stream:
    settings = yaml.load(stream)

for folder in ['data_folder',
               'search_results_folder',
               'processed_pairs_folder',
               'filtered_pairs_folder',
               'train_data_folder',
               'tables_folder',
               'alternative_product_imgs']:
    settings[folder] = os.path.join('..', 'output', settings[folder])

for folder in ['faces_folder',
               'half_face_folder',
               'filtered_out_folder',
               'jsons_folder']:
    settings[folder] = os.path.join(settings['search_results_folder'], settings[folder])

settings['header'] = settings['headers'][settings['header_option']]
