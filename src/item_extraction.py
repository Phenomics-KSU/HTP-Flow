#! /usr/bin/env python

import os
from operator import itemgetter, attrgetter, methodcaller
import math

# OpenCV imports
import cv2
import numpy as np

# Zbar imports
import zbar
import Image # Python Imaging Library

# Project imports
from data import *
from image_utils import *
from item_processing import *

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
            cv2.rectangle(marked_image, (1,1), (pixels, pixels), (255,255,255), 2) 
    
        field_items = []
        for locator in self.locators:
            located_items = locator.locate(geo_image, image, marked_image)
            field_items.extend(located_items)

        # Filter out any items that touch the image border since it likely doesn't represent entire item.
        items_without_border_elements = []
        for item in field_items:
            if touches_image_border(item, geo_image):
                # Mark as special color to show user why it wasn't included.
                if marked_image is not None:
                    dark_orange = (0, 140, 255) # dark orange
                    drawRect(marked_image, item.bounding_rect, dark_orange, thickness=2)
            else:
                items_without_border_elements.append(item)
        field_items = items_without_border_elements

        # Extract field items into separate image
        for item in field_items:
            
            extracted_image = extract_square_image(image, item.bounding_rect, 20)
            
            extracted_image_fname = "{0}_{1}.jpg".format(item.type, item.name)
            extracted_image_path = ImageWriter.save_normal(extracted_image_fname, extracted_image)
            
            item.image_path = extracted_image_path
            
            item.parent_image_filename = geo_image.file_name
            
            item.position = calculate_position(item, geo_image)
        
        return field_items
        
