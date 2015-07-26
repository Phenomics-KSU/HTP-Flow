#! /usr/bin/env python

import sys
import os
import argparse
import pickle
import itertools
import copy
from collections import Counter
from collections import defaultdict

# Project imports

if __name__ == '__main__':
    '''Group codes into rows/groups/segments.'''

    parser = argparse.ArgumentParser(description='''Group codes into rows/groups/segments.''')
    parser.add_argument('stage1_output_filename', help='path containing pickled files from stage 1.')
    
    args = parser.parse_args()
    
    # convert command line arguments
    stage1_filepath = args.stage1_output_filename

    # Unpickle geo images.
    geo_images = []
    with open(stage1_filepath) as stage1_file:
        file_geo_images = pickle.load(stage1_file)
        print 'Loaded {} geo images from {}'.format(len(file_geo_images), stage1_filepath)
        geo_images += file_geo_images
            
    if len(geo_images) == 0:
        print "Couldn't load any geo images from {}".format(stage1_filepath)
        sys.exit(1)
        
    for image in geo_images:
        for item in image.items:
            item.other_items = []

    
    '''
    num_duplicates = 0
    unique_items = []
    for image in geo_images:
        for item in image.items:
            if item.name == '95':
                print "{} in {} pos {}".format(item.name, item.parent_image_filename, item.position)
            duplicate = False
            for unique_item in unique_items:
                if item.position == unique_item.position:
                    duplicate = True
                    num_duplicates += 1
            if not duplicate:
                unique_items.append(item)

    print str(num_duplicates)
    sys.exit(1)

        
    num_duplicates = 0
    for image in geo_images:
        for item in image.items:
            unique_other_items = []
            for other_item in item.other_items:
                duplicate = False
                for unique_item in unique_other_items:
                    if other_item.position == unique_item.position:
                        duplicate = True
                        num_duplicates += 1
                if not duplicate:
                    unique_other_items.append(other_item)
            item.other_items = unique_other_items
        
    if num_duplicates == 0:
        print "No duplicates found. Exiting."
    '''
        
    in_directory, in_filename = os.path.split(stage1_filepath)
    just_filename, ext = os.path.splitext(in_filename)
    out_filename = "{}_removed{}".format(just_filename, ext)
    out_filepath = os.path.join(in_directory, out_filename)
    with open(out_filepath, 'wb') as dump_file:
        pickle.dump(geo_images, dump_file)