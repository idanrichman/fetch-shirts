#%%
import cv2
import os
import numpy as np
import shutil
import glob

from settings import settings

#%%
# load cascade classifier training file for haarcascade
haar_face_cascade = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_alt.xml'))

#%%
def convertToRGB(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

def is_face_exists(filepath):
    #load iamge
    img = cv2.imread(filepath)
    #convert the test image to gray image as opencv face detector expects gray images
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #let's detect multiscale (some images may be closer to camera than others) images
    faces = haar_face_cascade.detectMultiScale(gray_img, minNeighbors=10);

    return len(faces) > 0

def is_half_face_exists(filepath):
    """ checks if first row is the same (white usually). if so then its probably not a face cut in half in the margin"""
    img = cv2.imread(filepath)
    first_row = img[0,:,:].reshape(-1)
    last_row = img[-1,:,:].reshape(-1)
    return (len(np.unique(first_row)) > 1) & (len(np.unique(last_row)) > 1)

#%%
def main():
    # Iterates over the files in the search_results folder
    results = []
    images_paths = glob.glob(os.path.join(settings['search_results_folder'], '*.jpg'))
    for i, filepath in enumerate(images_paths):
        print('\r%i/%i analyzing file %s         ' % (i+1, len(images_paths), filepath), end='')
        is_face = is_face_exists(filepath)
        is_half_face = is_half_face_exists(filepath)
        results.append((filepath, 1 if is_face else 0, 1 if is_half_face else 0))

    print()
    os.makedirs(settings['faces_folder'], exist_ok=True)
    os.makedirs(settings['half_face_folder'], exist_ok=True)

    face_count = 0
    half_face_count = 0
    for i, (filepath, is_face, is_half_face) in enumerate(results):
        print('\r%i/%i screening file %s         ' % (i+1, len(results), filepath), end='')
        if is_face:
            shutil.move(filepath, settings['faces_folder'])
            face_count += 1
        elif is_half_face:
            shutil.move(filepath, settings['half_face_folder'])
            half_face_count += 1

    valid_count = len(results) - face_count - half_face_count
    print('\nDone. valid: %i, faces: %i, half-faces: %i' % (valid_count, face_count, half_face_count))

#%%
if __name__ == '__main__':
    main()
