#! /usr/bin/env python

import sys
import os
import argparse
import pickle
import itertools
from collections import Counter
from collections import defaultdict

# Project imports
from data import *

def remove_item(item, geo_images, image_name=None):

    for image in geo_images:
        
        if 


if __name__ == '__main__':
    ''''''

    parser = argparse.ArgumentParser(description='''''')
    parser.add_argument('input_file', help='output file from stage 1.')
    parser.add_argument('action', help='')
        
    args = parser.parse_args()
    
    # convert command line arguments
    input_filepath = args.input_file
    input_directory, input_filename = os.path.split(input_filepath)
    action = args.action

    # Unpickle input file.
    geo_images = []
    with open(input_filepath) as input_file:
        file_geo_images = pickle.load(input_file)
        print 'Loaded {} geo images from {}'.format(len(file_geo_images), input_filename)
        geo_images += file_geo_images
            
    if len(geo_images) == 0:
        print "Couldn't load any geo images from input file {}".format(input_filepath)
        sys.exit(1)
    
    all_codes = []
    for geo_image in geo_images:
        all_codes += [item for item in geo_image.items if 'code' in item.type.lower()]
    
    print 'Found {} codes in {} geo images.'.format(len(all_codes), len(geo_images))
    
    if len(all_codes) == 0:
        sys.exit(1)
    
    # Merge items down so they're unique.  One code with reference other instances of that same code.
    merged_codes = merge_items(all_codes, max_distance=2000)
    

    # Pickle
    just_input_filename, input_extension = os.path.splitext(input_filename)
    dump_filename = "{}_edited{}".format(just_input_filename, input_extension)
    dump_filepath = os.path.join(input_directory, dump_filename)
    print "Serializing {} rows to {}.".format(len(rows), dump_filepath)
    sys.setrecursionlimit(10000)
    with open(dump_filepath, 'wb') as dump_file:
        try:
            pickle.dump(rows, dump_file)
        except RuntimeError as e:
            print "Runtime error when pickling. Exception {}".format(e)
