#! /usr/bin/env python

import sys
import os
import argparse

# import the necessary things for OpenCV
import cv2 as cv
import numpy as np

class ImageItem:

    # Types of different image items.
    types = dict( 
                  qr = dict(index=0, group_name='QR_Items'),
    )
    
    def __init__(self, item_type, extracted_image, parent_filename, coordinates):
        _type = item_type
        _image = extracted_image
        _parent_filename = parent_filename
        _coordinates = coordinates

def locate_qr_items(image, image_filename, resolution, qr_size):

    # Grayscale original image so we can find edges in it. Default for OpenCV is BGR not RGB.
    gray_image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)

    # Need to blur image before running edge detector to avoid a bunch of small edges due to noise.
    blurred_image = cv.GaussianBlur(gray_image, (5,5), 0)
    
    # Canny will output a binary image where white = edges and black = background.
    edge_image = cv.Canny(blurred_image, 100, 200)
    
    # Find contours (edges) and 'approximate' them to reduce the number of points along nearly straight segments.
    storage = cv.CreateMemStorage (0)
    contours = cv.FindContours(edge_image, storage, cv.CV_RETR_TREE, cv.CV_CHAIN_APPROX_SIMPLE, (0,0))
    contours = cv.approxPolyDP(contours, storage, cv.CV_POLY_APPROX_DP, 3, 1)
    
    # Create rotated bounding rectangle for each contour.
    bounding_rectangles = [cv.minAreaRect(contour) for contour in contours]
    
    # Remove any rectangles that couldn't be a QR item based off specified side length.
    filtered_rectangles = filter_by_size(bounding_rectangles, resolution, qr_size)
    
    qr_items = []
    
    # Convert remaining bounding rectangles into image items.
    for filtered_rectangle in filtered_rectangles:
        extracted_image = extract_image(filtered_rectangle, padding, image)
        
        coordinates = (0, 0)
        
        image_type = ImageItem.types['qr']
        
        qr_items.append(image_type, extracted_image, image_filename, coordinates)
        
    return qr_items

def search_images_for_items(input_directory, find_qr_items, qr_size):

    image_filenames = []
    for fname in os.listdir(input_directory):
        if fname.endswith('.tiff') or fname.endswith('.tif') or fname.endswith('.jpg') or fname.endswith('.png'): 
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
        
        resolution = calculate_resolution(full_filename, 15000) # TODO specify altitude
        
        if resolution <= 0:
            print "Cannot calculate resolution of image. Make sure camera model is defined."
            continue
        
        image = cv.LoadImage(full_filename, cv.CV_LOAD_IMAGE_ANYDEPTH)
        
        if find_qr_items:
            qr_items = locate_qr_items(image, filename, resolution, qr_size)
            all_qr_items.extend(qr_items)
            print "Found {0} QR items".format(len(qr_items))
            
    return [all_qr_items]    

def calculate_resolution(image_filename, altitude):
    
    # Pull out focal length and image width from metadata.
    focal_length = 5
    image_width_in_pixels = 4000
    
    # Focal lengths are usually specified in 'mm' but for some reason some cameras multiply
    # this by 1000.  So 5mm = 5000.  Since there shouldn't be a real focal length longer than
    # a 1 meter. Therefore we need to scale down any large focal lengths by a factor of 1000.
    if focal_length >= 1000:
        focal_length /= 1000
        
    # Sensor width in millimeters (same as focal length).  TODO: let user specify this somewhere.
    sensor_width = 7.6
    
    # Avoid division by zero.
    if focal_length <= 0:
        return 0
        
    # The horizontal field of view (in same units as altitude, which should be centimeters) 
    # can be found by simply using the ratio of focal length and sensor size.
    hfov = altitude * (sensor_width / focal_length)
    
    # Avoid division by zero.
    if image_width_in_pixels == 0:
        return 0
    
    return hfov / image_width_in_pixels  # cm per pixel

def extract_image(rectangle, pad, image):
    
    # reference properties of rotated bounding rectangle
    x = rectangle[0].x
    y = rectangle[0].y
    w = rectangle[1].w
    h = rectangle[1].h
    
    # add in pad to rectangle and respect image boundaries
    top = max(1, y - pad)
    bottom = min(image.h - 1, y + h + pad)
    left = max(1, x - pad)
    right = min(image.w - 1, x + w + pad)
    
    return image[top:bottom, left:right]
    
def write_items(output_directory, items_list):
    
    for items in items_list:

        if len(items) == 0: continue
        
        set_type = items.type['group_name']
        
        sub_directory = os.path.join(output_directory, set_type)
        
        if not os.path.exists(sub_directory):
            os.path.makedirs(sub_directory)
                
        for i, item in enumerate(items):
            item_filename = "{0}_{1}.{2}".format(set_type, i, os.path.splitext(item.parent_filename)[1])
                
            cv.imwrite(item_filename, item.image)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Extract specified items from a set of aerial images.')
    parser.add_argument('input_directory', help='where to search for images to process')
    parser.add_argument('output_directory', help='where to write output files')
    parser.add_argument('-qr', dest='qr_size', default=0, help='side length of QR item in centimeters. Must be > 0')

    args = parser.parse_args()
    
    qr_size = float(args.qr_size)
    
    find_qr = qr_size > 0
    
    if not find_qr:
        print "\nError: must specify at least one type of item to extract.\n"
        parser.print_help()
        sys.exit(1)
        
    items = search_images_for_items(args.input_directory, find_qr, qr_size)
    
    write_items(args.output_directory, items)
