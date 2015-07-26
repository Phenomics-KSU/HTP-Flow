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
    field_direction = float(args.field_direction)
    output_directory = args.output_directory
    
    # Parse in group info
    grouping_info = parse_grouping_file(group_info_file)
    print "Parsed {} groups. ".format(len(grouping_info))
    
    # Warn if there are duplicate groups in info file.
    unique_grouping_info_dict = defaultdict(list)
    unique_grouping_info_list = []
    for info in grouping_info:
        unique_grouping_info_dict[info[0]].append(info)
    for id, infos in unique_grouping_info_dict.iteritems():
        if len(infos) > 2:
            print "More than 2 entries with id {}".format(id)
        elif len(infos) == 2:
            if infos[0][:-1] == infos[1][:-1]:
                print "Duplicate entries with id {}".format(id)
            else:
                print "Two different entries with id {}".format(id)
                print infos
            unique_grouping_info_list.append(infos[0])
        else: # just one unique info listing
            unique_grouping_info_list.append(infos[0])
    grouping_info = unique_grouping_info_list

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
        
    #for code in all_codes:
    #    from pprint import pprint
    #    pprint(vars(code))
    #    print "\n\n\n"
    
    # Merge items down so they're unique.  One code with reference other instances of that same code.
    merged_codes = merge_items(all_codes, max_distance=2000)
    
    merged_codes = cluster_merged_items(merged_codes, cluster_size=0.3)
    
    print '{} unique codes.'.format(len(merged_codes))
    
    # Sanity check that multiple references of the same code are all close to each other.
    largest_separation = 0
    sum_separation = 0
    sum_separation_count = 0
    for code in merged_codes:
        avg_position = average_position(code)
        code_refs = [code] + code.other_items
        for code_ref in code_refs:
            diff = position_difference(avg_position, code_ref.position)
            sum_separation += diff
            sum_separation_count += 1
            if diff > largest_separation:
                largest_separation = diff
            
        #code_combos = itertools.combinations([code] + code.other_items, 2)
        #for (code1, code2) in code_combos:
        #    separation = position_difference(code1.position, code2.position)
        #    if separation > largest_separation:
        #        largest_separation = separation
                
    average_separation = 0
    if sum_separation_count > 0:
        average_separation = sum_separation / sum_separation_count
                
    print "From average position largest separation is {} and average is {}".format(largest_separation, average_separation)
                

    # Sanity check that multiple references of the same code are all close to each other.
    '''
    seps = []
    for code in merged_codes:
        #if 'row' in code.type.lower():
        #    continue
        code_combos = itertools.combinations([code] + code.other_items, 2)
        for (code1, code2) in code_combos:
            separation = position_difference(code1.position, code2.position)
            seps.append(((code1, code2), separation))
    seps = sorted(seps, key=lambda s: s[1], reverse=True)
    worst = seps[0]
    worst_name = (worst[0][0]).name
    worst_code = [c for c in merged_codes if c.name == worst_name][0]
    code1, code2 = worst[0]
    print "worst sep for group codes {} centimeters".format(worst[1] * 100.0)
    print "code1 {} code2 {}".format(code1.parent_image_filename, code2.parent_image_filename)
    print "Worst code {} has position {} in {}".format(worst_code.name, worst_code.position, worst_code.parent_image_filename)
    for code in worst_code.other_items:
        rel_x = code.position[0] - worst_code.position[0]
        rel_y = code.position[1] - worst_code.position[1]
        rel_z = code.position[2] - worst_code.position[2]
        print "Other relative position ({},{},{}) in {}".format(rel_x, rel_y, rel_z, code.parent_image_filename)

    for sep in seps[:150]:
        code1, code2 = sep[0]
        dist = sep[1]
        print "{} in {} and  {} in {} has sep {}".format(code1.name, code1.parent_image_filename, code2.name, code2.parent_image_filename, dist)
        
    sys.exit(1)
    '''
    #worst1, worst2 = seps[0][0]
    #worst_results_filename = time.strftime("_results_worst-%Y%m%d-%H%M%S.csv")
    #worst_results_filepath = os.path.join(output_directory, worst_results_filename)
    #export_results([worst1, worst2], worst_results_filepath)
    
    #s = [s for s in merged_codes if s.name == '613'][0]
    #for c in [s] + s.other_items:
    #    print c.parent_image_filename
    
    row_codes = [code for code in merged_codes if code.type.lower() == 'rowcode']
    group_codes = [code for code in merged_codes if code.type.lower() == 'groupcode']
    
    # Tell user how many codes are missing or if there are any extra codes.
    found_code_ids = [code.name for code in group_codes] 
    all_code_ids = [g[0] for g in grouping_info] 
    missing_code_ids = [id for id in all_code_ids if id not in found_code_ids]
    extra_code_ids = [id for id in found_code_ids if id not in all_code_ids]
    
    print "Missing {} ids.".format(len(missing_code_ids))
    if len(missing_code_ids) < 30:
        for id in missing_code_ids:
            print "missing id: {}".format(id)
            
    if len(extra_code_ids) > 0:
        print "WARNING: Found {} group codes that aren't listed in expected grouping file.".format(len(extra_code_ids))
        for id in extra_code_ids:
            print "Extra ID: {}".format(id)

    # Update group codes with entry x rep
    num_matched_ids_to_info = 0
    for group_code in group_codes:
        matching_info = [info for info in grouping_info if info[0] == group_code.name]
        if len(matching_info) == 0:
            continue
        matching_info = matching_info[0]
        group_code.entry = matching_info[1]
        group_code.rep = matching_info[2]
        num_matched_ids_to_info += 1
        
    print "Updated {} group codes with entry x rep".format(num_matched_ids_to_info)

    # Group row codes by row number.
    grouped_row_codes = defaultdict(list)
    for code in row_codes:
        grouped_row_codes[code.row_number].append(code)
        
    if len(grouped_row_codes) == 0:
        print "Now rows detected."
        sys.exit(1)

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
            if start_code and end_code:
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
        if row.number in up_row_nums:
            row.direction = 'up'
        elif row.number in back_row_nums:
            row.direction = 'back'
        else:
            print "Row number {} doesn't have a defined up/back direction".format(row.number)
            sys.exit(1)

    field_passes = [rows[x:x+2] for x in xrange(0, len(rows), 2)]

    # Create list of vectors corresponding to rows then for each QR code figure out which one it belongs to and add it to row object
    #row_vectors = []
    #for row in rows:
    #    s = row.start_code.positions
    #    e = row.end_code.positions
    #    vector = (e[0]-s[0], e[1]-s[1], e[2]-s[2])
    #    row_vectors.append(row.number, vector)

    codes_with_projections = []
    for code in group_codes:
        
        min_distance = sys.float_info.max
        projection_distance = 0 # projection along closest row (in meters) from bottom of field to top.
        closest_row = None
        for row in rows:
            start_pos = row.start_code.position
            end_pos = row.end_code.position
            distance_to_code, row_projection_distance = lateral_and_projection_distance_2d(code.position, start_pos, end_pos)
            distance_to_code = abs(distance_to_code)
            if distance_to_code < min_distance:
                min_distance = distance_to_code
                projection_distance = row_projection_distance
                closest_row = row
        if closest_row is not None and min_distance < 3: # TODO remove hard-coded value
            code.row = closest_row.number
            if closest_row.number == 0:
                print "closest row has 0 number"
            codes_with_projections.append((code, projection_distance))
        else:
            code.row = -1
            print "Couldn't find a row for code {}. Closest row is {} meters away.".format(code.name, min_distance)
            
    group_segments = []
    for row in rows:
        group_codes_in_row = [code for code in codes_with_projections if code[0].row == row.number]
        if len(group_codes_in_row) == 0:
            print "No group codes in row {}.".format(row.number)
            continue
        # Sort group codes by projection distance.
        sorted_row_codes = [row.start_code]
        sorted_group_codes_in_row = sorted(group_codes_in_row, key=lambda c: c[1])
        sorted_row_codes += [code[0] for code in sorted_group_codes_in_row]
        sorted_row_codes.append(row.end_code)
        if row.direction == 'back':
            sorted_row_codes = list(reversed(sorted_row_codes))
        
        for i, code in enumerate(sorted_row_codes[:-1]):
            new_segment = PlantGroupSegment(start_code=code, end_code=sorted_row_codes[i+1])
            row.group_segments.append(new_segment)
            group_segments.append(new_segment)
        
    # Go through and organize segments.
    start_segments = []
    middle_segments = []
    end_segments = []
    single_segments = []
    for segment in group_segments:
        starts_with_row_code = segment.start_code.type.lower() == 'rowcode'
        ends_with_row_code = segment.end_code.type.lower() == 'rowcode'
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
    for end_segment in end_segments[:]: 
        
        field_pass = [fpass for fpass in field_passes if end_segment.row_number in [row.number for row in fpass]]
        
        if len(field_pass) == 0:
            print "End segment {} with row {} isn't in field pass list.".format(end_segment.start_code.name, end_segment.row_number)
            continue
        
        field_pass = field_pass[0]
        pass_index = [row.number for row in field_pass].index(end_segment.row_number)
        
        field_pass_index = field_passes.index(field_pass)
        if field_pass_index >= len(field_passes) - 1:
            print "End segment {} can't be matched since it's in the last pass. Treating as single segment.".format(end_segment.start_code.name)
            single_segments.append(end_segment)
            end_segments.remove(end_segment)
            continue
        
        next_pass = field_passes[field_pass_index+1]
        
        if len(next_pass) < 2:
            print "Pass {} doesn't contain 2 rows".format(field_pass_index+1)
            continue
        
        next_pass_index = 0 # assume inside
        if pass_index == 0:
            next_pass_index = 1 # was actually outside
            
        this_planting_row = field_pass[pass_index]
        next_planting_row = next_pass[next_pass_index]
        
        if this_planting_row.direction == next_planting_row.direction:
            single_segments.append(end_segment)
            end_segments.remove(end_segment)
            print "End segment {} in row {} can't match to row {} since both rows are in the same direction ({}).  Treating as single segment.".format(end_segment.start_code.name, this_planting_row.number, next_planting_row.number, this_planting_row.direction)
            continue
        
        if len(next_planting_row.group_segments) == 0:
            single_segments.append(end_segment)
            end_segments.remove(end_segment)
            print "End segment {} in row {} can't match to row {} since next row doesn't have any segments.  Treating as single segment.".format(end_segment.start_code.name, this_planting_row.number, next_planting_row.number)
            continue

        matching_start_segment = next_planting_row.group_segments[0]
        new_group = PlantGroup()
        new_group.add_segment(end_segment)
        new_group.add_segment(matching_start_segment)
        groups.append(new_group)
        
    # Handle single segments
    for segment in single_segments:
        new_group = PlantGroup()
        new_group.add_segment(segment)
        groups.append(new_group)
        
    print "Combined {} segments into {} groups.".format(len(group_segments), len(groups))
    
    group_seg_count = defaultdict(list)
    for group in groups:
        group_seg_count[len(group.segments)].append(group)
        
    for num_segs, groups_with_that_many_segs in group_seg_count.iteritems():
        print "{} groups with {} segments".format(len(groups_with_that_many_segs), num_segs) 
    
    # Warn about bad group lengths.
    num_good_lengths = 0 # how many groups have a close expected length
    num_bad_lengths = 0 # how many groups don't have a close expected length
    num_no_info = 0 # how many groups don'have any expected lengths
    num_too_much_info = 0 # how mnay groups have more than 1 expected lengths
    for group in groups:
        info = [i for i in grouping_info if i[0] == group.id]
        if len(info) == 0:
            #print "no expected info for group found in field {}".format(group.id)
            num_no_info += 1
            group.expected_num_plants = -1
            continue
        if len(info) > 1:
            #print "too many matches for row {} found in plant info file.".format(group.id)
            num_too_much_info += 1
            group.expected_num_plants = -1
            continue
        info = info[0]
        expected_num_plants = info[3]
        group.expected_num_plants = expected_num_plants
        spacing_between_plants = 0.9144 # meters
        spacing_for_codes = spacing_between_plants / 2.0
        expected_length = (expected_num_plants - 1) * spacing_between_plants
        expected_length += spacing_for_codes * 2 * len(group.segments) # for before and end codes for each segment
        actual_length = group.length

        max_length_difference = 5.0

        length_difference = actual_length - expected_length

        if abs(length_difference) > max_length_difference:
            #print "For group {} the actual length of {} is {} meters off from expected length {}.".format(group.id, actual_length, length_difference, expected_length)
            if length_difference > max_length_difference:
                print "Group with start code {} ({}{}) that is {} from the {} side of row {} is {} meters too long.".format(group.id,
                                                                                                                     group.entry,
                                                                                                                     group.rep,
                                                                                                                     group.start_code.number_within_row,
                                                                                                                     'south',
                                                                                                                     group.start_code.row, 
                                                                                                                     length_difference)
            num_bad_lengths += 1
        else:
            num_good_lengths += 1
    
    print "Found {} groups with close expected lengths and {} groups that aren't close.".format(num_good_lengths, num_bad_lengths)
    print "{} groups with no expected number of plants and {} with too many expected number number of plants.".format(num_no_info, num_too_much_info)
    
    # Write averaged results out to file.
    avg_results_filename = time.strftime("_results_averaged-%Y%m%d-%H%M%S.csv")
    avg_results_filepath = os.path.join(output_directory, avg_results_filename)
    avg_output_items = []
    for item in merged_codes:
        avg_item = item # copy.copy(item)
        item_references = [avg_item] + avg_item.other_items
        avg_x = np.mean([it.position[0] for it in item_references])
        avg_y = np.mean([it.position[1] for it in item_references])
        avg_z = np.mean([it.position[2] for it in item_references])
        avg_item.position = (avg_x, avg_y, avg_z)
        avg_item.area = np.mean([it.area for it in item_references])
        avg_width = np.mean([it.size[0] for it in item_references])
        avg_height = np.mean([it.size[1] for it in item_references])
        avg_item.size = (avg_width, avg_height)
        avg_output_items.append(avg_item)
    print 'Output averaged {} items'.format(len(avg_output_items))
    export_results(avg_output_items, rows, avg_results_filepath)
    print "Exported averaged results to " + avg_results_filepath

    # Pickle
    dump_filename = "stage2_rows_{}_{}.txt".format(geo_images[0].image_time, geo_images[-1].image_time)
    dump_filepath = os.path.join(output_directory, dump_filename)
    print "Serializing {} rows to {}.".format(len(rows), dump_filepath)
    sys.setrecursionlimit(10000)
    with open(dump_filepath, 'wb') as dump_file:
        try:
            pickle.dump(rows, dump_file)
        except RuntimeError as e:
            print "Runtime error when pickling. Exception {}".format(e)