class QRLocator:
    '''Locates and decodes QR codes.'''
    def __init__(self, qr_size):
        '''Constructor.  QR size is an estimate for searching.'''
        self.qr_size = qr_size
    
    def locate(self, geo_image, image, marked_image):
        '''Find QR codes in image and decode them.  Return list of FieldItems representing valid QR codes.''' 
        # Threshold grayscaled image to make white QR codes stands out.
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh_image = cv2.threshold(gray_image, 160, 255, 0)
        
        # Open mask (to remove noise) and then dilate it to connect contours.
        kernel = np.ones((5,5), np.uint8)
        mask_open = cv2.morphologyEx(thresh_image, cv2.MORPH_OPEN, kernel)
        thresh_image = cv2.dilate(mask_open, kernel, iterations = 1)
        
        # Find outer contours (edges) and 'approximate' them to reduce the number of points along nearly straight segments.
        contours, hierarchy = cv2.findContours(thresh_image.copy(), cv2.cv.CV_RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        #contours = [cv2.approxPolyDP(contour, .1, True) for contour in contours]
        
        # Create bounding box for each contour.
        bounding_rectangles = [cv2.minAreaRect(contour) for contour in contours]

        # Remove any rectangles that couldn't be a QR item based off specified side length.
        min_qr_size = self.qr_size * 0.6
        max_qr_size = self.qr_size * 4 # set large in case stuff under code
        filtered_rectangles = filter_by_size(bounding_rectangles, geo_image.resolution, min_qr_size, max_qr_size)
        
        if ImageWriter.level <= ImageWriter.DEBUG:
            # Debug save intermediate images
            thresh_filename = postfix_filename(geo_image.file_name, 'thresh')
            ImageWriter.save_debug(thresh_filename, thresh_image)
        
        # Scan each rectangle with QR reader to remove false positives and also extract data from code.
        qr_items = []
        for rectangle in filtered_rectangles:
            qr_data = self.scan_image_different_trims_and_threshs(image, rectangle, trims=[0, 3, 8, 12, 16])
            scan_successful = len(qr_data) != 0

            if scan_successful:

                qr_code = create_qr_code(qr_data[0], rectangle) 
                
                if qr_code is None:
                    print 'WARNING: Invalid QR data found ' + qr_data[0]
                else:
                    qr_items.append(qr_code)
                
            if marked_image is not None:
                # Show success/failure using colored bounding box
                success_color = (0, 255, 0) # green
                if scan_successful and qr_code is not None and qr_code.type == 'RowCode': 
                    success_color = (0, 255, 255) # yellow for row codes
                failure_color = (0, 0, 255) # red
                item_color = success_color if scan_successful else failure_color
                drawRect(marked_image, rectangle, item_color, thickness=2)
        
        return qr_items
    
    def scan_image_different_trims_and_threshs(self, full_image, rotated_rect, trims):
        '''Scan image using different trims if first try fails. Return list of data found in image.'''
        
        for i, trim in enumerate(trims):
            extracted_image = extract_rotated_image(full_image, rotated_rect, 30, trim=trim)
            qr_data = self.scan_image_different_threshs(extracted_image)
            if len(qr_data) != 0:
                if i > 0:
                    print "Success with trim value {} on try {}".format(trim, i+1)
                return qr_data # scan successful
            
        return [] # scans unsuccessful.
    
    def scan_image_different_threshs(self, cv_image):
        '''Scan image using multiple thresholds if first try fails. Return list of data found in image.'''
        scan_try = 0
        qr_data = []
        while True:
            if scan_try == 0:
                image_to_scan = cv_image # use original image
            elif scan_try == 1:
                cv_gray_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                cv_thresh_image = cv2.adaptiveThreshold(cv_gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 101, 2)
                image_to_scan = cv2.cvtColor(cv_thresh_image, cv2.COLOR_GRAY2BGR)
            elif scan_try == 2:
                cv_gray_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
                _, cv_thresh_image = cv2.threshold(cv_gray_image, 150, 255, 0)
                image_to_scan = cv2.cvtColor(cv_thresh_image, cv2.COLOR_GRAY2BGR)
            else:
                break # nothing else to try.
            
            qr_data = self.scan_image(image_to_scan)
            
            if len(qr_data) > 0:
                break # found code data in image so don't need to keep trying
            
            scan_try += 1
            
        # Notify if had to use a backup thresholding and had success.
        if scan_try > 0 and len(qr_data) > 0:
            print 'success on scan try {0}'.format(scan_try)
            
        return qr_data
    
    def scan_image(self, cv_image):
        '''Scan image with Zbar and return data found in visual code(s)'''
        # Create and configure reader.
        scanner = zbar.ImageScanner()
        scanner.parse_config('enable')
         
        # Convert colored OpenCV image to grayscale PIL image.
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
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
    def __init__(self, min_plant_size, max_plant_size):
        '''Constructor.  Plant size is an estimate for searching.'''
        self.min_plant_size = min_plant_size
        self.max_plant_size = max_plant_size
    
    def locate(self, geo_image, image, marked_image):
        '''Find plants in image and return list of Plant instances.''' 
        # Grayscale original image so we can find edges in it. Default for OpenCV is BGR not RGB.
        #blue_channel, green_channel, red_channel = cv2.split(image)
        
        # Convert Blue-Green-Red color space to HSV
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
        # Threshold the HSV image to get only green colors that correspond to healthy plants.
        green_hue = 60
        lower_green = np.array([green_hue - 30, 90, 50], np.uint8)
        upper_green = np.array([green_hue + 30, 255, 255], np.uint8)
        plant_mask = cv2.inRange(hsv_image, lower_green, upper_green)
        
        # Now do the same thing for greenish dead plants.
        lower_dead_green = np.array([10, 35, 60], np.uint8)
        upper_dead_green = np.array([90, 255, 255], np.uint8)
        dead_green_plant_mask = cv2.inRange(hsv_image, lower_dead_green, upper_dead_green)
    
        # Now do the same thing for yellowish dead plants.
        #lower_yellow = np.array([10, 50, 125], np.uint8)
        #upper_yellow = np.array([40, 255, 255], np.uint8)
        #dead_yellow_plant_mask = cv2.inRange(hsv_image, lower_yellow, upper_yellow)
        
        filtered_rectangles = []
        for i, mask in enumerate([plant_mask, dead_green_plant_mask]):
            # Open mask (to remove noise) and then dilate it to connect contours.
            kernel = np.ones((5,5), np.uint8)
            mask_open = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.dilate(mask_open, kernel, iterations = 1)
            
            # Find outer contours (edges) and 'approximate' them to reduce the number of points along nearly straight segments.
            contours, hierarchy = cv2.findContours(mask.copy(), cv2.cv.CV_RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            #contours = [cv2.approxPolyDP(contour, .1, True) for contour in contours]
            
            # Create bounding box for each contour.
            bounding_rectangles = [cv2.minAreaRect(contour) for contour in contours]
            
            if marked_image is not None:
                for rectangle in bounding_rectangles:
                    # Show rectangles using bounding box.
                    drawRect(marked_image, rectangle, (0,0,0), thickness=2)
            
            # Remove any rectangles that couldn't be a plant based off specified size.
            filtered_rectangles.extend(filter_by_size(bounding_rectangles, geo_image.resolution, self.min_plant_size, self.max_plant_size, enforce_min_on_w_and_h=False))
            
            if ImageWriter.level <= ImageWriter.DEBUG:
                # Debug save intermediate images
                mask_filename = postfix_filename(geo_image.file_name, 'mask_{0}'.format(i))
                ImageWriter.save_debug(mask_filename, mask)
        
        if marked_image is not None:
            for rectangle in filtered_rectangles:
                # Show rectangles using colored bounding box.
                purple = (255, 0, 255)
                drawRect(marked_image, rectangle, purple, thickness=2)
        
        # Now go through and cluster plants (leaves) that are close together.
        max_distance = 20 # centimeters
        rectangle_clusters = cluster_rectangles(filtered_rectangles, max_distance / geo_image.resolution)
            
        plants = []
        for i, rectangle in enumerate(rectangle_clusters):
            
            # Just give default name for saving image until we later go through and assign to plant group.
            plant = Plant(name = 'plant' + str(i), bounding_rect = rectangle)
            plants.append(plant)
                
            if marked_image is not None:
                # Show successful plants using colored bounding box.
                blue = (255, 0, 0)
                drawRect(marked_image, rectangle, blue, thickness=2)
        
        return plants

class BlueStickLocator:
    '''Locates blue sticks that are inserted into center of plants.'''
    def __init__(self, stick_length, stick_diameter):
        '''Constructor.  Sizes should be in centimeters.'''
        self.stick_length = stick_length
        self.stick_diameter = stick_diameter
    
    def locate(self, geo_image, image, marked_image):
        '''Find sticks in image and return list of FieldItem instances.''' 
        # Extract out just blue channel from BGR image.
        #blue_channel, _, _ = cv2.split(image)
        #_, mask = cv2.threshold(blue_channel, 160, 255, 0)
        
        # Convert Blue-Green-Red color space to HSV
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        lower_blue = np.array([90, 90, 50], np.uint8)
        upper_blue = np.array([130, 255, 255], np.uint8)
        mask = cv2.inRange(hsv_image, lower_blue, upper_blue)
        
        # Night time testing
        lower_blue = np.array([90, 10, 5], np.uint8)
        upper_blue = np.array([142, 255, 255], np.uint8)
        mask = cv2.inRange(hsv_image, lower_blue, upper_blue)

        filtered_rectangles = []
        
        # Open mask (to remove noise) and then dilate it to connect contours.
        kernel = np.ones((5,5), np.uint8)
        mask_open = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.dilate(mask_open, kernel, iterations = 1)
        
        # Find outer contours (edges) and 'approximate' them to reduce the number of points along nearly straight segments.
        contours, hierarchy = cv2.findContours(mask.copy(), cv2.cv.CV_RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        #contours = [cv2.approxPolyDP(contour, .1, True) for contour in contours]
        
        # Create bounding box for each contour.
        bounding_rectangles = [cv2.minAreaRect(contour) for contour in contours]
        
        if marked_image is not None:
            for rectangle in bounding_rectangles:
                # Show rectangles using bounding box.
                drawRect(marked_image, rectangle, (0,0,0), thickness=2)
        
        # Remove any rectangles that couldn't be a plant based off specified size.
        min_stick_size = self.stick_diameter * 0.75 # looking straight down on it
        max_stick_size = self.stick_length * 1.25 # laying flat on the ground
        filtered_rectangles.extend(filter_by_size(bounding_rectangles, geo_image.resolution, min_stick_size, max_stick_size, enforce_min_on_w_and_h=True))
        
        if ImageWriter.level <= ImageWriter.DEBUG:
            # Debug save intermediate images
            mask_filename = postfix_filename(geo_image.file_name, 'blue_thresh')
            ImageWriter.save_debug(mask_filename, mask)
        
        if marked_image is not None:
            for rectangle in filtered_rectangles:
                # Show rectangles using colored bounding box.
                purple = (255, 0, 255)
                drawRect(marked_image, rectangle, purple, thickness=2)

        sticks = []
        for i, rectangle in enumerate(filtered_rectangles):
            # Just give default name for saving image until we later go through and assign to plant group.
            stick = FieldItem(name = 'stick' + str(i), bounding_rect = rectangle)
            sticks.append(stick)
                
        return sticks

def filter_by_size(bounding_rects, resolution, min_size, max_size, enforce_min_on_w_and_h=True):
    '''Return list of rectangles that are within min/max size (specified in centimeters)'''
    filtered_rects = []
    
    for rectangle in bounding_rects:    
        center, dim, theta = rectangle
        w_pixels, h_pixels = dim
        
        w = w_pixels * resolution
        h = h_pixels * resolution
        
        if enforce_min_on_w_and_h:
            # Need both side lengths to pass check.
            min_check_passed = h >= min_size and w >= min_size
        else:
            # Just need one side length to be long enough.
            min_check_passed = h >= min_size or w >= min_size
            
        if min_check_passed and h <= max_size and w <= max_size:
            filtered_rects.append(rectangle)
            
    return filtered_rects

def extract_square_image(image, rectangle, pad, rotated=True):
    '''Return image that corresponds to bounding rectangle with pad added in.
       If rectangle is rotated then it is converted to a normal non-rotated rectangle.'''
    # reference properties of bounding rectangle
    if rotated:
        rectangle = rotatedToRegularRect(rectangle)

    x, y, w, h = rectangle
    
    # image width, height and depth
    image_h, image_w, image_d = image.shape
    
    # add in pad to rectangle and respect image boundaries
    top = int(max(1, y - pad))
    bottom = int(min(image_h - 1, y + h + pad))
    left = int(max(1, x - pad))
    right = int(min(image_w - 1, x + w + pad))

    return image[top:bottom, left:right]
    
def extract_rotated_image(image, rotated_rect, pad, trim=0):
    '''Return image that corresponds to bounding rectangle with a white pad background added in.'''
    center, dim, theta = rotated_rect
    width, height = dim
    trimmed_rect = (center, (width-trim, height-trim), theta)
    center, dim, theta = trimmed_rect
    width, height = dim

    rect_corners = rectangle_corners(trimmed_rect, rotated=True)
    poly = np.array([rect_corners], dtype=np.int32)
    mask = np.zeros((image.shape[0],image.shape[1],1), np.uint8)
    cv2.fillPoly(mask, poly, 255)
    masked_image = cv2.bitwise_and(image, image, mask=mask)
    
    inverted_mask = cv2.bitwise_not(mask, mask)
    masked_image = cv2.bitwise_not(masked_image, masked_image, mask=inverted_mask)
    
    return extract_square_image(masked_image, trimmed_rect, pad, rotated=True)
    
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
    
def create_qr_code(qr_data, bounding_rect):
    '''Return either GroupCode or RowCode depending on qr data.  Return None if neither.'''
    
    if qr_data == '22a':
        qr_data = '1'
    
    if qr_data[:2] == 'R.' and qr_data[2:].isdigit():
        qr_item = RowCode(name = qr_data)
    else:
        if qr_data.isdigit():
            qr_item = GroupCode(name = qr_data)
        else:
            # Wasn't a recognized code.
            return None
        
    # Fill in any common fields here.
    qr_item.bounding_rect = bounding_rect

    return qr_item
