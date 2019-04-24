# Environment Setup
import os
import shutil

from settings import settings


def main():
    os.makedirs(settings['train_data_folder'], exist_ok=True)
    products_folder = os.path.join(settings['train_data_folder'], 'products')
    reviews_folder = os.path.join(settings['train_data_folder'], 'reviews')
    os.makedirs(products_folder, exist_ok=True)
    os.makedirs(reviews_folder, exist_ok=True)

    csv_path = os.path.join(settings['train_data_folder'], 'train_pairs.csv')
    myfile = open(csv_path, "w")
    myfile.write(','.join(['review', 'product', 'asin', 'review_i'])+'\n')

    txt_path = os.path.join(settings['train_data_folder'], 'train_pairs.txt')
    txtfile = open(txt_path, "w")

    pairs_list = os.listdir(settings['filtered_pairs_folder'])
    for i, pair in enumerate(pairs_list):
        print('\r%i/%i Preparing pair %s         ' % (i+1, len(pairs_list), pair), end='')
        asin = os.path.splitext(pair)[0].split('_')[0]
        review_i = os.path.splitext(pair)[0].split('_')[1]
        review_path = os.path.join(settings['data_folder'], asin)
        product_filename = '%s_1.jpg' % str(i).zfill(5)
        review_filename = '%s_0.jpg' % str(i).zfill(5)

        if os.path.exists(review_path):
            shutil.copy2(os.path.join(review_path, 'product.jpg'),
                         os.path.join(products_folder, product_filename))
            shutil.copy2(os.path.join(review_path, '_%s.jpg' % review_i),
                         os.path.join(reviews_folder, review_filename))
            myfile.write(','.join([review_filename, product_filename, asin, str(review_i)])+'\n')
            txtfile.write('%s %s\n' % (review_filename, product_filename))
        else:
            print('ERROR: Cannot find %s' % review_path)

    print('\nDone.')
    myfile.close()
    txtfile.close()


if __name__ == '__main__':
    main()
