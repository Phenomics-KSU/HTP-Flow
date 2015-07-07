#! /usr/bin/env python

import sys
import os
import argparse

def is_number(s):
    '''Return true if s is a number.'''
    try:
        float(s)
        return True
    except ValueError:
        return False

if __name__ == '__main__':
    '''Rename image filenames.'''
    
    default_old_prefix = 'IMG'
    parser = argparse.ArgumentParser(description='Rename image filenames. Must be prefix_#.extension')
    parser.add_argument('input_directory', help='Where to search for files to rename.')
    parser.add_argument('new_prefix', help='Prefix for image number to occur before image number.')
    parser.add_argument('-o', dest='old_prefix', default=default_old_prefix, help='Original prefix to replace.  Default {0}'.format(default_old_prefix))
    args = parser.parse_args()
    
    # Convert command line arguments
    input_directory = args.input_directory
    new_prefix = args.new_prefix
    old_prefix = args.old_prefix
    
    if not os.path.exists(input_directory):
        print "Directory does not exist: {0}".format(input_directory)
        sys.exit(1)

    filenames = os.listdir(input_directory)
    
    number_renamed = 0 # How many images are successfully renamed
    
    for filename in filenames:
        i = filename.rfind('_')
        if i == -1:
            print 'Skipping {0}. Does not contain underscore.'.format(filename)
            continue
        
        prefix = filename[:i]
        if prefix != old_prefix:
            print 'Skipping {0}. Prefix {1} does not match old prefix of {2}'.format(filename, prefix, old_prefix)
            continue
        
        p = filename.rfind('.')
        
        if p == -1:
            print 'Skipping {0}. No extension.'.format(filename)
            continue
        
        image_number = filename[i+1:p]
        
        if not is_number(image_number):
            print 'Skipping {0}. Expected image number {1} is not an integer.'.format(filename, image_number)
            continue
            
        extension = filename[p+1:]
        
        # Rename file since it passes all the tests.
        new_filename = '{0}_{1}.{2}'.format(new_prefix, image_number, extension)
        old_filepath = os.path.join(input_directory, filename)
        new_filepath = os.path.join(input_directory, new_filename)
        os.rename(old_filepath, new_filepath)
        
        number_renamed += 1
        
    print 'Renamed {0} files.'.format(number_renamed)