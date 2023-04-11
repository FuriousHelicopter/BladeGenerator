import numpy as np

import pathlib
DIR = pathlib.Path(__file__).parent.resolve()

import gmsh

from BladeGenerator.loc_utils.naca import NACA4
from BladeGenerator.loc_utils.point_generator import PointGenerator


class MeshGenerator:
    def __init__(self, h: float, NACA: NACA4, alpha=0.0, n=100):
        gmsh.initialize()
        # The script used to generate the MTC uses an older version of gmsh
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        self.h = h
        self.NACA = NACA
        self.alpha = alpha  # in radians
        self.points = None
        self.n = n
        self.code = None
        self.file_writen = False
        self.geo_loaded = False
        self.mesh_generated = False

    def getPoints(self) -> None:
        if self.points is None:
            self.points = PointGenerator(self.NACA, self.n).getPoints()

    # def loadPoints(self) -> None:
    #     if self.points is None:
    #         self.getPoints()
    #     self.points = np.round(self.points, 8)
    #     for i, (x, y) in enumerate(self.points):
    #         gmsh.model.geo.addPoint(x, y, 0, self.h, i)
    #     n = len(self.points)
    #     gmsh.model.geo.addSpline(list(range(len(self.points)))+[0], n+100)
    #     gmsh.model.geo.addCurveLoop([n+100], n + 200)
    #     gmsh.model.geo.addPlaneSurface([n + 200], n + 300)

    def loadGEOCode(self) -> None:
        if self.points is None:
            self.getPoints()
        self.points = np.round(self.points, 8)
        code = f"h = {self.h};\n"
        for i, (x, y) in enumerate(self.points):
            code += f"Point({i}) = {{{x}, {y}, 0, h}};\n"
        n = len(self.points)
        sequence = list(range(len(self.points)))+[0]
        sequence_str = [f"{i}" for i in sequence]
        code += f"Spline({n}) = {{{', '.join(sequence_str)}}};\n"
        code += f"Curve Loop({n+1}) = {{{n}}};\n"
        code += f"Plane Surface({n+2}) = {{{n+1}}};\n"

        # rotate + center the airfoil
        code += f"Rotate {{ {{0, 0, 1}}, {{0, 0, 0}}, -{self.alpha} }} {{ Surface{{{n+2}}}; Curve{{{n}}}; }}\n"
        code += f"Translate {{ 0, {np.sin(self.alpha)/2}, 0 }} {{ Surface{{{n+2}}}; Curve{{{n}}}; }}\n"

        self.code = code

    def writeGEO(self) -> None:
        if self.code is None:
            self.loadGEOCode()
        with open(f"{DIR}\\blade.geo", "w") as f:
            f.write(self.code)
        self.file_writen = True

    def loadGEO(self) -> None:
        if not self.file_writen:
            self.writeGEO()
        # load geo file
        print(f"{DIR}\\blade.geo")
        gmsh.open(f"{DIR}\\blade.geo")

    def generateMesh(self) -> None:
        if not self.geo_loaded:
            self.loadGEO()
        gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(2)
        self.mesh_generated = True

    def saveMesh(self, filename: str) -> None:
        if not self.mesh_generated:
            self.generateMesh()
        gmsh.write(filename)

if __name__ == "__main__":
    MeshGenerator(0.01, NACA4(2412)).saveMesh('test.msh')
    # Show the mesh
    gmsh.fltk.run()
    gmsh.finalize()
    
