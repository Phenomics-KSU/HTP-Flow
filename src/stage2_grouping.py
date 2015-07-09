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
from item_extraction import *
from image_utils import *
from item_processing import *

if __name__ == '__main__':
    '''Group codes into rows/groups/segments.'''

    parser = argparse.ArgumentParser(description='''Group codes into rows/groups/segments.''')
    parser.add_argument('group_info_file', help='file with group numbers and corresponding number of plants.')
    #parser.add_argument('path_file', help='file with path position information used for segmenting rows.')
    parser.add_argument('input_directory', help='directory containing pickled files from previous stage.')
    parser.add_argument('field_direction', help='Planting angle of entire field.  0 degrees East and increases CCW.')
    parser.add_argument('output_directory', help='where to write output files')
    
    args = parser.parse_args()
    
    # convert command line arguments
    group_info_file = args.group_info_file
    #path_file = args.path_file
    input_directory = args.input_directory
    field_direction = args.field_direction
    output_directory = args.output_directory
    
    # Parse in group info
    grouping_info = parse_grouping_file(group_info_file)
    print "Parsed {0} groups. ".format(len(grouping_info))
    
    # Warn if there are duplicate groups in info file.
    grouping_info_ids = [g[0] for g in grouping_info]
    for id, count in Counter(grouping_info_ids).most_common():
        if count > 1:
            print "ERROR: found {} groups with id {} in {}".format(count, id, group_info_file)
            sys.exit(1)

    # Unpickle geo images.
    stage1_filenames = [f for f in os.listdir(input_directory) if os.path.isfile(f)]
    geo_images = []
    for stage1_filename in stage1_filenames:
        stage1_filepath = os.path.join(input_directory, stage1_filename)
        with open(stage1_filepath) as stage1_file:
            file_geo_images = pickle.load(stage1_file)
            print 'Loaded {} geo images from {}'.format(len(file_geo_images), stage1_filename)
            geo_images += file_geo_images
            
    if len(geo_images) == 0:
        print "Couldn't load any geo images from input directory {}".format(input_directory)
        sys.exit(1)
    
    all_codes = []
    for geo_image in geo_images:
        all_codes += [item for item in geo_image.items if 'code' in item.type.lower()]
    
    print 'Found {] codes in {} geo images.'.format(len(all_codes), len(geo_images))
    
    if len(all_codes) == 0:
        sys.exit(1)
    
    # Merge items down so they're unique.  One code with reference other instances of that same code.
    codes = merge_items(all_codes, max_distance=100)
    
    # Sanity check that multiple references of the same code are all close to each other.
    largest_separation = 0
    for code in codes:
        code_combos = itertools.combinations([code] + code.other_items, 2)
        for (code1, code2) in code_combos:
            separation = position_difference(code1.position, code2.position)
            if separation > largest_separation:
                largest_separation = separation
                
    print "Largest separation between same instances of any code is {} centimeters".format(largest_separation * 100.0)
    
    row_codes = [code for code in codes if code.type.lower() == 'rowcode']
    group_codes = [code for code in codes if code.type.lower() == 'groupcode']
    
    # Tell user how many codes are missing or if there are any extra codes.
    found_code_ids = [code.name for code in group_codes] 
    all_code_ids = [g[0] for g in grouping_info] 
    missing_code_ids = [id for id in all_code_ids if id not in found_code_ids]
    extra_code_ids = [id for id in found_code_ids if id not in all_code_ids]
    
    print "Missing {} ids.".format(len(missing_code_ids))
    if len(missing_code_ids) < 10:
        for id in missing_code_ids:
            print "missing id: {}".format(id)
            
    if len(extra_code_ids) > 0:
        print "WARNING: Found {} group codes that aren't listed in expected grouping file.".format(len(extra_code_ids))
        for id in extra_code_ids:
            print "Extra ID: {}".format(id)

    # Group row codes by row number.
    grouped_row_codes = defaultdict(list)
    for code in row_codes:
        grouped_row_codes[code.number].append(code)

    # Show user information about which rows were found and which are missing.
    sorted_row_numbers = sorted(grouped_row_codes.keys())
    smallest_row_number = sorted_row_numbers[0]
    biggest_row_number = sorted_row_numbers[-1]
    print "Found rows from {} to {}".format(smallest_row_number, biggest_row_number)
    missing_row_numbers = range(smallest_row_number, biggest_row_number+1) - sorted_row_numbers
    if len(missing_row_numbers) > 0:
        print "Missing row numbers {}".format(missing_row_numbers)
    else:
        print "No skipped row numbers."
    
    rows = []
    for row_number, codes in grouped_row_codes:
        if len(codes) == 1:
            print "Only found 1 code for row {}".format(row_number)
        elif len(codes) > 2:
            print "Found {} codes for row {}".format(len(codes), row_number)
        else:
            # Create row objects with start/end codes.
            start_code, end_code = order_row_codes(codes, field_direction)
            rows.append(Row(start_code, end_code))
            
    # Take into account how the row runs (up or back)
    
    # Create list of vectors corresponding to rows then for each QR code figure out which one it belongs to and add it to row object
    
    # For each row sort QR codes in order of row direction (up or back).
    
    # For each row create segments.
    
    # Go through segments and create groups.
    
    # Warn about bad group lengths.
    
    # Pickle
