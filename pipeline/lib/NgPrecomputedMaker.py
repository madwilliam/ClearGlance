import os
from skimage import io
from utilities.utilities_cvat_neuroglancer import NumpyToNeuroglancer, calculate_chunks
from utilities.utilities_process import SCALING_FACTOR, test_dir


class NgPrecomputedMaker:
    """Class to convert a tiff image stack to the precomputed 
    neuroglancer format deviced in Seung lab"""

    def get_scales(self):
        """returns the scanning resolution for a given animal.  
        The scan resolution and sectioning thickness are retrived from the database.
        The resolution in the database is stored as micrometers (microns -um). But
        neuroglancer wants nanometers so we multipy by 1000

        Returns:
            list: list of converstion factors from pixel to micron for x,y and z
        """
        db_resolution = self.sqlController.scan_run.resolution
        zresolution = self.sqlController.scan_run.zresolution
        resolution = int(db_resolution * 1000) 
        if self.downsample:
          resolution = int(db_resolution * 1000 * SCALING_FACTOR)
 
        scales = (resolution, resolution, int(zresolution * 1000))
        return scales

    def get_file_information(self, INPUT, PROGRESS_DIR):
        """getting the information of files in the directory

        Args:
            INPUT (str): path to input directory

        Returns:
            str: name of the tif images corresponding to the section in the middle of the stack
            list: list of id and filename tuples for the files in the directory
            tuple: tuple of integers for the width,height and number of sections in the stack
            int: number of channels present in each tif files
        """
        files = sorted(os.listdir(INPUT))
        midpoint = len(files) // 2
        midfilepath = os.path.join(INPUT, files[midpoint])
        midfile = io.imread(midfilepath, img_num=0)
        height = midfile.shape[0]
        width = midfile.shape[1]
        num_channels = midfile.shape[2] if len(midfile.shape) > 2 else 1
        file_keys = []
        volume_size = (width, height, len(files))
        orientation = self.sqlController.histology.orientation
        for i, f in enumerate(files):
            filepath = os.path.join(INPUT, f)
            file_keys.append([i, filepath, orientation, PROGRESS_DIR])
        return midfile, file_keys, volume_size, num_channels

    def create_neuroglancer(self):

        """create the Seung lab cloud volume format from the image stack"""
        progress_id = self.sqlController.get_progress_id(self.downsample, self.channel, "NEUROGLANCER")

        if self.downsample:
            INPUT = self.fileLocationManager.get_thumbnail_aligned(channel=self.channel)
        if not self.downsample:
            INPUT = self.fileLocationManager.get_full_aligned(channel=self.channel)
            self.sqlController.set_task(self.animal, progress_id)

        OUTPUT_DIR = self.fileLocationManager.get_neuroglancer(self.downsample, self.channel)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        PROGRESS_DIR = self.fileLocationManager.get_neuroglancer_progress(self.downsample, self.channel)
        os.makedirs(PROGRESS_DIR, exist_ok=True)

        starting_files = test_dir(self.animal, INPUT, self.section_count, self.downsample, same_size=True)
        self.logevent(f"INPUT FOLDER: {INPUT}")
        self.logevent(f"CURRENT FILE COUNT: {starting_files}")
        self.logevent(f"OUTPUT FOLDER: {OUTPUT_DIR}")

        midfile, file_keys, volume_size, num_channels = self.get_file_information(INPUT, PROGRESS_DIR)
        chunks = calculate_chunks(self.downsample, -1)
        scales = self.get_scales()
        self.logevent(f"CHUNK SIZE: {chunks}; SCALES: {scales}")
        ng = NumpyToNeuroglancer(
            self.animal,
            None,
            scales,
            "image",
            midfile.dtype,
            num_channels=num_channels,
            chunk_size=chunks,
        )
        
        ng.init_precomputed(OUTPUT_DIR, volume_size, progress_id=progress_id)
        workers = self.get_nworkers()
        self.run_commands_concurrently(ng.process_image, file_keys, workers)
        ng.precomputed_vol.cache.flush()

    def create_neuroglancer_zarr(self):
        """Testing with zarr files. I think using zarr files would
        only be useful with downsampled volumes at one zoom level.
        """
        import zarr
        import numpy as np

        INPUT = self.fileLocationManager.get_thumbnail_aligned(channel=self.channel)
        progress_id = self.sqlController.get_progress_id(
            self.downsample, self.channel, "NEUROGLANCER"
        )
        # self.sqlController.session.close()
        if not self.downsample:
            INPUT = self.fileLocationManager.get_full_aligned(channel=self.channel)
            self.sqlController.set_task(self.animal, progress_id)
        OUTPUT_DIR = f"/net/birdstore/Active_Atlas_Data/data_root/pipeline_data/{self.animal}/neuroglancer_data"
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        test_dir(self.animal, INPUT, self.downsample, same_size=True)
        midfile, file_keys, volume_size, num_channels = self.get_file_information(INPUT)
        files = sorted(os.listdir(INPUT))
        # chunks should really be called chunksize, the bigger the number below in chunks, the bigger the size of the chunks
        z = zarr.zeros(
            (volume_size[0], volume_size[1], volume_size[2]),
            chunks=(64, 64, 32),
            dtype="u2",
        )
        for i, f in enumerate(files):
            filepath = os.path.join(INPUT, f)
            arr = io.imread(filepath)
            arr2 = np.flip(arr, axis=1)
            arr2 = np.rot90(arr2)
            z[:, :, i] = arr2
        outfile = os.path.join(OUTPUT_DIR, f"{self.animal}.zarr")
        zarr.save(outfile, z)

    def create_neuroglancer_lite(self, INPUT, OUTPUT_DIR):
        """a light weitght version of create_neuroglancer that can process any generic images stack that is not necessarily
            generated by the pipeline

        Args:
            INPUT (str): path to input directory
            OUTPUT_DIR (str): path to output the files for the neuroglancer cloudvolume
        """
        scales = self.get_scales("DK39", self.downsample)
        midfile, file_keys, volume_size, num_channels = self.get_file_information(INPUT)
        chunks = calculate_chunks(self.downsample, -1)
        ng = NumpyToNeuroglancer(
            "Atlas",
            None,
            scales,
            "image",
            midfile.dtype,
            num_channels=num_channels,
            chunk_size=chunks,
        )
        workers = self.get_nworkers()
        ng.init_precomputed(OUTPUT_DIR, volume_size, progress_id=None)
        self.run_commands_concurrently(ng.process_image, file_keys, workers)
