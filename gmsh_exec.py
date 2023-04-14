"""
To run the pipeline:
- Set CONV_TIMEOUT to the desired timeout (maximum computation time per profile)
- Set the desired NACA profile and angles of attack
- Set the paths to the executables and result folder

Results: results_folder\\naca{NACA}_alpha{alpha}.csv
"""

import sys
sys.path.append("..\\")

import time
import numpy as np
import gmsh
from BladeGenerator.loc_utils.naca import NACA4
from BladeGenerator.simul_pipeline.pipeline import Pipeline


CONV_TIMEOUT = 1 * 60
K = 0.001


naca = 2412
for alpha_deg in [0, 2, 4, 6, 8, 10]:
    alpha = np.deg2rad(alpha_deg)
    print(f"\n-------\n\nStarting study for NACA{naca} @ alpha={alpha_deg}°...")
    p = Pipeline(
        # directories
        mtc_dir="E:\\MECAERO",
        gmsh2mtc_path="E:\\MECAERO\\gmsh2mtc.py",
        boundary_layer_dir="E:\\MECAERO\\BoundaryLayerMesh",
        naca_simulator_dir="E:\\MECAERO\\NACAsimulator",
        results_dir="E:\\MECAERO\\BladeGenerator\\results",
        # use_temp_airfoil=True,
        # use_temp_boundary=True
    )
    proc = p.run_pipeline(naca, alpha)
    
    current_time = CONV_TIMEOUT
    step = CONV_TIMEOUT // 60
    while current_time > 0:
        print(f"Time: {CONV_TIMEOUT - current_time}, convergence: {p.has_converged()} (>? {K})")
        if p.has_converged() < K:
            print("Converged!")
            # copy results to temp folder
        current_time -= step
        time.sleep(step)
    
    p.save_results(f"naca{naca}_alpha{alpha_deg}")

    # kill process
    proc.terminate()
    proc.kill()