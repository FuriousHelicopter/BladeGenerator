import os, sys
import pathlib
import importlib
import adsk.core, adsk.fusion, traceback

# install packages
def installPackages(packages_to_install):
    try:
        [importlib.import_module(_) for _ in packages_to_install]
    except:
        install_str = sys.path[0] +'\\Python\\python.exe -m pip install ' + ' '.join(packages_to_install)
        os.system('cmd /c "' + install_str + '"')
        [importlib.import_module(_) for _ in packages_to_install]

installPackages(['numpy', 'gmsh'])

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

    def addNACAtoPlane(self, plane = None):
        design = self.app.activeProduct
        rootComp = design.rootComponent  # root component (contains sketches, volumnes, etc)
        if plane is None:
            plane = rootComp.xYConstructionPlane
        sketch = rootComp.sketches.add(plane)  # in the XZ plane
        points = adsk.core.ObjectCollection.create()  # object collection that contains points

        # Define the points the spline with fit through.
        for x, y in self.points:
            points.add(adsk.core.Point3D.create(x, y, 0))
        
        # draw the spline
        spline = sketch.sketchCurves.sketchFittedSplines.add(points)
        return sketch

    def createOffsetPlane(self, offset):
        # TODO: create new plane at offset	
        design = self.app.activeProduct
        rootComp = design.rootComponent
        planes = rootComp.constructionPlanes
        planeInput = planes.createInput()
        planeInput.setByOffset(
            rootComp.xYConstructionPlane, 
            adsk.core.ValueInput.createByReal(offset)
        )
        return planes.add(planeInput)
    
    def loftProfiles(self, profileSketches):
        # Lofts together all profiles
        # TODO: see if loft is the best way to do this
        design = self.app.activeProduct
        rootComp = design.rootComponent
        
        loftFeats = rootComp.features.loftFeatures
        loftInput = loftFeats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        loftSectionsObj = loftInput.loftSections
        [loftSectionsObj.add(sketch.profiles.item(0)) for sketch in profileSketches]

        loftInput.isSolid = True
        loftInput.isClosed = False
        loftInput.isTangentEdgesMerged = True
        loftFeats.add(loftInput)


def run(context):
    app = adsk.core.Application.get()
    
    # Make the user enter a NACA input
    interface = NACAInterface(app)

    profileSketches = []
    for offset in range(0, 15, 5):
        interface.promptNACA()
        interface.pointsFromNACA()
        newPlane = interface.createOffsetPlane(offset/10)
        profileSketches.append(interface.addNACAtoPlane(newPlane))
    
    interface.loftProfiles(profileSketches)
