import os, sys
import pathlib
import importlib
import adsk.core, adsk.fusion, traceback

# install packages
def installPackages(packages_to_install = []):
    try:
        [importlib.import_module(_) for _ in packages_to_install]
    except:
        install_str = sys.path[0] +'\\Python\\python.exe -m pip install ' + ' '.join(packages_to_install)
        os.system('cmd /c "' + install_str + '"')
        [importlib.import_module(_) for _ in packages_to_install]

installPackages(['numpy'])

# Local imports
from .loc_utils import *

DIR = pathlib.Path(__file__).parent.resolve()

class NACAInterface():
    def __init__(self, app) -> None:
        self.naca : NACA4 = None
        self.app = app
        self.ui = app.userInterface
        self.points = []  # TODO: replace with NACA object

    def promptNACA(self) -> None:
        naca_str = ''
        while len(str(naca_str)) != 4:
            naca_str, status = self.ui.inputBox('Enter NACA airfoil', 'NACA', '0012')
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
        sketch = rootComp.sketches.add(rootComp.xZConstructionPlane)  # in the XZ plane
        points = adsk.core.ObjectCollection.create()  # object collection that contains points

        # Define the points the spline with fit through.
        for x, y in self.points:
            points.add(adsk.core.Point3D.create(x, y, 0))
        
        # draw the spline
        spline = sketch.sketchCurves.sketchFittedSplines.add(points)


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    
    # Make the user enter a NACA input
    interface = NACAInterface(app)
    interface.promptNACA()
    interface.pointsFromNACA()
    interface.addNACAtoPlane()

