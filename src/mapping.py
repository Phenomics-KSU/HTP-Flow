#! /usr/bin/env python

import sys
import os
import argparse

# OpenCV imports
import cv2 as cv
import numpy as np

# Project imports
from data import *
from item_extraction import *
from image_utils import *

if __name__ == '__main__':
    '''Extract plants from images and assign to group using QR code'''
    
    parser = argparse.ArgumentParser(description='Extract plants from images and assign to group using QR code.')
    parser.add_argument('image_directory', help='where to search for images to process')
    parser.add_argument('image_geo_file', help='file with position/heading data for each image.')
    parser.add_argument('output_directory', help='where to write output files')
    parser.add_argument('starting_row_number', help='Row number for starting images')
    parser.add_argument('row_skip_number', help='How many rows to skip when moving to next row')
    parser.add_argument('-qr', dest='qr_size', default=0, help='side length of QR item in centimeters. Must be > 0')
    parser.add_argument('-ps', dest='plant_size', default=0, help='Estimated plant size in centimeters. Must be > 0')
    parser.add_argument('-ch', dest='camera_height', default=0, help='camera height in centimeters. Must be > 0')
    parser.add_argument('-sw', dest='sensor_width', default=0, help='Sensor width in same units as focal length. Must be > 0')
    parser.add_argument('-fl', dest='focal_length', default=0, help='effective focal length in same units as sensor width. Must be > 0')
    parser.add_argument('-mk', dest='marked_image', default=False, help='If true then will output marked up image.  Default false.')
    parser.add_argument('-cr', dest='camera_rotation', default=0, help='Camera rotation (0, 90, 180, 270).  0 is camera top forward and increases counter-clockwise.' )
    parser.add_argument('-md', dest='max_distance', default=12, help='Maximum radius in centimeters to consider two items the same between multiple images.')

    args = parser.parse_args()
    
    # convert command line arguments
    image_directory = args.image_directory
    image_geo_file = args.image_geo_file
    out_directory = args.output_directory
    start_row_num = int(args.starting_row_number)
    row_skip_num = int(args.row_skip_number)
    qr_size = float(args.qr_size)
    plant_size = float(args.plant_size)
    camera_height = float(args.camera_height)
    sensor_width = float(args.sensor_width)
    focal_length = float(args.focal_length)
    use_marked_image = args.marked_image
    camera_rotation = int(args.camera_rotation)
    max_distance = float(args.max_distance)
    
    if qr_size <= 0 or plant_size <= 0 or camera_height <= 0 or sensor_width <= 0 or focal_length <= 0:
        print "\nError: One or more arguments were not greater than zero.\n"
        parser.print_help()
        sys.exit(1)
        
    possible_camera_rotations = [0, 90, 180, 270]
    if camera_rotation not in possible_camera_rotations:
        print "Error: Camera rotation {0} invalid.  Possible choices are {1}".format(camera_rotation, possible_camera_rotations)
        sys.exit(1)
        
    current_row_num = start_row_num
    
    image_filenames = read_images(image_directory, ['tiff', 'tif', 'jpg', 'jpeg', 'png'])
                        
    if len(image_filenames) == 0:
        print "No images found in directory: {0}".format(image_directory)
        sys.exit(1)
    
    print "\nFound {0} images to process".format(len(image_filenames))
    
    geo_images = parse_geo_file(image_geo_file, focal_length, camera_rotation, camera_height, sensor_width)
            
    print "Parsed {0} geo images".format(len(geo_images))
    
    print "Sorting images by timestamp."
    geo_images = sorted(geo_images, key=lambda image: image.image_time)
    
    missing_image_count = verify_geo_images(geo_images, image_filenames)
           
    if missing_image_count > 0:
        print "Warning {0} geo images do not exist and will be skipped.".format(missing_image_count)

    need_to_start_new_row = True
    in_row = True
    
    qr_locator = QRLocator(qr_size)
    plant_locator = PlantLocator(plant_size)
    item_extractor = ItemExtractor([qr_locator, plant_locator])
    
    ImageWriter.level = ImageWriter.DEBUG

    items = [] # All field items found in images.
    
    for i, geo_image in enumerate(geo_images):
        '''
        if need_to_start_new_row:
            print "Starting row {0}".format(current_row_num)
            row_directory = "row{0}".format(current_row_num)
            row_directory = os.path.join(out_directory, row_directory)
            if not os.path.exists(row_directory):
                os.makedirs(row_directory)
            need_to_start_new_row = False
            in_row = False
        '''
        print "Analyzing image [{0}/{1}]".format(i+1, len(geo_images))
        
        full_filename = os.path.join(image_directory, geo_image.file_name)
        
        image = cv.imread(full_filename, cv.CV_LOAD_IMAGE_COLOR)

        if image is None:
            print 'Cannot open image: {0}'.format(full_filename)
            continue

        # Update remaining geo image properties before doing image analysis.  This makes it so we only open image once.
        image_height, image_width, _ = image.shape
        geo_image.size = (image_width, image_height)
  
        if geo_image.resolution <= 0:
            print "Cannot calculate image resolution. Skipping image."
            continue
        
        # Specify 'image directory' so that if any images associated with current image are saved a directory is created.
        image_out_directory = os.path.join(out_directory, os.path.splitext(geo_image.file_name)[0])
        ImageWriter.output_directory = image_out_directory

        marked_image = None
        if use_marked_image:
            # Copy original image so we can mark on it for debugging.
            marked_image = image.copy()

        image_items = item_extractor.extract_items(geo_image, image, marked_image, image_out_directory)
        
        image_items = order_items(image_items, camera_rotation)
        
        print 'Found {0} items.'.format(len(image_items))
        for item in image_items:
            print "Type: {0} Name: {1}".format(item.item_type, item.name)

        items.extend(image_items)

        if marked_image is not None:
            marked_image_filename = postfix_filename(geo_image.file_name, '_marked')
            marked_image_path = os.path.join(out_directory, marked_image_filename)
            cv.imwrite(marked_image_path, marked_image)

    # Eliminate any duplicated items coming from multiple pictures.
    unique_items = []
    for item in items:
        matching_item = None
        for comparision_item in unique_items:
            if is_same_item(item, comparision_item, max_distance):
                matching_item = comparision_item
                break
        if matching_item is None:
            unique_items.append(item)

    print len(unique_items)
    for item in items:
        print item.name
        print item.position
