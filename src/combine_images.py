# Environment Setup
import re
import os

from settings import settings
from PIL import Image


def append_images(images_fn, images_path, direction='horizontal', bg_color=(255, 255, 255), aligment='center'):
    """
    Appends images in horizontal/vertical direction.

    Args:
        images: List of PIL images
        direction: direction of concatenation, 'horizontal' or 'vertical'
        bg_color: Background color (default: white)
        aligment: alignment mode if images need padding;
           'left', 'right', 'top', 'bottom', or 'center'

    Returns:
        Concatenated image as a new PIL image object.
    """
    images = [Image.open(os.path.join(images_path, img_fn)) for img_fn in images_fn]

    widths, heights = zip(*(i.size for i in images))

    if direction == 'horizontal':
        new_width = sum(widths)
        new_height = max(heights)
    else:
        new_width = max(widths)
        new_height = sum(heights)

    new_im = Image.new('RGB', (new_width, new_height), color=bg_color)

    offset = 0
    for im in images:
        if direction == 'horizontal':
            y = 0
            if aligment == 'center':
                y = int((new_height - im.size[1])/2)
            elif aligment == 'bottom':
                y = new_height - im.size[1]
            new_im.paste(im, (offset, y))
            offset += im.size[0]
        else:
            x = 0
            if aligment == 'center':
                x = int((new_width - im.size[0])/2)
            elif aligment == 'right':
                x = new_width - im.size[0]
            new_im.paste(im, (x, offset))
            offset += im.size[1]

    return new_im


def main():
    os.makedirs(settings['processed_pairs_folder'], exist_ok=True)

    asins_list = os.listdir(settings['data_folder'])
    for asin_i, asin in enumerate(asins_list):
        print('\r%i/%i Joining images on %s         ' % (asin_i+1, len(asins_list), asin), end='')
        review_path = os.path.join(settings['data_folder'], asin)
        try:
            os.listdir(review_path)
        except NotADirectoryError:
            continue
        for review in os.listdir(review_path):
            if review != 'product.jpg':
                new_img = append_images(images_fn=['product.jpg', review], images_path=review_path)
                if settings['resize_width'] != 0:  # 0 means no resizing
                    new_img = new_img.resize((settings['resize_width'], int(settings['resize_width'] * new_img.height / new_img.width)))
                review_i = re.sub("[^0-9]", "", review)  # remove all non-digits
                new_img.save(os.path.join(settings['processed_pairs_folder'], '%s_%s.%s' % (asin, review_i, settings['processed_fileformat'])))

    print('\nDone.')


if __name__ == '__main__':
    main()
