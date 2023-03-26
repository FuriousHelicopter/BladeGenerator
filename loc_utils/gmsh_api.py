import numpy as np

import pathlib
DIR = pathlib.Path(__file__).parent.resolve()

import gmsh

from .naca import NACA4
from .point_generator import PointGenerator


class MeshGenerator:
    def __init__(self, h: float, NACA: NACA4, n=100):
        gmsh.initialize()
        self.h = h
        self.NACA = NACA
        self.points = None
        self.n = n
        self.code = None

    def __getPoints(self) -> None:
        self.points = PointGenerator(self.NACA, self.n).getPoints()

    def __loadGEOCode(self) -> None:
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
        self.code = code

    def __writeGEO(self) -> None:
        with open(f"{DIR}\\blade.geo", "w") as f:
            f.write(self.code)
        self.file_writen = True

    def __loadGEO(self) -> None:
        print(f"{DIR}\\blade.geo")
        gmsh.open(f"{DIR}\\blade.geo")

    def __generateMesh(self) -> None:
        gmsh.model.geo.synchronize()
        gmsh.model.mesh.generate(2)
        self.mesh_generated = True

    def __saveMesh(self, filename: str) -> None:
        gmsh.write(filename)

    def generateAndWriteMesh(self, filename: str) -> None:
        self.__getPoints()
        self.__loadGEOCode()
        self.__writeGEO()
        self.__loadGEO()
        self.__generateMesh()
        self.__saveMesh(filename)

if __name__ == "__main__":
    MeshGenerator(0.01, NACA4(2412)).generateAndWriteMesh('test.msh')
    gmsh.fltk.run()
    gmsh.finalize()
    
