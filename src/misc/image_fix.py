#! /usr/bin/env python

import sys
import os
import argparse
import ExifTags
import Image
import time
#import exifread

if __name__ == '__main__':
    '''Rename and optionally move images.'''

    recursive = False
    
    input_directory = r"L:\sunflower\day3_7_08_2015\images\cam01_converted"
    
    if not os.path.exists(input_directory):
        print "Directory does not exist: {0}".format(input_directory)
        sys.exit(1)
        
    # Get list of image file paths to rename.
    image_filepaths = []
    for (dirpath, dirnames, filenames) in os.walk(input_directory):
        for filename in filenames:
            # Make sure file has correct extension before adding it.
            extension = os.path.splitext(filename)[1][1:]
            if extension in '.jpg':
                image_filepaths.append(os.path.join(dirpath, filename))
        if not recursive:
            break # only walk top level directory
    
    number_renamed = 0 # How many images are successfully renamed
    
    for filepath in image_filepaths:
        
        original_directory, original_filename = os.path.split(filepath)
        
        right_cam_idx = original_filename.find('CAM')
        second_cam_idx = original_filename.find('CAM', 3)
        
        if second_cam_idx > 0:
            new_filename = original_filename[second_cam_idx:]
        else:
            continue

        new_filepath = os.path.join(original_directory, new_filename)
            
        #print "Renameming \n{} to\n{}".format(filepath, new_filepath)
            
        try:
            os.rename(filepath, new_filepath)
            number_renamed += 1
        except WindowsError as e:
            print "Failed to rename\n{} to\n{}\n{}".format(filepath, new_filepath, e)


    print 'Renamed {0} files.'.format(number_renamed)