#! /usr/bin/env python

import sys
import os
import argparse
import ExifTags
import Image
import time
#import exifread

def is_number(s):
    '''Return true if s is a number.'''
    try:
        float(s)
        return True
    except ValueError:
        return False

if __name__ == '__main__':
    '''Rename and optionally move images.'''

    default_recursive = True
    parser = argparse.ArgumentParser(description='Rename and optionally move images.')
    parser.add_argument('input_directory', help='Where to search for files to rename.')
    parser.add_argument('output_directory', help='Where to move all renamed files. If \'none\' then renamed files will not be moved.')
    parser.add_argument('extensions', help='List of file extensions to rename separated by commas. Example "jpg, CR2". Case sensitive.')
    parser.add_argument('-r', dest='recursive', default=default_recursive, help='If true then will recursively search through input directory for images. Default {}'.format(default_recursive))
    args = parser.parse_args()
    
    # Convert command line arguments
    input_directory = args.input_directory
    output_directory = args.output_directory
    extensions = args.extensions.split(',')
    recursive = args.recursive.lower() == 'true'
    
    if not os.path.exists(input_directory):
        print "Directory does not exist: {0}".format(input_directory)
        sys.exit(1)
        
    move_files = (output_directory.lower() != 'none')
    if move_files:
        # Make sure output directory exists
        if not os.path.exists(output_directory):
            print "Creating output directory {}".format(output_directory)
            os.makedirs(output_directory)
        
    # Get list of image file paths to rename.
    image_filepaths = []
    for (dirpath, dirnames, filenames) in os.walk(input_directory):
        for filename in filenames:
            # Make sure file has correct extension before adding it.
            extension = os.path.splitext(filename)[1][1:]
            if extension in extensions:
                image_filepaths.append(os.path.join(dirpath, filename))
        if not recursive:
            break # only walk top level directory
    
    number_renamed = 0 # How many images are successfully renamed
    
    for filepath in image_filepaths:
        
        original_directory, original_filename = os.path.split(filepath)
        
        # Extract camera serial number and capture date/time from EXIF metadata so we can use it for renaming image.
        with open(filepath, 'rb') as f:
            img = Image.open(f)
            exif = img._getexif()
            cam_serial_number = exif[42033]
            datetime_original = exif[36867]
            datetime_original = time.strptime(datetime_original, "%Y:%m:%d %H:%M:%S")
            del img
        
        #epoch_seconds = time.mktime(datetime_original)

        new_filename = "CAM_{}_{}_{}".format(cam_serial_number, time.strftime("%Y%m%d_%H%M%S", datetime_original), original_filename) 
        
        if move_files:
            # Rename and move file.
            new_filepath = os.path.join(output_directory, new_filename)
        else: 
            # Just rename file.
            new_filepath = os.path.join(original_directory, new_filename)
            
        try:
            os.rename(filepath, new_filepath)
            number_renamed += 1
        except WindowsError as e:
            print "Failed to rename\n{} to\n{}\n{}".format(filepath, new_filepath, e)

    print 'Renamed {0} files.'.format(number_renamed)