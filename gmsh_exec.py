import sys
sys.path.append("..\\")

import numpy as np
import gmsh
from BladeGenerator.loc_utils.naca import NACA4
from BladeGenerator.simul_pipeline.pipeline import Pipeline


alpha = 10 * np.pi / 180

p = Pipeline(
    mtc_dir="E:\\MECAERO",
    gmsh2mtc_path="E:\\MECAERO\\gmsh2mtc.py",
    boundary_layer_dir="E:\\MECAERO\\BoundaryLayerMesh",
    naca_simulator_dir="E:\\MECAERO\\NACAsimulator"
)

p.generate_airfoil_mesh(0.01, NACA4(2412), 0.0)
p.save_mesh()
p.gmsh_to_mtc()
p.process_airfoil_mtc()
p.generate_boundary_layer_mesh()


# gmsh.fltk.run()
# gmsh.finalize()