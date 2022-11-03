"""
Keep cell dectector folder
This program will create everything.
The only required argument is the animal. By default it will work on channel=1
and downsample = True. Run them in this sequence:
    python pipeline/create_pipeline.py --animal DKXX --step 0|1|2|3|4|5
    And then:
    python pipeline/create_pipeline.py --animal DKXX channel 2|3 --step 0|1|2|3|4|5
    And then:
    python pipeline/create_pipeline.py --animal DKXX channel 1 downsample false --step 0|1|2|3|4|5
    And then:
    python pipeline/create_pipeline.py --animal DKXX channel 2|3 downsample false --step 0|1|2|3|4|5

Changes from previous pipeline version:
1. use ov cv2.imwrite instead of tiff.imwrite. This saves lots of space and works fine
2. More of the code was moved from pipeline.py to this file to make it obvious what is being run
3. I removed the greater than sign in the steps and replaced it with == to run specific methods only.
4. Fine tuned the scaled method in the cleaning process. This will save lots of RAM!!!!
5. Replaced the run_commands_with_executor with run_commands_concurrently. Much simpler!
6. Removed the insert and select from ng.process_image and replaced with a touch file in the PROGRESS_DIR,
    this will remove those 'mysql connection has gone away' errors.
7. Changed the session to a scoped session and extended the connection timeout to 12 hours.
Timing results
0. The processes that take the longest and need the most monitoring are, cleaning, aligning
and creating the neuroglancer images. The number of workers must be set correctly
otherwise the workstations will crash if the # of workers is too high. If the number
of workers is too low, the processes take too long.
1. Cleaning full resolution of 480 images on channel 1 on ratto took 5.5 hours
2. Aligning full resolution of 480 images on channel 1 on ratto took 6.8 hours
3. Running entire neuroglancer process on 480 images on channel 1 on ratto took 11.3 hours

Human intervention is required at several points in the process:
1. After create meta - the user needs to check the database and verify the images 
are in the correct order and the images look good.
2. After the first create mask method - the user needs to check the colored masks
and possible dilate or crop them.
3. After the alignment process - the user needs to verify the alignment looks good. 
increasing the step size will make the pipeline move forward in the process.
"""
import argparse
try:
    from settings import data_path, host, password, user, schema
except ImportError as fe:
    print('You must have a settings file in the pipeline directory.', fe)
    raise

from lib.pipeline import Pipeline


def run_pipeline(animal, channel, data_path, downsample, host, password, schema, step, tg, user, debug):

    pipeline = Pipeline(animal, channel, data_path, downsample, host, password, schema, tg, user, debug)

    print("RUNNING PREPROCESSING-PIPELINE WITH THE FOLLOWING SETTINGS:")
    print(f"\tprep_id:".ljust(20), f"{animal}".ljust(20))
    print(f"\tstep:".ljust(20), f"{step}".ljust(20))
    print(f"\tchannel:".ljust(20), f"{str(channel)}".ljust(20))
    print(f"\tdownsample:".ljust(20), f"{str(downsample)}".ljust(20))
    print(f"\thost:".ljust(20), f"{host}".ljust(20))
    print(f"\tschema:".ljust(20), f"{schema}".ljust(20))
    print(f"\ttg:".ljust(20), f"{str(tg)}".ljust(20))
    print(f"\tdebug:".ljust(20), f"{str(debug)}".ljust(20))
    print()

    if step == 0:
        print(f"Step {step}: prepare images for quality control.")
        pipeline.run_program_and_time(pipeline.extract_slide_meta_data_and_insert_to_database, pipeline.TASK_CREATING_META)
        pipeline.run_program_and_time(pipeline.create_web_friendly_image, pipeline.TASK_CREATING_WEB_IMAGES)
        pipeline.run_program_and_time(pipeline.extract_tifs_from_czi, pipeline.TASK_EXTRACTING_TIFFS)

    if step == 1:
        print(f"Step {step}: apply QC and prepare image masks")
        pipeline.set_task_preps()
        pipeline.run_program_and_time(pipeline.apply_QC, pipeline.TASK_APPLYING_QC)
        pipeline.run_program_and_time(pipeline.create_normalized_image, pipeline.TASK_APPLYING_NORMALIZATION)
        pipeline.run_program_and_time(pipeline.create_mask, pipeline.TASK_CREATING_MASKS)
    
    if step == 2:
        print(f"Step {step}: clean images")
        pipeline.run_program_and_time(pipeline.apply_user_mask_edits, pipeline.TASK_APPLYING_MASKS)
        pipeline.run_program_and_time(pipeline.create_cleaned_images, pipeline.TASK_CREATING_CLEANED_IMAGES)
    
    if step == 3:
        print(f"Step {step}: create histograms")
        pipeline.run_program_and_time(pipeline.make_histogram, pipeline.TASK_CREATING_HISTOGRAMS)
        pipeline.run_program_and_time(pipeline.make_combined_histogram, pipeline.TASK_CREATING_COMBINED_HISTOGRAM)

    if step == 4:
        print(f"Step {step}: align images within stack")
        pipeline.run_program_and_time(pipeline.create_within_stack_transformations, pipeline.TASK_CREATING_ELASTIX_TRANSFORM)
        transformations = pipeline.get_transformations()
        pipeline.align_downsampled_images(transformations)
        pipeline.align_full_size_image(transformations)
        pipeline.run_program_and_time(pipeline.call_alignment_metrics, pipeline.TASK_CREATING_ELASTIX_METRICS)
        pipeline.run_program_and_time(pipeline.create_section_pngs, pipeline.TASK_CREATING_ALIGNED_PNGS)
    
    if step == 5:
        print(f"Step {step}: create neuroglancer data")
        pipeline.run_program_and_time(pipeline.create_neuroglancer, pipeline.TASK_NEUROGLANCER_SINGLE)
        pipeline.run_program_and_time(pipeline.create_downsamples, pipeline.TASK_NEUROGLANCER_PYRAMID)


if __name__ == "__main__":
    steps = """
    start=0, prep, normalized and masks=1, mask, clean and histograms=2, 
     elastix and alignment=3, neuroglancer=4
     """
    parser = argparse.ArgumentParser(description="Work on Animal")
    parser.add_argument("--animal", help="Enter the animal", required=True)
    parser.add_argument("--channel", help="Enter channel", required=False, default=1)
    parser.add_argument("--downsample", help="Enter true or false", required=False, default="true")
    parser.add_argument("--step", help="steps", required=False, default=0)
    parser.add_argument("--debug", help="Enter true or false", required=False, default="false")
    parser.add_argument("--tg", help="Extend the mask to expose the entire underside of the brain", required=False, default=False)

    args = parser.parse_args()

    animal = args.animal
    channel = int(args.channel)
    downsample = bool({"true": True, "false": False}[str(args.downsample).lower()])
    step = int(args.step)
    debug = bool({"true": True, "false": False}[str(args.debug).lower()])
    tg = bool({"true": True, "false": False}[str(args.tg).lower()])

    run_pipeline(
        animal,
        channel,
        data_path,
        downsample,
        host,
        password,
        schema,
        step,
        tg,
        user,
        debug,
    )
