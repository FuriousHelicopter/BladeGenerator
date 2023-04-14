import sys
import time

import pandas as pd
from matplotlib import pyplot as plt
# this adds BladeGenerator to the PYTHONPATH
sys.path.append("..\\..\\")

from typing import Tuple
import os, shutil
import signal
import psutil
import glob
import subprocess
from pathlib import Path
import numpy as np
import gmsh
from BladeGenerator.loc_utils.naca import NACA4
from .gmsh_api import MeshGenerator


DIR = Path().resolve()
TEMP_DIR = DIR / "temp"
BOUNDARY_LAYER_BOX2_DEFAULT = [5.0, 0.4]


def delete_folder_contents(folder_path, delete_directory=False):
    if delete_directory:
        shutil.rmtree(folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)
    else:
        for f in glob.glob(str(folder_path / "*")):
            os.remove(f)


class Pipeline():
    def __init__(self, mtc_dir: str, gmsh2mtc_path: str, boundary_layer_dir: str, naca_simulator_dir: str, results_dir: str,
                 use_temp_airfoil=False, use_temp_boundary=False) -> None:
        self.airfoil_mesh_generator = None

        self.airfoil_mesh_name = "airfoil.msh"
        self.airfoil_mesh_path = TEMP_DIR / self.airfoil_mesh_name
        self.airfoil_mtc_path = self.airfoil_mesh_path.with_suffix(".t")

        self.mtc2gmsh_path = Path(gmsh2mtc_path)
        self.mtc_path = Path(mtc_dir) / "mtc.exe"
        self.boundary_layer_dir = Path(boundary_layer_dir)
        self.naca_simulator_dir = Path(naca_simulator_dir)

        self.results_dir = Path(results_dir)

        # Create temp directory if it doesn't exist
        Path(DIR / "temp").mkdir(parents=True, exist_ok=True)
        # delete_folder_contents(TEMP_DIR)

        self.use_temp_airfoil = use_temp_airfoil
        self.use_temp_boundary = use_temp_boundary

    def generate_airfoil_mesh(self, h: float, NACA: NACA4, alpha=0.0) -> None:
        self.airfoil_mesh_generator = MeshGenerator(h, NACA, alpha)

    def gmsh_to_mtc(self) -> None:
        # This is suboptimal (calling a python script with subprocess)
        print("\nConverting gmsh mesh to mtc mesh...")
        print(f"{self.airfoil_mesh_path} -> {self.airfoil_mtc_path}")
        subprocess.run([
            "python",
            self.mtc2gmsh_path, 
            self.airfoil_mesh_path, 
            self.airfoil_mtc_path
        ])

    def process_airfoil_mtc(self) -> None:
        print(f"\nProcessing {self.airfoil_mtc_path}...")
        p = subprocess.Popen([self.mtc_path, self.airfoil_mtc_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.communicate(input=b'0\n')

    def generate_boundary_layer_mesh(self, alpha, timeout=60) -> None:
        
        Pipeline.warn("this will override the previous results of BoundaryLayerMesh")
        # move the mtc file to the boundary layer directory
        shutil.copy(self.airfoil_mtc_path, self.boundary_layer_dir / "naca.t")

        # configure the Box2 file (it must be resized when alpha != 0)
        with open(self.boundary_layer_dir / "Box2.txt", "w") as f:
            x, y = BOUNDARY_LAYER_BOX2_DEFAULT
            f.write(f"{x} {y*(1 + np.sin(alpha))}")

        # delete old results
        delete_folder_contents(self.boundary_layer_dir / "Output")

        # Start the process for a given number of seconds (adjust timeout if needed)
        print(f"\nStarting BoundaryLayerMesh... (timemout = {timeout}s)")
        proc = subprocess.Popen([self.boundary_layer_dir / "modeles.exe", "main.mtc"], cwd=self.boundary_layer_dir,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        target_iteration = 4
        current_iteration = 0
        step = timeout//10
        while timeout > 0:
            time.sleep(step)
            timeout -= step
            result_num, result = self.get_last_BLM_result()
            current_iteration = result_num
            print(f"Current iteration: {current_iteration}")
            if current_iteration >= target_iteration:
                return
        
        # if current_iteration < target_iteration:
        #     raise TimeoutError("Timeout reached without getting target iteration, try increasing the timeout")
        
        # kill the main and generated process
        print("Killing BoundaryLayerMesh...")
        proc.terminate()
        proc.kill()

        # move the results to the temp directory
        result_num, result = self.get_last_BLM_result()
        print(f"Using latest file: iteration={result_num}, file={result}")

        if result is None:
            raise FileNotFoundError("No results yet, try increasing the timeout")
        
        print(result)
        shutil.copy(result, TEMP_DIR / "boundary_layer.t")

    def run_simulation(self) -> None:
        # move boundary layer file and airfoil file to the naca simulator directory
        Pipeline.warn("this will override the previous results of NACASimulator")
        shutil.copy(TEMP_DIR / "airfoil.t", self.naca_simulator_dir / "naca.t")
        shutil.copy(TEMP_DIR / "boundary_layer.t", self.naca_simulator_dir / "domaine.t")

        delete_folder_contents(self.naca_simulator_dir / "resultats", delete_directory=True)

        # Start the process
        print("Starting NACASimulator...")
        proc = subprocess.Popen([self.naca_simulator_dir / "cimlib_driver.exe", "main.mtc"], 
                                cwd=self.naca_simulator_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return proc

    def get_simulation_results(self, plot=False) -> Tuple[Path, Path]:
        # get the latest results
        force_dir = self.naca_simulator_dir / "resultats" / "capteurs" / "Efforts.txt"
        df = pd.DataFrame(np.loadtxt(force_dir, skiprows=2)[:, :3])
        df.columns = ["t", "cd", "cl"]
        df.to_csv(TEMP_DIR / "force.csv", index=False)

        # plot the results, first column vs second column
        if plot:
            ax1 = df.plot(x="t", y="cd", color="red", ylabel="C_d")
            ax2 = ax1.twinx()
            df.plot(ax=ax2, x="t", y="cl", color="blue", ylabel="C_l")
            plt.show()

        return df
    
    def has_converged(self) -> bool:
        # check if the simulation has converged
        try:
            df = self.get_simulation_results()
        except (FileNotFoundError, IndexError):
            return np.inf

        k = df[['cl', 'cd']][-10:].std()
        # print(f"Current std: {k}")
        return k.max() # < 0.001

    def run_pipeline(self, naca, alpha, h=0.01):
        if not self.use_temp_airfoil:
            self.generate_airfoil_mesh(h, NACA4(naca), alpha)
            self.save_mesh()
            self.gmsh_to_mtc()
            self.process_airfoil_mtc()
        else:
            print("Using temp airfoil {self.airfoil_mtc_path}}")
        
        if not self.use_temp_boundary:
            self.generate_boundary_layer_mesh(alpha)
        else:
            print(f"Using temp boundary {TEMP_DIR / 'boundary_layer.t'}")

        return self.run_simulation()

    def save_mesh(self):
        self.airfoil_mesh_generator.saveMesh(str(TEMP_DIR / self.airfoil_mesh_name))

    def save_results(self, name):
        shutil.copy(TEMP_DIR / "force.csv", self.results_dir / f"{name}.csv")

    def warn(message: str) -> None:
        print("WARNING: " + message)
        # if input("Continue ? [Y/n]").lower() not in ["", "y", " "]:
        #     raise SystemExit(1, "User stopped execution")
        
    def get_last_BLM_result(self) -> Tuple[int, Path]:
        files = glob.glob(str(self.boundary_layer_dir / "Output" / "*.t"))
        if len(files) == 0:
            return (0, None)
        
        p = Path(sorted(files)[-1])
        return int(p.stem.split("_")[-1]), p
