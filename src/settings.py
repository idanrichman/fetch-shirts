import yaml
import os

with open(os.path.join('..','config.yaml'), 'r') as stream:
    settings = yaml.load(stream)

for folder in ['data_folder',
               'search_results_folder',
               'processed_pairs_folder',
               'tables_folder']:
    settings[folder] = os.path.join('..', 'output', settings[folder])

for folder in ['faces_folder',
               'half_face_folder']:
    settings[folder] = os.path.join(settings['processed_pairs_folder'], settings[folder])
