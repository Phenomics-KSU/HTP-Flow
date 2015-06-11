#! /usr/bin/env python

import sys
import os

# OpenCV imports
import cv2 as cv

# Project imports
from data import *

class ImageWriter:
    '''Facilitate writing output images to an output directory.'''
    DEBUG = 0
    NORMAL = 1
    
    level = DEBUG
    output_directory = './'

    @staticmethod
    def save_debug(filename, image):
        return ImageWriter.save(filename, image, ImageWriter.DEBUG)

    @staticmethod
    def save_normal(filename, image):
        return ImageWriter.save(filename, image, ImageWriter.NORMAL)

    @staticmethod
    def save(filename, image, level):
        '''Save image if the specified level is above current output level.'''
        if level < ImageWriter.level:
            return

        filepath = os.path.join(ImageWriter.output_directory, filename)
        if not os.path.exists(os.path.dirname(filepath)):
            os.makedirs(os.path.dirname(filepath))
            
        cv.imwrite(filepath, image)
        
        return filepath

def postfix_filename(filename, postfix):
    '''Return post-fixed file name with original extension.'''
    filename, extension = os.path.splitext(filename)
    postfixed_name = "{0}{1}{2}".format(filename, postfix, extension)
    return postfixed_name

def read_images(image_directory, extensions):
    '''Return list of images with specified extensions inside of directory.'''
    image_filenames = []
    for fname in os.listdir(image_directory):
        extension = os.path.splitext(fname)[1][1:]
        if extension.lower() in extensions:
            image_filenames.append(fname)
        else:
            print 'Skipping file {0} due to unsupported extension'.format(fname)
    return image_filenames
    
def parse_geo_file(image_geo_file, focal_length, camera_rotation, camera_height, sensor_width):
    '''Parse geo file and return list of GeoImage instances.'''
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
                image_time = float(fields[0])
                image_name = fields[1]
                x = float(fields[2])
                y = float(fields[3])
                z = float(fields[4])
                roll = float(fields[5])
                pitch = float(fields[6])
                heading = float(fields[7])
                # Make sure filename doesn't have extension, we'll add it from image that we're processing.
                image_name = os.path.splitext(image_name)[0]
            except (IndexError, ValueError):
                print 'Bad line: {0}'.format(line) 
                continue

            geo_image = GeoImage(image_name, image_time, (x, y, z), heading, focal_length, camera_rotation, camera_height, sensor_width)
            images.append(geo_image)
            
    return images

def verify_geo_images(geo_images, image_filenames):
    '''Verify each geo image exists in specified image file names. Return # missing images.'''
    missing_image_count = 0
    for geo_image in geo_images:
        image_filenames_no_ext = [os.path.splitext(fname)[0] for fname in image_filenames]
        try:
            # Make sure actual image exists and use it's file extension.
            index = image_filenames_no_ext.index(geo_image.file_name)
            extension = os.path.splitext(image_filenames[index])[1][1:]
            geo_image.file_name = "{0}.{1}".format(geo_image.file_name, extension)
        except ValueError:
            # Geo image doesn't have corresponding actual image
            missing_image_count += 1
            
    return missing_image_count

def rectangle_center(rectangle):
    '''Returns (x,y) tuple of center of rectangle.'''
    x, y, w, h = rectangle
    return (x + w/2, y + h/2)
