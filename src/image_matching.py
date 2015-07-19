#! /usr/bin/env python

import sys
import os
import argparse
import time
import itertools

if __name__ == '__main__':
    '''Match log file up with renamed image files.'''

    default_recursive = 'true'
    parser = argparse.ArgumentParser(description='Match log file up with renamed image files.')
    parser.add_argument('image_directory', help='Directory containing renamed image files.')
    parser.add_argument('image_log', help='File containing time-stamped file names to match to actual images.')
    parser.add_argument('extensions', help='List of file extensions to rename separated by commas. Example "jpg, CR2". Case sensitive.')
    parser.add_argument('-r', dest='recursive', default=default_recursive, help='If true then will recursively search through input directory for images. Default {}'.format(default_recursive))
    args = parser.parse_args()
    
    # Convert command line arguments
    image_directory = args.image_directory
    image_log = args.image_log
    extensions = args.extensions.split(',')
    recursive = args.recursive.lower() == 'true'
    
    if not os.path.exists(image_directory):
        print "Directory does not exist: {}".format(image_directory)
        sys.exit(1)
        
    image_log_directory, image_log_filename = os.path.split(image_log)
    output_directory = os.path.join(image_log_directory, 'matched/')
    if not os.path.exists(output_directory):
        print "Creating output directory {}".format(output_directory)
        os.makedirs(output_directory)
        
    filesystem_images = []
    for (dirpath, dirnames, filenames) in os.walk(image_directory):
        for filename in filenames:
            # Make sure file has correct extension before adding it.
            just_filename, extension = os.path.splitext(filename)
            if extension[1:] in extensions:
                filename_parts = just_filename.split('_')
                serial_number = filename_parts[1]
                datetime_original = '-'.join(filename_parts[2:4])
                datetime_original = time.strptime(datetime_original, "%Y%m%d-%H%M%S")
                epoch_seconds = time.mktime(datetime_original)
                image_number = int(filename_parts[-1])
                filesystem_images.append((epoch_seconds, filename, image_number))
        if not recursive:
            break # only walk top level directory
        
    if len(filesystem_images) == 0:
        print "No images with extensions {} from directory {} could be read in.".format(extensions, image_directory)
        sys.exit(1)
        
    print "Read in {} images from image directory.".format(len(filesystem_images))

    print "Sorting images from file system by time stamp."
    filesystem_images = sorted(filesystem_images, key=lambda i: i[0])

    # Read in input file.
    log_contents = []
    with open(image_log, 'r') as input_file:
        for line in input_file.readlines():
            items = [i.strip() for i in line.split(',')]
            if len(items) != 2:
                continue
            utc_time = float(items[0])
            image_filename = items[1]
            log_contents.append((utc_time, image_filename))
            
    print "Read in {} timestamped image names from image log.".format(len(log_contents))
            
    print 'Sorting log contents by time stamp.'
    log_contents = sorted(log_contents, key=lambda c: c[0])
            
    last_matched_index = 0
    matched_log_contents = []
    for line_num, log_line in enumerate(log_contents):
        
        utc_time = log_line[0]
        original_filename = log_line[1]
        just_filename, extension = os.path.splitext(original_filename)
        
        filename_parts = just_filename.split('_')
        image_number = int(filename_parts[-1])

        found_match = False
        current_index = last_matched_index
        for filesystem_image in itertools.islice(filesystem_images, last_matched_index, None):
            filesystem_image_number = filesystem_image[2]
            if image_number == filesystem_image_number:
                last_matched_index = current_index
                found_match = True
                
                filesystem_imagename = filesystem_image[1]
                just_filesystem_imagename = os.path.splitext(filesystem_imagename)[0]
                new_log_filename = just_filesystem_imagename + extension
                matched_log_contents.append(("{0:.4f}".format(utc_time), new_log_filename))
                
                break
            
            current_index += 1
                
        if not found_match:
            print "Couldn't find image on file system corresponding to log file line {} time {} filename {}".format(line_num, utc_time, original_filename)
        
    print "Matched {} out of {} log file names to actual image names.".format(len(matched_log_contents), len(log_contents))
        
    log_just_filename, log_extension = os.path.splitext(image_log_filename)
    output_filename = "{}_matched{}".format(log_just_filename, log_extension)
    output_filepath = os.path.join(output_directory, output_filename)
    print "Writing results to {}".format(output_filepath)
    with open(output_filepath, 'w') as out_file:
        for line in matched_log_contents:
            out_file.write("{},{}\n".format(line[0], line[1]))
    

