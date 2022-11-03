"""
If you need to swap out a tif. Get the section number, go to:
https://activebrainatlas.ucsd.edu/activebrainatlas/admin/brain/section/
search for the animal and then the section number and get the file name
Remove that file from DKXX/tif then run this script
python fix_missing_tif.py --animal DKXX --channel 1 --fix false 
after confirming it will be replaced, run:
python fix_missing_tif.py --animal DKXX --channel 1 --fix true
do a ls -lh DKXX/tif/filename to confirm or
python fix_missing_tif.py --animal DKXX --channel 1 --fix false 

"""
import os, sys
import argparse
from pathlib import Path

PIPELINE_ROOT = Path('.').absolute().parent
sys.path.append(PIPELINE_ROOT.as_posix())

from utilities.SqlController import SqlController
from utilities.FileLocationManager import FileLocationManager
from utilities.utilities_process import make_tif
from sql_setup import session



def directory_filled(dir, channel):
    MINSIZE = 1000
    FAILED = 'FAILED'
    badsize = False
    file_status = []
    dir_exists = os.path.isdir(dir)
    files = os.listdir(dir)
    files = [file for file in files if 'C{}.tif'.format(channel) in file]

    for file in files:
        size = os.path.getsize(os.path.join(dir, file))
        if size < MINSIZE:
            file_status.append(FAILED)

    if FAILED in file_status:
        badsize = True
    return dir_exists, len(files), badsize

def find_missing(dir, db_files):
    source_files = []
    for section in db_files:
        source_files.append(section.file_name)
    files = os.listdir(dir)
    return (list(set(source_files) - set(files)))

def fix_tifs(animal, channel):
    sqlController = SqlController(animal)
    fileLocationManager = FileLocationManager(animal)
    dir = fileLocationManager.tif
    db_files = sqlController.get_sections(animal, channel)

    source_files = []
    source_keys = []
    for tif in db_files:
        source_files.append(tif.file_name)
        source_keys.append(tif.id)
    files = os.listdir(dir)
    files = [file for file in files if 'C{}.tif'.format(channel) in file]
    missing_files =  list(set(source_files) - set(files))

    for i,missing in enumerate(missing_files):
        #pass
        file_id =  source_keys[source_files.index(missing)]
        section = sqlController.get_section(file_id)
        print(i, missing, file_id, section.id, section.file_name)
        make_tif(animal, section.tif_id, file_id, testing=False)



def test_tif(animal, channel):
    sqlController = SqlController(animal)
    checks = ['tif']
    fileLocationManager = FileLocationManager(animal)
    # tifs
    for name, dir in zip(checks, [fileLocationManager.tif]):
        db_files = sqlController.get_distinct_section_filenames(animal, channel)
        valid_file_length = db_files.count()
        dir_exists, lfiles, badsize = directory_filled(dir, channel)

        if not dir_exists:
            print("{} does not exist.".format(dir))

        missings = find_missing(dir, db_files)
        if len(missings) > 0:
            print("Missing files:")
            count = 1
            for missing in missings:
                print(count, missing)
                count += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Work on Animal')
    parser.add_argument('--animal', help='Enter the animal ID', required=True)
    parser.add_argument('--fix', help='Enter True to fix', required=False, default='False')
    parser.add_argument('--channel', help='Enter channel (1,2,3)', required=False, default=1)
    args = parser.parse_args()
    animal = args.animal
    fix = bool({'true': True, 'false': False}[args.fix.lower()])
    channel = int(args.channel)
    test_tif(animal, channel)
    if fix:
        fix_tifs(animal, channel)
        test_tif(animal, channel)
