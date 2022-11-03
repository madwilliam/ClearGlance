import os
from multiprocessing.pool import Pool
import numpy as np
from datetime import datetime
from utilities.utilities_process import workernoshell
from Controllers.SqlController import SqlController
from cell_extractor.CellDetectorBase import CellDetectorBase
from multiprocessing.pool import Pool
import tqdm
import shutil


class TiffSegmentor(CellDetectorBase):
    def __init__(self, animal, n_workers=10, *args, **kwargs):
        super().__init__(animal, *args, **kwargs)
        self.detect_annotator_person_id()
        self.n_workers = n_workers

    def detect_annotator_person_id(self):
        Ed = 1
        Beth = 2
        Hannah = 3
        self.person_id = None
        for person_id in [Beth, Hannah, Ed]:
            search_dictionary = {
                "FK_prep_id": self.animal,
                "FK_annotator_id": person_id,
                "FK_cell_type_id": 1,
            }
            has_annotation = self.sqlController.get_marked_cells(search_dictionary)
            if has_annotation != []:
                self.person_id = person_id

    def get_save_folders(self, save_directory):
        files = os.listdir(self.tif_directory)
        self.save_folders = []
        for filei in files:
            file_name = filei[:-4]
            save_folder = os.path.join(save_directory, file_name)
            self.save_folders.append(save_folder)

    def create_directories_for_channeli(self, channel):
        self.channel = channel
        os.path.join(self.path.prep)
        self.tif_directory = self.path.get_full_aligned(self.channel)
        self.save_directory = self.ANIMAL_PATH + f"/CH{self.channel}/"
        if not os.path.exists(self.save_directory):
            os.mkdir(self.save_directory)
        self.get_save_folders(self.save_directory)
        for save_folder in self.save_folders:
            if not os.path.exists(save_folder):
                os.mkdir(save_folder)

    def generate_tiff_segments(self, channel, create_csv=False):
        print(f"generate segment for channel: {channel}")
        self.create_directories_for_channeli(channel)
        tif_directory = self.path.get_full_aligned(channel)
        commands = []
        for save_folder in self.save_folders:
            filei = "/" + save_folder[-3:] + ".tif"
            file_name = save_folder[-3:]
            if create_csv:
                if self.person_id != None:
                    self.create_sectioni_csv(save_folder, int(file_name))
                if len(os.listdir(save_folder)) >= 10:
                    continue
            else:
                if len(os.listdir(save_folder)) == 10:
                    continue
            cmd = [
                f"convert",
                tif_directory + filei,
                "-compress",
                "LZW",
                "-crop",
                f"{self.ncol}x{self.nrow}-0-0@",
                "+repage",
                "+adjoin",
                f"{save_folder}/{file_name}tile-%d.tif",
            ]
            commands.append(cmd)
        print(f"working on {len(commands)} sections")
        with Pool(self.n_workers) as p:
            for _ in tqdm.tqdm(p.map(workernoshell, commands), total=len(commands)):
                pass

    def have_csv_in_path(self, path):
        files = os.listdir(path)
        return np.any([".csv" in filei for filei in files])

    def create_sectioni_csv(self, save_path, sectioni):
        time_stamp = datetime.today().strftime("%Y-%m-%d")
        csv_path = save_path + f"/{self.animal}_premotor_{sectioni}_{time_stamp}.csv"
        if not self.have_csv_in_path(save_path):
            search_dictionary = {
                "FK_prep_id": self.animal,
                "FK_annotator_id": self.person_id,
                "FK_cell_type_id": 1,
                "z": int(sectioni * 20),
            }
            premotor = self.sqlController.get_marked_cells(search_dictionary)
            if premotor != []:
                print("creating " + csv_path)
                np.savetxt(
                    csv_path,
                    premotor,
                    delimiter=",",
                    header="x,y,Section",
                    comments="",
                    fmt="%f",
                )

    def move_full_aligned(self):
        os.makedirs(self.ORIGINAL_IMAGE, exist_ok=True)
        for channeli in [1, 3]:
            self.tif_directory = self.path.get_full_aligned(channeli)
            ch_dir = os.path.join(self.ORIGINAL_IMAGE, f"CH{channeli}")
            nfiles_birdstore = len(os.listdir(self.tif_directory))
            nfiles_disk = len(os.listdir(ch_dir))
            if not os.path.exists(ch_dir) or nfiles_disk != nfiles_birdstore:
                shutil.rmtree(ch_dir)
                shutil.copytree(self.tif_directory, ch_dir)

    def delete_full_aligned(self):
        for channeli in [1, 3]:
            ch_dir = os.path.join(self.ORIGINAL_IMAGE, f"CH{channeli}")
            if os.path.exists(ch_dir):
                os.remove(ch_dir)
