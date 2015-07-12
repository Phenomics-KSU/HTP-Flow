#! /usr/bin/env python

import sys
import os
import argparse
from collections import Counter
import copy
import pickle

# OpenCV imports
import cv2
import numpy as np

# Project imports
from data import *
from item_extraction import *
from image_utils import *
from item_processing import *

if __name__ == '__main__':
    '''Extract codes from images.'''

    parser = argparse.ArgumentParser(description='''Extract codes from images''')
    parser.add_argument('image_directory', help='where to search for images to process')
    parser.add_argument('image_geo_file', help='file with position/heading data for each image.')
    parser.add_argument('output_directory', help='where to write output files')
    parser.add_argument('-qr', dest='qr_size', default=2.54, help='side length of QR item in centimeters. Must be > 0')
    parser.add_argument('-rs', dest='resolution', default=0, help='Calculated image resolution in centimeter/pixel.')
    parser.add_argument('-ch', dest='camera_height', default=0, help='camera height in centimeters. Must be > 0')
    parser.add_argument('-sw', dest='sensor_width', default=0, help='Sensor width in same units as focal length. Must be > 0')
    parser.add_argument('-fl', dest='focal_length', default=0, help='effective focal length in same units as sensor width. Must be > 0')
    parser.add_argument('-mk', dest='marked_image', default=False, help='If true then will output marked up image.  Default false.')
    parser.add_argument('-cr', dest='camera_rotation', default=0, help='Camera rotation (0, 90, 180, 270).  0 is camera top forward and increases counter-clockwise.' )
    parser.add_argument('-debug_start', dest='debug_start', default='__none__', help='Substring in image name to start processing at.')
    parser.add_argument('-debug_stop', dest='debug_stop', default='__none__', help='Substring in image name to stop processing at.')
    
    args = parser.parse_args()
    
    # convert command line arguments
    image_directory = args.image_directory
    image_geo_file = args.image_geo_file
    out_directory = args.output_directory
    qr_size = float(args.qr_size)
    provided_resolution = float(args.resolution)
    camera_height = float(args.camera_height)
    sensor_width = float(args.sensor_width)
    focal_length = float(args.focal_length)
    use_marked_image = args.marked_image
    camera_rotation = int(args.camera_rotation)
    debug_start = args.debug_start
    debug_stop = args.debug_stop
    
    if qr_size <= 0:
        print "\nError: QR code must be greater than zero.\n"
        parser.print_help()
        sys.exit(1)
    
    if provided_resolution <= 0 and (camera_height <= 0 or sensor_width <= 0 or focal_length <= 0):
        print "\nError: Resolution not provided so camera height, sensor width and focal length must be non-zero."
        parser.print_help()
        sys.exit(1)
        
    possible_camera_rotations = [0, 90, 180, 270]
    if camera_rotation not in possible_camera_rotations:
        print "Error: Camera rotation {0} invalid.  Possible choices are {1}".format(camera_rotation, possible_camera_rotations)
        sys.exit(1)
        
    image_filenames = read_images(image_directory, ['tiff', 'tif', 'jpg', 'jpeg', 'png'])
                        
    if len(image_filenames) == 0:
        print "No images found in directory: {0}".format(image_directory)
        sys.exit(1)
    
    print "\nFound {0} images to process".format(len(image_filenames))
    
    geo_images = parse_geo_file(image_geo_file, provided_resolution, focal_length, camera_rotation, camera_height, sensor_width)
            
    print "Parsed {0} geo images".format(len(geo_images))
    
    if len(geo_images) == 0:
        print "No geo images. Exiting."
        sys.exit(1)
    
    geo_image_filenames = [g.file_name for g in geo_images]
    start_geo_index = index_containing_substring(geo_image_filenames, debug_start)
    if start_geo_index < 0:
        start_geo_index = 0
    stop_geo_index = index_containing_substring(geo_image_filenames, debug_stop)
    if stop_geo_index < 0:
        stop_geo_index = len(geo_images) - 1
        
    print "Processing geo images {} through {}".format(start_geo_index, stop_geo_index)
    geo_images = geo_images[start_geo_index+1 : stop_geo_index+1]
        
    print "Sorting images by timestamp."
    geo_images = sorted(geo_images, key=lambda image: image.image_time)
    
    geo_images, missing_image_count = verify_geo_images(geo_images, image_filenames)
           
    if missing_image_count > 0:
        print "Warning {0} geo images do not exist and will be skipped.".format(missing_image_count)

    qr_locator = QRLocator(qr_size)
    item_extractor = ItemExtractor([qr_locator])
    
    ImageWriter.level = ImageWriter.DEBUG

    # Extract all QR items from images.
    for i, geo_image in enumerate(geo_images):
            print "Analyzing image {0} [{1}/{2}]".format(geo_image.file_name, i+1, len(geo_images))
            geo_image.items = process_geo_image(geo_image, item_extractor, camera_rotation, image_directory, out_directory, use_marked_image)
            for code in geo_image.items:
                print "Found code: {}".format(code.name)
  
    dump_filename = "stage1_geoimages_{}.txt".format(int(geo_images[0].image_time))
    dump_filepath = os.path.join(out_directory, dump_filename)
    print "Serializing {} geo images to {}.".format(len(geo_images), dump_filepath)
    with open(dump_filepath, 'wb') as dump_file:
        pickle.dump(geo_images, dump_file)

    # Display QR code stats for user.
    all_codes = all_items(geo_images)
    merged_codes = merge_items(all_codes, max_distance=100)
    if len(merged_codes) == 0:
        print "No codes found."
    else:
        print "There were {} codes found and {} were unique.  Average code is in {} images.".format(len(all_codes), len(merged_codes), float(len(all_codes)) / len(merged_codes))
        print "Merged codes not being saved.  Just for user information."
