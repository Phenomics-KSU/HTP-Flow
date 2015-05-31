#! /usr/bin/env python

import sys
import os
import argparse

# import the necessary things for OpenCV
import cv2 as cv
import numpy as np

from data import *
from item_extraction import *

    
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
    parser.add_argument('-mk', dest='marked_image', default=False, help='If true then will output marked up image.  Default false.')

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
    use_marked_image = args.marked_image
    
    if qr_size <= 0 or camera_height <= 0 or sensor_width <= 0 or focal_length <= 0:
        print "\nError: One or more arguments were not greater than zero.\n"
        parser.print_help()
        sys.exit(1)
        
    current_row_num = start_row_num
    
    image_filenames = []
    for fname in os.listdir(image_directory):
        extension = os.path.splitext(fname)[1][1:]
        if extension.lower() in ['tiff', 'tif', 'jpg', 'jpeg', 'png']:
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
                x, y, z = fields[2 : 5]
                heading = fields[5]
                # Make sure filename doesn't have extension, we'll add it from image that we're processing.
                image_name = os.path.splitext(image_name)[0]
            except IndexError:
                print 'Bad line: {0}'.format(line) 
                continue

            geo_image = GeoImage(image_name, (x, y, z), heading, focal_length, camera_height, sensor_width)
            images.append(geo_image)
            
            
    print "Parsed {0} geo images".format(len(images))
    
    missing_image_count = 0
    for geo_image in images:
        image_filenames_no_ext = [os.path.splitext(fname)[0] for fname in image_filenames]
        try:
            # Make sure actual image exists and use it's file extension.
            index = image_filenames_no_ext.index(geo_image.file_name)
            extension = os.path.splitext(image_filenames[index])[1][1:]
            geo_image.file_name = "{0}.{1}".format(geo_image.file_name, extension)
        except ValueError:
            # Geo image doesn't have corresponding actual image
            missing_image_count += 1
           
    if missing_image_count > 0:
        print "Warning {0} geo images do not exist and will be skipped.".format(missing_image_count)

    need_to_start_new_row = True
    in_row = True
    
    qr_locator = QRLocator(qr_size)
    item_extractor = ItemExtractor([qr_locator])
    
    for i, geo_image in enumerate(images):
        
        if need_to_start_new_row:
            print "Starting row {0}".format(current_row_num)
            row_directory = "row{0}".format(current_row_num)
            row_directory = os.path.join(out_directory, row_directory)
            if not os.path.exists(row_directory):
                os.makedirs(row_directory)
            need_to_start_new_row = False
            in_row = False
        
        print "Analyzing image [{0}/{1}]".format(i+1, len(images))
        
        full_filename = os.path.join(image_directory, geo_image.file_name)
        
        image = cv.imread(full_filename, cv.CV_LOAD_IMAGE_UNCHANGED)

        if image is None:
            print 'Cannot open image: {0}'.format(full_filename)
            continue

        # Update remaining geo image properties before doing image analysis.  This makes it so we only open image once.
        geo_image.image_width_in_pixels = image.shape[1]
  
        if geo_image.resolution <= 0:
            print "Cannot calculate image resolution. Skipping image."
            continue
        
        # Create output directory for each image so we can store things we find there.
        image_out_directory = os.path.join(row_directory, os.path.splitext(geo_image.file_name)[0])
        if not os.path.exists(image_out_directory):
                os.makedirs(image_out_directory)

        marked_image = None
        if use_marked_image:
            # Copy original image so we can mark on it for debugging.
            marked_image = image.copy()

        items = item_extractor.extract_items(geo_image, image, marked_image, image_out_directory)
        
        print 'Found {0} items.'.format(len(items))
        for item in items:
            print item

        if marked_image is not None:
            filename, extension = os.path.splitext(geo_image.file_name)
            marked_image_filename = "{0}_marked{1}".format(filename, extension)
            marked_image_path = os.path.join(row_directory, marked_image_filename)
            cv.imwrite(marked_image_path, marked_image)

        continue
        
        qr_names = [item.name for item in image_items if "code" in item.type.lower()] 
        
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
