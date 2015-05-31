#! /usr/bin/env python

import sys
import os
import argparse

# import the necessary things for OpenCV
import cv2 as cv
import numpy as np
import zbar
import Image

from data import *

#class ItemMarker

class ItemExtractor:
    
    def __init__(self, locators):
        self.locators = locators
    
    def extract_items(self, geo_image, image, out_directory):
    
        field_items = []
        failed_items = []
    
        for locator in self.locators:
            located_items, failed_items = locator.locate(geo_image, image)
            field_items.extend(located_items)
            failed_items.extend(failed_items)

        # Extract field items into own image
        for item in field_items:
            
            extracted_image = extract_image(item.bounding_rect, 20, image)
            
            extracted_image_fname = "{0}_{1}.jpg".format(item.item_type, item.name)
            extracted_image_path = os.path.join(out_directory, extracted_image_fname)
            
            cv.imwrite(extracted_image_path, extracted_image)
            
            item.image_path = extracted_image_path

        #sorts them in order
        
        return field_items
        

class QRLocator:
    
    def __init__(self, qr_size):
        self.qr_size = qr_size
    
    def locate(self, geo_image, image):

        # Grayscale original image so we can find edges in it. Default for OpenCV is BGR not RGB.
        gray_image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    
        # Need to blur image before running edge detector to avoid a bunch of small edges due to noise.
        blurred_image = cv.GaussianBlur(gray_image, (5,5), 0)
        
        # Canny will output a binary image where white = edges and black = background.
        edge_image = cv.Canny(blurred_image, 100, 200)
        
        # Find contours (edges) and 'approximate' them to reduce the number of points along nearly straight segments.
        contours, hierarchy = cv.findContours(edge_image, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
        contours = [cv.approxPolyDP(contour, .1, True) for contour in contours]
        
        # Create rotated bounding rectangle for each contour.
        #bounding_rectangles = [cv.minAreaRect(contour) for contour in contours]
        bounding_rectangles = [cv.boundingRect(contour) for contour in contours]
        
        # Remove any rectangles that couldn't be a QR item based off specified side length.
        min_qr_size = self.qr_size * 0.3
        max_qr_size = self.qr_size * 2.5
        filtered_rectangles = filter_by_size(bounding_rectangles, geo_image.resolution, min_qr_size, max_qr_size)
        
        # Scan each rectangle with QR reader to remove false positives and also extract data from code.
        qr_items = []
        failed_items = []
        for rectangle in filtered_rectangles:
            extracted_image = extract_image(rectangle, 30, image)
            qr_data = self.scan_image(extracted_image)
            
            qr_item = FieldItem(item_type = 'code', name = 'default', parent_image = geo_image.file_name, bounding_rect = rectangle)
            
            if len(qr_data) != 0:
                qr_item.name = qr_data[0]
                qr_items.append(qr_item)
            else:
                failed_items.append(qr_item)
        
        return qr_items, failed_items
    
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
        for symbol in image:
            print symbol.data
        return [symbol.data for symbol in image]

def filter_by_size(bounding_rects, resolution, min_size, max_size):
    
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


