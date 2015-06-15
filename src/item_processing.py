#! /usr/bin/env python

# Project imports
from data import *
from image_utils import *

def process_geo_images(geo_images, item_extractor, camera_rotation, image_directory, out_directory, use_marked_image):
    '''Return list of extracted items sorted in direction of movement.'''
    items = []
    for i, geo_image in enumerate(geo_images):

        print "Analyzing image {0} [{1}/{2}]".format(geo_image.file_name, i+1, len(geo_images))
        
        full_filename = os.path.join(image_directory, geo_image.file_name)
        
        image = cv.imread(full_filename, cv.CV_LOAD_IMAGE_COLOR)

        if image is None:
            print 'Cannot open image: {0}'.format(full_filename)
            continue

        # Update remaining geo image properties before doing image analysis.  This makes it so we only open image once.
        image_height, image_width, _ = image.shape
        geo_image.size = (image_width, image_height)
  
        if geo_image.resolution <= 0:
            print "Cannot calculate image resolution. Skipping image."
            continue
        
        # Specify 'image directory' so that if any images associated with current image are saved a directory is created.
        image_out_directory = os.path.join(out_directory, os.path.splitext(geo_image.file_name)[0])
        ImageWriter.output_directory = image_out_directory

        marked_image = None
        if use_marked_image:
            # Copy original image so we can mark on it for debugging.
            marked_image = image.copy()

        image_items = item_extractor.extract_items(geo_image, image, marked_image, image_out_directory)
        
        image_items = order_items(image_items, camera_rotation)
        
        print 'Found {0} items.'.format(len(image_items))
        for item in image_items:
            print "Type: {0} Name: {1}".format(item.item_type, item.name)

        items.extend(image_items)

        if marked_image is not None:
            marked_image_filename = postfix_filename(geo_image.file_name, '_marked')
            marked_image_path = os.path.join(out_directory, marked_image_filename)
            cv.imwrite(marked_image_path, marked_image)
            
    return items

def order_items(items, camera_rotation):
    '''Return new list but sorted from backward to forward taking into account camera rotation.'''
    if camera_rotation == 180:  # top to bottom
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[1])
    elif camera_rotation == 0: # bottom to top
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[1], reverse=True)
    elif camera_rotation == 90: # left to right
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[0])
    elif camera_rotation == 270: # right to left
        return sorted(items, key=lambda item: rectangle_center(item.bounding_rect)[0], reverse=True)
    else:
        return None
    
def merge_items(items, max_distance):
    '''Return new list of items with all duplicates removed and instead can be referenced through surviving items.'''
    unique_items = []
    for item in items:
        matching_item = None
        for comparision_item in unique_items:
            if is_same_item(item, comparision_item, max_distance):
                matching_item = comparision_item
                break
        if matching_item is None:
            unique_items.append(item)
        else:
            # We've already stored this same item so just have the one we stored reference this one.
            matching_item.other_items.append(item)
            
    return unique_items

def group_into_rows(items):
    '''Split items into list of rows.  Current row will be None if didn't end in middle of row.'''
    rows = []
    current_row = None
    outside_row_plants = [] # plants found not in a row.
    for item in items:
        if item.item_type == 'code-row':
            row_number = int(item.name)
            if current_row is None:
                # Start a new row.
                current_row = Row(start_code=item)
            elif row_number == current_row.number:
                # Ending current row.
                current_row.end_code = item
                current_row = None
                rows.append(current_row)
                continue
            else:
                # Unexpectedly hit next row.  Likely missed row end QR code.
                print "HIT NEXT ROW!!!" # TODO ask user for correction
        else: # item isn't a row end code.
            if current_row is not None:
                current_row.items.append(item)
            else: # Not in a row.
                if item.item_type == 'code-group':
                    # Hit a QR code outside of row.  This means we likely missed the row start code.
                    print "HIT QR GROUP CODE OUTSIDE OF ROW!!!" # TODO have user fix
                else:
                    # This means item is a false positive plant since it occurred outside of row.
                    outside_row_plants.append(item)
                    
    return rows, current_row, outside_row_plants

def split_into_plant_groupings(rows):
    '''Return list of plant groups.'''
    plant_groups = []
    for row in rows:
        print "Finding plant groupings in row {0}".format(row.number)
        
        current_group = None
        for item in row.items:
            if item.item_type == 'code-group':
                if current_group is not None:
                    # End current group.
                    plant_groups.append(current_group)
                    current_group = None
                    
                # Start a new group.
                current_group = PlantGroup(start_code=item)

            else: # item is a plant since it's not a code.
                if current_group is None:
                    # TODO: Need to look up and add to previous group from 2 rows ago.
                    print "TODO: Hit plant in row before group"
                else:
                    current_group.plants.append(item)
                    
    return plant_groups

def correct_plant_groupings(plant_groups, grouping_info):
    '''Correct plant groups to match specified grouping info.'''
    for group in plant_groups:
        # Find expected number of plants in group so we can do validations/corrections.
        try:
            grouping_index = [y[0] for y in grouping_info].index(group.name)
            expected_num_plants = grouping_info[grouping_index][1]
        except ValueError:
            # TODO handle better
            print 'WARNING: Group {0} not found in provided group list. Skipping.'.format(group.name)
            continue
        
        # First need to make actual/expected number of plants match.
        num_plants = len(group.plants)

        if num_plants > expected_num_plants:
            pass # group = remove_false_positive_plants(group, expected_num_plants)
        elif num_plants < expected_num_plants:
            pass # group = add_missing_plants(group, expected_num_plants)
            
        # Now fill in any gaps.
        #group = include_gaps(group)