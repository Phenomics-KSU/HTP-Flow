#! /usr/bin/env python

import os
from operator import itemgetter, attrgetter, methodcaller
import math

# OpenCV imports
import cv2 as cv
import numpy as np

# Zbar imports
import zbar
import Image # Python Imaging Library

# Project imports
from data import *
from image_utils import *

class ItemExtractor:
    '''Extracts field items from image.'''    
    def __init__(self, locators):
        '''Constructor'''
        self.locators = locators
    
    def extract_items(self, geo_image, image, marked_image, out_directory):
        '''Find items with locators and extract items into separate images. Return list of FieldItems.'''
        if marked_image is not None:
            # Show what 1" is on the top-left of the image.
            pixels = int(2.54 / geo_image.resolution)
            cv.rectangle(marked_image, (1,1), (pixels, pixels), (255,255,255), 2) 
    
        field_items = []
        for locator in self.locators:
            located_items = locator.locate(geo_image, image, marked_image)
            field_items.extend(located_items)

        # Extract field items into separate image
        for item in field_items:
            
            extracted_image = extract_image(item.bounding_rect, 20, image)
            
            extracted_image_fname = "{0}_{1}.jpg".format(item.item_type, item.name)
            extracted_image_path = ImageWriter.save_normal(extracted_image_fname, extracted_image)
            
            item.image_path = extracted_image_path
            
            item.position = calculate_position(item, geo_image)
        
        return field_items
        
