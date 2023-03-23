import os, sys
import pathlib
import importlib
import adsk.core, adsk.fusion, traceback
from utils import *


DIR = pathlib.Path(__file__).parent.resolve()
print(DIR)

class NACAInterface():
    def __init__(self, app) -> None:
        self.naca : NACA4 = None
        self.app = app
        self.ui = app.userInterface
        self.points = []  # TODO: replace with NACA object

    def promptNACA(self) -> None:
        naca_str = ''
        while len(str(naca_str)) != 4:
            naca_str, status = self.ui.inputBox('Enter NACA airfoil', 'NACA')
            if status:
                raise SystemExit(0)
        self.naca = NACA4(naca_str)

    def points_from_dat(self, filename):
        with open(f'{DIR}\\{filename}', 'r') as f:
            lines = f.readlines()
        self.points = PointGenerator(lines).getPoints()

    def pointsFromNACA(self):
        self.points = PointGenerator(self.naca).getPoints()

    def addNACAtoPlane(self) -> None:
        design = self.app.activeProduct
        rootComp = design.rootComponent  # root component (contains sketches, volumnes, etc)
        sketch = rootComp.sketches.add(rootComp.zXConstructionPlane)  # in the XZ plane
        points = adsk.core.ObjectCollection.create()  # object collection that contains points

        # Define the points the spline with fit through.
        for x, y in self.points:
            points.add(adsk.core.Point3D.create(x, y, 0))
        
        # draw the spline
        spline = sketch.sketchCurves.sketchFittedSplines.add(points)


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface

    # install packages
    packages_to_install = ['numpy']
    for package in packages_to_install:
        install_str = sys.path[0] +'\\Python\\python.exe -m pip install' + package
        os.system('cmd /c "' + install_str + '"')
    
    try:
        test = importlib.import_module(packages_to_install[0])
        ui.messageBox("Installation succeeded !")
    except:
        ui.messageBox("Failed when importing numpy")


    # Make the user enter a NACA input
    interface = NACAInterface(app)
    interface.promptNACA()
    interface.pointsFromNACA()
    interface.addNACAtoPlane()

