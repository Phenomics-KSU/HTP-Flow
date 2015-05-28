#! /usr/bin/env python

import sys
import os
import argparse

# import the necessary things for OpenCV
import cv2 as cv
import numpy as np

from geo_image import GeoImage

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

def calculate_resolution(image_filename, camera_height, image_width_in_pixels, sensor_width, focal_length):

    # Avoid division by zero.
    if focal_length <= 0:
        return 0
        
    # The horizontal field of view (in same units as camera_height, which should be centimeters) 
    # can be found by simply using the ratio of focal length and sensor size.
    hfov = camera_height * (sensor_width / focal_length)
    
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
            os.makedirs(sub_directory)
                
        for i, item in enumerate(items):
            item_filename = "{0}_{1}.{2}".format(set_type, i, os.path.splitext(item.parent_filename)[1])
                
            cv.imwrite(item_filename, item.image)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Extract plants from images and assign to group using QR code.')
    parser.add_argument('image_directory', help='where to search for images to process')
    parser.add_argument('image_geo_file', help='file with position/heading data for each image.')
    parser.add_argument('output_directory', help='where to write output files')
    parser.add_argument('starting_row_number', help='Row number for starting images')
    parser.add_argument('row_skip_number', help='How many rows to skip when moving to next row')
    parser.add_argument('-qr', dest='qr_size', default=0, help='side length of QR item in centimeters. Must be > 0')
    parser.add_argument('-ch', dest='camera_height', default=0, help='camera height in centimeters. Must be > 0')
    parser.add_argument('-sw', dest='sensor_width', default=0, help='Sensor width in same units as focal length. Must be > 0')
    parser.add_argument('-fl', dest='focal_length', default=0, help='effective focal length in same units as sensor width. Must be > 0')

    args = parser.parse_args()
    
    image_directory = args.image_directory
    image_geo_file = args.image_geo_file
    out_directory = args.output_directory
    start_row_num = int(args.starting_row_number)
    row_skip_num = int(args.row_skip_number)
    qr_size = float(args.qr_size)
    camera_height = float(args.camera_height)
    sensor_width = float(args.sensor_width)
    focal_length = float(args.focal_length)
    
    if qr_size <= 0 or camera_height <= 0 or sensor_width <= 0 or focal_length <= 0:
        print "\nError: One or more arguments were not greater than zero.\n"
        parser.print_help()
        sys.exit(1)
        
    current_row_num = start_row_num
    
    image_filenames = []
    for fname in os.listdir(image_directory):
        if fname.endswith('.tiff') or fname.endswith('.tif') or fname.endswith('.jpg') or fname.endswith('.png'): 
            image_filenames.append(fname)
        else:
            print 'Skipping file {0} due to unsupported extension'.format(fname)
                        
    if len(image_filenames) == 0:
        print "No images found in directory: {0}".format(image_directory)
        sys.exit(1)
    
    print "\nFound {0} images to process".format(len(image_filenames))
    
    images = []
    with open(image_geo_file, 'r') as geofile:
        lines = geofile.readlines()
        for line in lines:
            if line.isspace():
                continue
            
            fields = [field.strip() for field in line.split(',')]
        
            if len(fields) == 0:
                continue

            try:
                image_name = fields[0]
                image_time = fields[1]
                x = fields[2]
                y = fields[3]
                z = fields[4]
                heading = fields[5]
            except IndexError:
                print 'Bad line: {0}'.format(line) 
                continue
            
            images.append(GeoImage(image_name, x, y, z, heading))
            
            
    print "Parsed {0} geo images".format(len(images))
    
    missing_image_count = 0
    for geo_image in images:
        if not geo_image.file_name in image_filenames:
            missing_image_count += 1
            
    if missing_image_count > 0:
        "Warning {0} geo images do not exist and will be skipped.".format(missing_image_count)

    need_to_start_new_row = True
    in_row = True
    
    for i, image in enumerate(images):
        
        if need_to_start_new_row:
            print "Starting row {0}".format(current_row_num)
            row_directory = "row{0}".format(current_row_num)
            row_directory = os.path.join(out_directory, row_directory)
            if not os.path.exists(row_directory):
                os.makedirs(row_directory)
            need_to_start_new_row = False
            in_row = False
        
        print "Analyzing image [{0}/{1}]".format(i+1, len(images))
        
        full_filename = os.path.join(image_directory, image.file_name)
        
        cv_image = cv.LoadImage(full_filename, cv.CV_LOAD_IMAGE_ANYDEPTH)
        
        resolution = calculate_resolution(full_filename, camera_height, cv_image.w, sensor_width, focal_length)
        
        if resolution <= 0:
            print "Cannot calculate image resolution."
            continue
        
        #i.    Extract possible QR codes, plants and blue sticks and assign X,Y,Z and row to each object.
        #ii.    Order objects sequentially from bottom to top.
        # iii.    Pass into Z-bar library to read QRs and remove and false positives.
        (marked_image, image_items) = extract_items(image, cv_image, resolution, qr_size)

        qr_names = [item.name for item in image_items if "code" in lower(item.type)] 
        
        if not in_row:
            if "start" in qr_names:
                # TODO update 'start' name to include row number
                in_row = True
                print 'Found start code'
            elif len(qr_names) > 0:
                # TODO make sure not seeing 'end' twice
                print "Warning! QR code found before start code."

        if "end" in qr_names:
            need_to_start_new_row = True

        # if 
        # vi.    If we’ve hit a start QR code keep adding heading to running average.  (also do check for robot turning)
        
        # vii.    Save marked up image to ‘row1/image-001’ and then create a directory with same name and store sub images in there ‘row1/image-001/plant-1’

    write_items(args.output_directory, items)