class QRLocator:
    '''Locates and decodes QR codes.'''
    def __init__(self, qr_size):
        '''Constructor.  QR size is an estimate for searching.'''
        self.qr_size = qr_size
    
    def locate(self, geo_image, image, marked_image):
        '''Find QR codes in image and decode them.  Return list of FieldItems representing valid QR codes.''' 
        # Grayscale original image so we can find edges in it. Default for OpenCV is BGR not RGB.
        gray_image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    
        # Need to blur image before running edge detector to avoid a bunch of small edges due to noise.
        _, thresh_image = cv.threshold(gray_image, 150, 255, 0)
        
        # Find outer contours (edges) and 'approximate' them to reduce the number of points along nearly straight segments.
        contours, hierarchy = cv.findContours(thresh_image.copy(), cv.cv.CV_RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        contours = [cv.approxPolyDP(contour, .1, True) for contour in contours]
        
        # Create bounding box for each contour.
        bounding_rectangles = [cv.boundingRect(contour) for contour in contours]
        
        # Remove any rectangles that couldn't be a QR item based off specified side length.
        min_qr_size = self.qr_size * 0.3
        max_qr_size = self.qr_size * 2.5
        filtered_rectangles = filter_by_size(bounding_rectangles, geo_image.resolution, min_qr_size, max_qr_size)
        
        if ImageWriter.level <= ImageWriter.DEBUG:
            # Debug save intermediate images
            thresh_filename = postfix_filename(geo_image.file_name, 'thresh')
            ImageWriter.save_debug(thresh_filename, thresh_image)
        
        # Scan each rectangle with QR reader to remove false positives and also extract data from code.
        qr_items = []
        for rectangle in filtered_rectangles:
            extracted_image = extract_image(rectangle, 30, image)
            qr_data = self.scan_image(extracted_image)            
            scan_successful = len(qr_data) != 0

            if scan_successful:
                qr_item = FieldItem(item_type = 'code', name = 'default', parent_image = geo_image.file_name, bounding_rect = rectangle)
                qr_item.name = qr_data[0]
                qr_items.append(qr_item)
                
            if marked_image is not None:
                # Show success/failure using colored bounding box.
                green = (0, 255, 0)
                red = (0, 0, 255)
                item_color = green if scan_successful else red
                x,y,w,h = rectangle
                cv.rectangle(marked_image, (x,y), (x+w,y+h), item_color, 2) 
        
        return qr_items
    
    def scan_image(self, cv_image):
        '''Scan image with Zbar and return data found in visual code(s)'''
        # Create and configure reader.
        scanner = zbar.ImageScanner()
        scanner.parse_config('enable')
         
        # Convert colored OpenCV image to grayscale PIL image.
        cv_image = cv.cvtColor(cv_image, cv.COLOR_BGR2RGB)
        pil_image= Image.fromarray(cv_image)
        pil_image = pil_image.convert('L') # convert to grayscale

        # Wrap image data. Y800 is grayscale format.
        width, height = pil_image.size
        raw = pil_image.tostring()
        image = zbar.Image(width, height, 'Y800', raw)
        
        # Scan image and return results.
        scanner.scan(image)

        return [symbol.data for symbol in image]

class PlantLocator:
    '''Locates plants within an image.'''
    def __init__(self, plant_size):
        '''Constructor.  Plant size is an estimate for searching.'''
        self.plant_size = plant_size
    
    def locate(self, geo_image, image, marked_image):
        '''Find plants in image and return list of Plant instances.''' 
        # Grayscale original image so we can find edges in it. Default for OpenCV is BGR not RGB.
        #blue_channel, green_channel, red_channel = cv.split(image)
        
        # Convert Blue-Green-Red color space to HSV
        hsv_image = cv.cvtColor(image, cv.COLOR_BGR2HSV)
            
        # Define range of green colors in HSV that corresponds with plants.
        green_hue = 60
        lower_green = np.array([green_hue - 30, 50, 50], np.uint8)
        upper_green = np.array([green_hue + 30, 255, 255], np.uint8)
    
        # Threshold the HSV image to get only green colors
        green_mask = cv.inRange(hsv_image, lower_green, upper_green)
        
        # Find outer contours (edges) and 'approximate' them to reduce the number of points along nearly straight segments.
        contours, hierarchy = cv.findContours(green_mask.copy(), cv.cv.CV_RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
        contours = [cv.approxPolyDP(contour, .1, True) for contour in contours]
        
        # Create bounding box for each contour.
        bounding_rectangles = [cv.boundingRect(contour) for contour in contours]
        
        # Remove any rectangles that couldn't be a plant based off specified size
        min_plant_size = self.plant_size * 0.2
        max_plant_size = self.plant_size * 3
        filtered_rectangles = filter_by_size(bounding_rectangles, geo_image.resolution, min_plant_size, max_plant_size)
        
        if ImageWriter.level <= ImageWriter.DEBUG:
            # Debug save intermediate images
            '''
            hue, saturation, value = cv.split(hsv_image)
            hue_filename = postfix_filename(geo_image.file_name, 'hue_channel')
            ImageWriter.save_debug(hue_filename, hue)
            saturation_filename = postfix_filename(geo_image.file_name, 'saturation_channel')
            ImageWriter.save_debug(saturation_filename, saturation)
            value_filename = postfix_filename(geo_image.file_name, 'value_channel')
            ImageWriter.save_debug(value_filename, value)
            '''
            edge_filename = postfix_filename(geo_image.file_name, 'edges')
            ImageWriter.save_debug(edge_filename, green_mask)
        
        plants = []
        for i, rectangle in enumerate(filtered_rectangles):
            
            # Just give default name for saving image until we later go through and assign to plant group.
            plant = Plant(item_type = 'plant', name = 'plant{0}'.format(i), parent_image = geo_image.file_name, bounding_rect = rectangle)
            plants.append(plant)
                
            if marked_image is not None:
                # Show successful plants using colored bounding box.
                purple = (255, 0, 255)
                x,y,w,h = rectangle
                cv.rectangle(marked_image, (x,y), (x+w,y+h), purple, 2) 
        
        return plants

def filter_by_size(bounding_rects, resolution, min_size, max_size):
    '''Return list of rectangles that are within min/max size (specified in centimeters)'''
    filtered_rects = []
    
    for rectangle in bounding_rects:    
        #w_pixels, h_pixels = rectangle[1]
        _, _, w_pixels, h_pixels = rectangle
        
        w = w_pixels * resolution
        h = h_pixels * resolution
        
        if h >= min_size and w >= min_size and h <= max_size and w <= max_size:
            filtered_rects.append(rectangle)
            
    return filtered_rects

def extract_image(rectangle, pad, image):
    '''Return image that corresponds to bounding rectangle with pad added in.'''
    # reference properties of bounding rectangle
    #x, y = rectangle[0]
    #w, h = rectangle[1]
    x, y, w, h = rectangle
    
    # image width, height and depth
    image_h, image_w, image_d = image.shape
    
    # add in pad to rectangle and respect image boundaries
    top = int(max(1, y - pad))
    bottom = int(min(image_h - 1, y + h + pad))
    left = int(max(1, x - pad))
    right = int(min(image_w - 1, x + w + pad))

    return image[top:bottom, left:right]

def order_items(items, camera_rotation):
    '''Return new list but sorted from backward to forward taking into account camera rotation.'''
    if camera_rotation == 180:  # top to bottom
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[1])
    elif camera_rotation == 0: # bottom to top
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[1], reverse=True)
    elif camera_rotation == 90: # left to right
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[0])
    elif camera_rotation == 270: # right to left
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[0], reverse=True)
    else:
        return None
    
def calculate_position(item, geo_image):
    '''Return (x,y,z) position of item within geo image.'''
    resolution = geo_image.resolution
    x, y = rectangle_center(item.bounding_rect)
    # Reference x y from center of image instead of top left corner.
    x = x - geo_image.size[0]/2
    y = -y + geo_image.size[1]/2
    # Rotate x y from image frame to easting-northing frame.
    # A camera rotation of 0 corresponds to top of image being forward so need to subtract 90 to get positive x being top of image.
    heading = math.radians(geo_image.heading_degrees + geo_image.camera_rotation_degrees - 90)
    east_offset = math.cos(heading) * x - math.sin(heading) * y
    north_offset = math.sin(heading) * x + math.cos(heading) * y
    # Convert offsets from pixels to meters.
    east_offset *= resolution / 100
    north_offset *= resolution / 100
    # Take into account camera height.  Negative since item is below camera.
    z_meters = -geo_image.camera_height / 100
    
    return (geo_image.position[0] + east_offset, geo_image.position[1] + north_offset, geo_image.position[2] + z_meters)

    
     
    
