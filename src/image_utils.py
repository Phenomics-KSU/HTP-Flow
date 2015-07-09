#! /usr/bin/env python

import sys
import os
import math

# OpenCV imports
import cv2 as cv

# Project imports
from data import *

class ImageWriter(object):
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
    
def parse_geo_file(image_geo_file, provided_resolution, focal_length, camera_rotation, camera_height, sensor_width):
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
                heading = math.degrees(float(fields[7]))
                # Make sure filename doesn't have extension, we'll add it from image that we're processing.
                image_name = os.path.splitext(image_name)[0]
            except (IndexError, ValueError):
                print 'Bad line: {0}'.format(line) 
                continue

            geo_image = GeoImage(image_name, image_time, (x, y, z), heading, provided_resolution, focal_length, camera_rotation, camera_height, sensor_width)
            images.append(geo_image)
            
    return images

def parse_grouping_file(group_filename):
    '''Parse file and return list of tuples (group_name, number_plants) for each row.'''
    groups = []
    with open(group_filename, 'r') as group_file:
        lines = group_file.readlines()
        for line in lines:
            if line.isspace():
                continue
            fields = [field.strip() for field in line.split(',')]
            if len(fields) == 0:
                continue
            try:
                order_entered = fields[0]
                qr_id = fields[1]
                flag = fields[2] # just entry x rep combined
                entry = fields[3]
                rep = fields[4]
                estimated_num_plants = int(fields[5])
                groups.append((qr_id, entry, rep, estimated_num_plants))
            except (IndexError, ValueError):
                print 'Bad line: {0}'.format(line) 
                continue
            
    return groups

def verify_geo_images(geo_images, image_filenames):
    '''Verify each geo image exists in specified image file names. Return # missing images.'''
    missing_image_count = 0
    matching_geo_images = []
    image_filenames_no_ext = [os.path.splitext(fname)[0] for fname in image_filenames]
    for geo_image in geo_images:
        try:
            # Make sure actual image exists and use it's file extension.
            index = image_filenames_no_ext.index(geo_image.file_name)
            extension = os.path.splitext(image_filenames[index])[1][1:]
            geo_image.file_name = "{0}.{1}".format(geo_image.file_name, extension)
            matching_geo_images.append(geo_image)
        except ValueError:
            # Geo image doesn't have corresponding actual image
            missing_image_count += 1
            
    return matching_geo_images, missing_image_count

def index_containing_substring(the_list, substring):
    for i, s in enumerate(the_list):
        if substring in s:
            return i
    return -1

def rectangle_center(rectangle):
    '''Returns (x,y) tuple of center of rectangle.'''
    x, y, w, h = rectangle
    return (x + w/2, y + h/2)

def rectangle_corners(rectangle):
    '''Return top left (x1, y1) and bottom right (x2, y2) corners as flat tuple.'''
    x, y, w, h = rectangle
    return (x, y, x+w, y+h)

def distance_between_rects(rect1, rect2):
    '''Return distance between center of rectangles.'''
    x1, y1 = rectangle_center(rect1)
    x2, y2 = rectangle_center(rect2)
    dx = x1 - x2
    dy = y1 - y2
    return math.sqrt(dx*dx + dy*dy)
    
def merge_rectangles(rectangles):
    '''Return rectangle that contains all rectangles.'''
    corners = [rectangle_corners(rectangle) for rectangle in rectangles]
    x1 = min([c[0] for c in corners])
    y1 = min([c[1] for c in corners])
    x2 = max([c[2] for c in corners])
    y2 = max([c[3] for c in corners])
    return (x1, y1, x2-x1, y2-y1)
                
def cluster_rectangles(rectangles, eps):
    '''Combine rectangles within eps (pixels) of each other.'''
    groupings = [-1] * len(rectangles)
    for i, rectangle in enumerate(rectangles):
        if groupings[i] == -1:
            groupings[i] = i # haven't been claim yet.
        for j, other_rectangle in enumerate(rectangles):
            if i == j:
                continue # same rectangle
            if distance_between_rects(rectangle, other_rectangle) < eps:
                if groupings[j] == -1:
                    groupings[j] = groupings[i] # claim this rectangle
                else:
                    # claim all rectangle with group we're running into
                    groupings = [groupings[i] if x==groupings[j] else x for x in groupings]
     
    used_groupings = list(set(groupings))
    
    clustered_rectangles = []
    for group in used_groupings:
        # Get all rectangles associated with this group
        rectangles_in_group = []
        for i, g in enumerate(groupings):
            if g == group:
                rectangles_in_group.append(rectangles[i])
                
        clustered_rectangles.append(merge_rectangles(rectangles_in_group))
   
    return clustered_rectangles
