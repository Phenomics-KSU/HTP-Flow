#! /usr/bin/env python

import sys
import os
import argparse
import ExifTags
import Image
import time
#import exifread

if __name__ == '__main__':
    ''''''

    input_directory = r"C:\Users\Kyle\Documents\sunflower\day4_7_13_2015\pisc_logs\combined_20150715-194156"
    input_filename = r"canon_7D_C01_lc_2_combined.csv"
    just_input_filename, input_filename_ext = os.path.splitext(input_filename)
    
    input_filepath = os.path.join(input_directory, input_filename)
    if not os.path.exists(input_filepath):
        print "File does not exist: {0}".format(input_filepath)
        sys.exit(1)
        
    output_filename = "{}_renumbered{}".format(just_input_filename, input_filename_ext)
    output_filepath = os.path.join(input_directory, output_filename)
    
    with open(output_filepath, 'w') as out_file:
        with open(input_filepath, 'r') as in_file:
            for input_line in in_file.readlines():
                utc_time, image_filename = [field.strip() for field in input_line.split(',')]
                
                just_image_filename, image_extension = os.path.splitext(image_filename)
                filename_parts = just_image_filename.split('_')
                image_number = int(filename_parts[-1])
                
                fixed_image_number = image_number - 1
                if fixed_image_number == 0:
                    fixed_image_number = 9999
                if fixed_image_number == 10000:
                    fixed_image_number = 1
                
                new_image_name = "{}_{:04d}{}".format('_'.join(filename_parts[:-1]), fixed_image_number, image_extension)
                
                out_file.write("{},{}\n".format(utc_time, new_image_name))
