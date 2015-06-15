#! /usr/bin/env python

import sys
import os
import argparse
from collections import Counter

# OpenCV imports
import cv2 as cv
import numpy as np

# Project imports
from data import *
from item_extraction import *
from image_utils import *
from item_processing import *

if __name__ == '__main__':
    '''Extract plants from images and assign to group using QR code'''
    
    parser = argparse.ArgumentParser(description='Extract plants from images and assign to group using QR code.')
    parser.add_argument('image_directory', help='where to search for images to process')
    parser.add_argument('image_geo_file', help='file with position/heading data for each image.')
    parser.add_argument('group_info_file', help='file with group numbers and corresponding number of plants.')
    parser.add_argument('output_directory', help='where to write output files')
    parser.add_argument('starting_row_number', help='Row number for starting images')
    parser.add_argument('row_skip_number', help='How many rows to skip when moving to next row')
    parser.add_argument('-qr', dest='qr_size', default=0, help='side length of QR item in centimeters. Must be > 0')
    parser.add_argument('-minps', dest='min_plant_size', default=0, help='Minimum plant size in centimeters. Must be > 0')
    parser.add_argument('-maxps', dest='max_plant_size', default=0, help='Maximum plant size in centimeters. Must be > 0')
    parser.add_argument('-ch', dest='camera_height', default=0, help='camera height in centimeters. Must be > 0')
    parser.add_argument('-sw', dest='sensor_width', default=0, help='Sensor width in same units as focal length. Must be > 0')
    parser.add_argument('-fl', dest='focal_length', default=0, help='effective focal length in same units as sensor width. Must be > 0')
    parser.add_argument('-mk', dest='marked_image', default=False, help='If true then will output marked up image.  Default false.')
    parser.add_argument('-cr', dest='camera_rotation', default=0, help='Camera rotation (0, 90, 180, 270).  0 is camera top forward and increases counter-clockwise.' )
    parser.add_argument('-md', dest='max_distance', default=12, help='Maximum radius in centimeters to consider two items the same between multiple images.')
    parser.add_argument('-rs', dest='resolution', default=0, help='Calculated image resolution in centimeter/pixel.')

    args = parser.parse_args()
    
    # convert command line arguments
    image_directory = args.image_directory
    image_geo_file = args.image_geo_file
    group_info_file = args.group_info_file
    out_directory = args.output_directory
    start_row_num = int(args.starting_row_number)
    row_skip_num = int(args.row_skip_number)
    qr_size = float(args.qr_size)
    min_plant_size = float(args.min_plant_size)
    max_plant_size = float(args.max_plant_size)
    camera_height = float(args.camera_height)
    sensor_width = float(args.sensor_width)
    focal_length = float(args.focal_length)
    use_marked_image = args.marked_image
    camera_rotation = int(args.camera_rotation)
    max_distance = float(args.max_distance)
    provided_resolution = float(args.resolution)
    
    if qr_size <= 0 or min_plant_size <= 0 or max_plant_size <= 0:
        print "\nError: One or more arguments were not greater than zero.\n"
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
        
    current_row_num = start_row_num
    
    image_filenames = read_images(image_directory, ['tiff', 'tif', 'jpg', 'jpeg', 'png'])
                        
    if len(image_filenames) == 0:
        print "No images found in directory: {0}".format(image_directory)
        sys.exit(1)
    
    print "\nFound {0} images to process".format(len(image_filenames))
    
    geo_images = parse_geo_file(image_geo_file, provided_resolution, focal_length, camera_rotation, camera_height, sensor_width)
            
    print "Parsed {0} geo images".format(len(geo_images))
    
    grouping_info = parse_grouping_file(group_info_file)
    
    print "Parsed {0} groups. ".format(len(grouping_info))
    
    grouping_info_names = [g[0] for g in grouping_info]
    for name, count in Counter(grouping_info_names).most_common():
        if count > 1:
            print "ERROR: found {} groups named {} in {}".format(count, name, group_info_file)
            sys.exit(1)
        
    print "Sorting images by timestamp."
    geo_images = sorted(geo_images, key=lambda image: image.image_time)
    
    missing_image_count = verify_geo_images(geo_images, image_filenames)
           
    if missing_image_count > 0:
        print "Warning {0} geo images do not exist and will be skipped.".format(missing_image_count)

    need_to_start_new_row = True
    in_row = True
    
    qr_locator = QRLocator(qr_size)
    plant_locator = PlantLocator(min_plant_size, max_plant_size)
    item_extractor = ItemExtractor([qr_locator, plant_locator])
    
    ImageWriter.level = ImageWriter.DEBUG

    # Extract all field items from images.
    items = process_geo_images(geo_images, item_extractor, camera_rotation, image_directory, out_directory, use_marked_image)
            
    # Merge duplicated items coming from multiple pictures so that first references the others.
    print "Merging items."
    items = merge_items(items, max_distance)

    # Sort items into row groupings
    rows, current_row, outside_row_plants = group_into_rows(items)

    if len(outside_row_plants) > 0:
        print "Detected {0} plants outside of rows.".format(len(outside_row_plants))

    if current_row is not None:
        print "Ended in middle of row {0}.  It will not be processed. Row start image {1}".format(current_row.number, current_row.start_code.file_name)

    plant_groups = split_into_plant_groupings(rows)
                    
    #plant_groups = correct_plant_groupings(plant_groups, grouping_info)
        
    # Write everything out to CSV file to be imported into database.

    print len(items)
    for item in items:
        print item.name
        print item.position
        for other_item in item.other_items:
            print "\t{0}".format(other_item.position)
        if len(item.other_items) > 0:
            item_references = [item] + item.other_items
            average_x = np.mean([item.position[0] for item in item_references])
            average_y = np.mean([item.position[1] for item in item_references])
            average_z = np.mean([item.position[2] for item in item_references])
            distances = [position_difference(item_ref.position, (average_x, average_y)) for item_ref in item_references]
            print "\tAvg: {0} Max: {1}".format(np.mean(distances), np.max(distances)) 
        
                

