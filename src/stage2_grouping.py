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
    print "Parsed {} groups. ".format(len(grouping_info))
    
    # Warn if there are duplicate groups in info file.
    grouping_info_ids = [g[0] for g in grouping_info]
    for id, count in Counter(grouping_info_ids).most_common():
        if count > 1:
            print "ERROR: found {} groups with id {} in {}".format(count, id, group_info_file)
            #sys.exit(1)
    
    # Unpickle geo images.
    stage1_filenames = [f for f in os.listdir(input_directory) if os.path.isfile(os.path.join(input_directory, f))]
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
    
    print 'Found {} codes in {} geo images.'.format(len(all_codes), len(geo_images))
    
    if len(all_codes) == 0:
        sys.exit(1)
    
    # Merge items down so they're unique.  One code with reference other instances of that same code.
    merged_codes = merge_items(all_codes, max_distance=500)
    
    # Sanity check that multiple references of the same code are all close to each other.
    largest_separation = 0
    for code in merged_codes:
        code_combos = itertools.combinations([code] + code.other_items, 2)
        for (code1, code2) in code_combos:
            separation = position_difference(code1.position, code2.position)
            if separation > largest_separation:
                largest_separation = separation
                
    print "Largest separation between same instances of any code is {} centimeters".format(largest_separation * 100.0)
    
    row_codes = [code for code in merged_codes if code.type.lower() == 'rowcode']
    group_codes = [code for code in merged_codes if code.type.lower() == 'groupcode']
    
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
        grouped_row_codes[code.row_number].append(code)

    # Show user information about which rows were found and which are missing.
    sorted_row_numbers = sorted(grouped_row_codes.keys())
    smallest_row_number = sorted_row_numbers[0]
    biggest_row_number = sorted_row_numbers[-1]
    print "Found rows from {} to {}".format(smallest_row_number, biggest_row_number)
    missing_row_numbers = set(range(smallest_row_number, biggest_row_number+1)) - set(sorted_row_numbers)
    if len(missing_row_numbers) > 0:
        print "Missing row numbers {}".format(missing_row_numbers)
    else:
        print "No skipped row numbers."
        
    rows = []
    for row_number, codes in grouped_row_codes.iteritems():
        if len(codes) == 1:
            print "Only found 1 code for row {}".format(row_number)
        elif len(codes) > 2:
            print "Found {} codes for row {}".format(len(codes), row_number)
        else:
            # Create row objects with start/end codes.
            code1, code2 = codes
            start_code, end_code = orient_items(code1, code2, field_direction)
            rows.append(Row(start_code, end_code))
            
    if len(rows) == 0:
        print "No complete rows found.  Exiting."
        sys.exit(1)
        
    # Take into account how the row runs (up or back)
    # Have to change this for each field or all to pass in with args.
    first_start = 1 # first section start row
    first_end = 22 # last row number from first section
    second_start = first_end + 1 # first row number from second section (since started in wrong direction)
    second_end = 58 # last row number in field
    row_step = 4 # Goes with double planter.
    # First section
    up_row_nums = range(first_start, second_start, row_step)
    up_row_nums += range(first_start+1, second_start, row_step)
    back_row_nums = range(first_start+2, second_start, row_step)
    back_row_nums += range(first_start+3, second_start, row_step)
    # Second section
    up_row_nums += range(second_start, second_end+1, row_step)
    up_row_nums += range(second_start+1, second_end+1, row_step)
    back_row_nums += range(second_start+2, second_end+1, row_step)
    back_row_nums += range(second_start+3, second_end+1, row_step)
    
    up_row_nums = sorted(up_row_nums, key=lambda n: n)
    back_row_nums = sorted(back_row_nums, key=lambda n: n)

    overlap = list(set(up_row_nums) & set(back_row_nums))
    if len(overlap) > 0:
        print "Bad row generation.  Overlapping between up and back: "
        print overlap
        sys.exit(1)
    
    if back_row_nums[-1] != 58:
        print "Bad row generation.  Last row should be back and number 58"
        sys.exit(1) 
        
    if 22 not in up_row_nums or 23 not in up_row_nums:
        print "Bad row generation.  Back rows should have number 22"
        sys.exit(1) 

    for row in rows:
        if row.row_number in up_row_nums:
            row.direction = 'up'
        elif row.row_number in back_row_nums:
            row.direction = 'back'
        else:
            print "Row number {} doesn't have a defined up/back direction".format(row.row_number)
            sys.exit(1)

    # Create list of vectors corresponding to rows then for each QR code figure out which one it belongs to and add it to row object
    #row_vectors = []
    #for row in rows:
    #    s = row.start_code.positions
    #    e = row.end_code.positions
    #    vector = (e[0]-s[0], e[1]-s[1], e[2]-s[2])
    #    row_vectors.append(row.row_number, vector)

    codes_with_projections = []
    for code in group_codes:
        min_distance = sys.float_info.max
        projection_distance = 0 # projection along closest row (in meters) from bottom of field to top.
        closest_row = None
        for row in rows:
            start_pos = row.start_code.position
            end_pos = row.end_code.position
            distance_to_code, row_projection_distance = abs(lateral_and_projection_distance_2d(code.position, start_pos, end_pos))
            if distance_to_code < min_distance:
                min_distance = distance_to_code
                projection_distance = row_projection_distance
                closest_row = row
        if closest_row is not None and min_distance < 2: # TODO remove hard-coded value
            code.row_number = closest_row.row_number
            codes_with_projections.append((code, projection_distance))
        else:
            print "Couldn't find a row for code {}. Closest row is {} meters away.".format(code.name, min_distance)
            
    group_segments = []
    for row in rows:
        group_codes_in_row = [code for code in codes_with_projections if code[0].row_number == row.row_number]
        if len(group_codes_in_row) == 0:
            print "No group codes in row {}.".format(row.row_number)
            continue
        # Sort group codes by projection distance.
        sorted_row_codes = []
        if row.direction == 'up':
            sorted_row_codes = [row.start_code]
            sorted_row_codes += sorted(group_codes_in_row, key=lambda c: c[1])
            sorted_row_codes.append(row.end_code)
        elif row.direction == 'back':
            sorted_row_codes = [row.end_code]
            sorted_row_codes += sorted(group_codes_in_row, key=lambda c: c[1], reverse=True)
            sorted_row_codes.append(row.start_code)
        else:
            print "Bad row direction {}".format(row.direction)
            sys.exit(1)
        
        for i, code in enumerate(sorted_row_codes[:-1]):
            new_segment = PlantGroupSegment(start_code=code, end_code=sorted_row_codes[i+1])
            group_segments.append(new_segment)
        
    # Go through and organize segments.
    start_segments = []
    middle_segments = []
    end_segments = []
    single_segments = []
    for segment in group_segments:
        starts_with_row_code = segment.start_code.type.lower() == 'rowcode'
        ends_with_row_code = segment.stop_code.type.lower() == 'rowcode'
        if starts_with_row_code and ends_with_row_code:
            middle_segments.append(segment)
        elif starts_with_row_code:
            start_segments.append(segment)
        elif ends_with_row_code:
            end_segments.append(segment)
        else:
            single_segments.append(segment)
    
    if len(middle_segments) > 0:
        print "Middle segments that span entire row aren't supported right now. Exiting"
        sys.exit(1)
    
    # Complete groups.
    groups = []
    for segment in single_segments:
        new_group = PlantGroup()
        new_group.add_segment(segment)
        groups.append(new_group)
        
    for end_segment in end_segment:
        matching_start_segments = [seg for seg in start_segments if seg.end_code.name == end_segment.start_code.name]
        if len(matching_start_segments) == 0:
            print "No matching start segment for ending segment with name: ".format(end_segment.start_code.name)
        elif len(matching_start_segments) > 1:
            print "Two start segments match ending segment. Exiting"
            sys.exit(1)
        else:
            matching_start_segment = matching_start_segments[0]
            new_group = PlantGroup()
            new_group.add_segment(end_segment)
            new_group.add_segment(matching_start_segment)
            groups.append(new_group)
    
    # Warn about bad group lengths.
    for group in groups:
        info = [i for i in grouping_info if i[0] == group.id]
        expected_num_plants = info[3]
        spacing_between_plants = 0.9144 # meters
        spacing_for_codes = spacing_between_plants / 2.0
        expected_length = (expected_num_plants - 1) * spacing_between_plants
        expected_length += spacing_for_codes * 2 * len(group.segments) # for before and end codes for each segment
        actual_length = group.length
        
        max_length_difference = 3.0
        
        length_difference = actual_length - expected_length
        
        if abs(length_difference) > max_length_difference:
            print "Actual length for group {} is {} meters than expected of {}.".format(group.id, length_difference, expected_length)
    
    # Pickle
    
    sys.exit(1)
    
    # Sanity check that multiple references of the same code are all close to each other.
    seps = []
    for code in merged_codes:
        #if 'row' in code.type.lower():
        #    continue
        code_combos = itertools.combinations([code] + code.other_items, 2)
        for (code1, code2) in code_combos:
            separation = position_difference(code1.position, code2.position)
            seps.append(((code1, code2), separation))
    seps = sorted(seps, key=lambda s: s[1], reverse=True)
    for sep in seps:
        code1, code2 = sep[0]
        dist = sep[1]
        print "{} {} {}".format(code1.name, code2.name, dist)
    #worst1, worst2 = seps[0][0]
    #worst_results_filename = time.strftime("_results_worst-%Y%m%d-%H%M%S.csv")
    #worst_results_filepath = os.path.join(output_directory, worst_results_filename)
    #export_results([worst1, worst2], worst_results_filepath)
    sys.exit(1)
            
    # Write averaged results out to file.
    avg_results_filename = time.strftime("_results_averaged-%Y%m%d-%H%M%S.csv")
    avg_results_filepath = os.path.join(output_directory, avg_results_filename)
    avg_output_items = []
    for item in merged_codes:
        avg_item = item # copy.copy(item)
        item_references = [avg_item] + avg_item.other_items
        avg_x = np.mean([item.position[0] for item in item_references])
        avg_y = np.mean([item.position[1] for item in item_references])
        avg_z = np.mean([item.position[2] for item in item_references])
        avg_item.position = (avg_x, avg_y, avg_z)
        avg_item.area = np.mean([item.area for item in item_references])
        avg_width = np.mean([item.size[0] for item in item_references])
        avg_height = np.mean([item.size[1] for item in item_references])
        avg_item.size = (avg_width, avg_height)
        avg_output_items.append(avg_item)
    print 'Output averaged {} items'.format(len(avg_output_items))
    export_results(avg_output_items, avg_results_filepath)
    print "Exported averaged results to " + avg_results_filepath
