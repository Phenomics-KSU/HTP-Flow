#! /usr/bin/env python

import sys
import os
import argparse

# import the necessary things for OpenCV
import cv2.cv as cv

# definition of some colors
_red =  (0, 0, 255, 0);
_green =  (0, 255, 0, 0);
_white = cv.RealScalar (255)
_black = cv.RealScalar (0)

class ImageItem:

    # Types of different image items.
    _QR_ITEM = 0;
    
    def __init__(self, item_type, extracted_image, parent_filename, coordinates):
        _type = item_type
        _image = extracted_image
        _parent_filename = parent_filename
        _coordinates = coordinates

def locate_qr_items(image, image_filename, resolution, qr_size):

    # grayscale

    # gaussian blur
    
    # canny
    
    # iterate contours and draw rotated bounding boxes for each one
    
    # check if width and height are within threshold of qr size
    
    # if they are then extract image and coordinates and create a new image item instance

    return [] # list of image items

def search_images_for_items(input_directory, find_qr_items, qr_size):

    image_filenames = []
    for fname in os.listdir(input_directory):
        if fname.endswith('.tiff') or fname.endswith('.tif') or fname.endswith('.jpg') or fname.endswith('png'): 
            image_filenames.append(fname)
            
    if len(image_filenames) == 0:
        print "No images found in directory: {0}".format(input_directory)
        return []
    
    print "\nPreparing to search {0} images for:".format(len(image_filenames))
    if find_qr_items: 
        print "QR items with side length of {0} centimeters".format(qr_size)
    print ""
    
    all_qr_items = []
    
    for i, filename in enumerate(image_filenames):
        print "Searching image [{0}/{1}]".format(i+1, len(image_filenames))
        
        full_filename = os.path.join(input_directory, filename)
        
        resolution = calculate_resolution(full_filename);
        
        if resolution <= 0:
            print "Cannot calculate resolution of image. Make sure camera model is defined."
            continue
        
        image = cv.LoadImage(full_filename, cv.CV_LOAD_IMAGE_COLOR)
        
        if find_qr_items:
            qr_items = locate_qr_items(image, filename, resolution, qr_size)
            all_qr_items.extend(qr_items)
            print "Found {0} QR items".format(len(qr_items))
            
    return [all_qr_items]    

def calculate_resolution(filename):


    
def write_items(output_directory, items):  
    
    return
    
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Extract specified items from a set of aerial images.')
    parser.add_argument('input_directory', help='where to search for images to process')
    parser.add_argument('output_directory', help='where to write output files')
    parser.add_argument('-qr', dest='qr_size', default=0, help='side length of QR item in centimeters. Must be > 0')

    args = parser.parse_args()
    
    qr_size = float(args.qr_size);
    
    find_qr = qr_size > 0
    
    if not find_qr:
        print "\nError: must specify at least one type of item to extract.\n"
        parser.print_help()
        sys.exit(1)
        
    items = search_images_for_items(args.input_directory, find_qr, qr_size)
    
    write_items(args.output_directory, items)
    
    '''
# the callback on the trackbar, to set the level of contours we want
# to display
def on_trackbar (position):

    # create the image for putting in it the founded contours
    contours_image = cv.CreateImage ( (_SIZE, _SIZE), 8, 3)

    # compute the real level of display, given the current position
    levels = position - 3

    # initialisation
    _contours = contours

    if levels <= 0:
        # zero or negative value
        # => get to the nearest face to make it look more funny
        _contours = contours.h_next().h_next().h_next()

    # first, clear the image where we will draw contours
    cv.SetZero (contours_image)

    # draw contours in red and green
    cv.DrawContours (contours_image, _contours,
                       _red, _green,
                       levels, 3, cv.CV_AA,
                        (0, 0))

    # finally, show the image
    cv.ShowImage ("contours", contours_image)

if __name__ == '__main__':

    # create the image where we want to display results
    image = cv.CreateImage ( (_SIZE, _SIZE), 8, 1)

    # start with an empty image
    cv.SetZero (image)

    # draw the original picture
    for i in range (6):
        dx = (i % 2) * 250 - 30
        dy = (i / 2) * 150

        cv.Ellipse (image,
                       (dx + 150, dy + 100),
                       (100, 70),
                      0, 0, 360, _white, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 115, dy + 70),
                       (30, 20),
                      0, 0, 360, _black, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 185, dy + 70),
                       (30, 20),
                      0, 0, 360, _black, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 115, dy + 70),
                       (15, 15),
                      0, 0, 360, _white, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 185, dy + 70),
                       (15, 15),
                      0, 0, 360, _white, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 115, dy + 70),
                       (5, 5),
                      0, 0, 360, _black, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 185, dy + 70),
                       (5, 5),
                      0, 0, 360, _black, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 150, dy + 100),
                       (10, 5),
                      0, 0, 360, _black, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 150, dy + 150),
                       (40, 10),
                      0, 0, 360, _black, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 27, dy + 100),
                       (20, 35),
                      0, 0, 360, _white, -1, 8, 0)
        cv.Ellipse (image,
                       (dx + 273, dy + 100),
                       (20, 35),
                      0, 0, 360, _white, -1, 8, 0)

    # create window and display the original picture in it
    cv.NamedWindow ("image", 1)
    cv.ShowImage ("image", image)

    # create the storage area
    storage = cv.CreateMemStorage (0)

    # find the contours
    contours = cv.FindContours(image,
                               storage,
                               cv.CV_RETR_TREE,
                               cv.CV_CHAIN_APPROX_SIMPLE,
                               (0,0))

    # comment this out if you do not want approximation
    contours = cv.ApproxPoly (contours,
                                storage,
                                cv.CV_POLY_APPROX_DP, 3, 1)

    # create the window for the contours
    cv.NamedWindow ("contours", 1)

    # create the trackbar, to enable the change of the displayed level
    cv.CreateTrackbar ("levels+3", "contours", 3, 7, on_trackbar)

    # call one time the callback, so we will have the 1st display done
    on_trackbar (_DEFAULT_LEVEL)

    # wait a key pressed to end
    cv.WaitKey (0)
    cv.DestroyAllWindows()
'''