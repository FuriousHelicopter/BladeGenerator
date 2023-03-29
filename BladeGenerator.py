import os, sys
import pathlib
import importlib
import adsk.core, adsk.fusion, traceback

# install packages
def installPackages(packages_to_install):
    try:
        [importlib.import_module(pack[1]) for pack in packages_to_install]
    except:
        install_str = sys.path[0] +'\\Python\\python.exe -m pip install ' + ' '.join([pack[0] for pack in packages_to_install])
        os.system('cmd /c "' + install_str + '"')
        [importlib.import_module(pack[1]) for pack in packages_to_install]

installPackages([('numpy', 'numpy'), ('gmsh', 'gmsh'), ('pyyaml', 'yaml')]) # list format : [(pip_name, import_name), ...]

import numpy as np
import yaml

# Local imports
from .loc_utils import *

DIR = pathlib.Path(__file__).parent.resolve()

class BladeGeneratorMain():
    def __init__(self, app) -> None:
        self.naca : NACA4 = None
        self.app = app
        self.ui = app.userInterface
        #self.points = []  # TODO: replace with NACA object
        self.rails = (adsk.core.ObjectCollection.create(), adsk.core.ObjectCollection.create())  # Two extrusion rails, collection of Points

    def prompt_config_file(self) -> None:
        file_ok = False
        while not file_ok:

            # Prepare file input dialog
            fileDlg = self.ui.createFileDialog()
            fileDlg.isMultiSelectEnabled = False
            fileDlg.title = 'Select a .yml file'
            fileDlg.filter = 'YAML Files (*.yml, *.yaml)'
            
            # Show file input dialog
            dlgResult = fileDlg.showOpen()
            if dlgResult == adsk.core.DialogResults.DialogOK:
                self.filepath = fileDlg.filename
            else:
                raise SystemExit(1, 'No config file selected')
            
            # Confirmation dialog
            status = self.ui.messageBox(f'Use {self.filepath} as config file ?', 'Confirm', adsk.core.MessageBoxButtonTypes.YesNoButtonType)

            if status == adsk.core.DialogResults.DialogYes:
                file_ok = True

    def interpret_config_file(self):
        with open(self.filepath, 'r') as stream:
            self.config = yaml.safe_load(stream.read())

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

    def createOffsetPlanes(self):
        self.profiles = []
        profiles = self.config['profiles']
        for profile in profiles:
            res = Profile(
                plane = self.createOffsetPlane(profile['offset']),
                naca = NACA4(profile['naca']),
                c = profile['c'],
                angle = profile['angle'],
                offset = profile['offset']
            )
            self.profiles.append(res)
            print(res)

    @staticmethod
    def rotate(points: np.ndarray, angle: float):
        angle_rad = angle / 180 * np.pi
        derivative = np.tan(angle_rad)
        return np.array([points[:, 0], points[:, 1] + derivative*points[:, 0]]).T # Works because leading edge is at (0, 0)

    def transformedPointsFromProfile(self, profile: Profile):
        return self.rotate(
            profile.generatePoints() * profile.c, # c scaling (corde)
            profile.angle # angle rotation
        )

    def generateProfile(self, profile: Profile):
        design = self.app.activeProduct
        rootComp = design.rootComponent  # root component (contains sketches, volumnes, etc)
        plane = profile.plane
        sketch = rootComp.sketches.add(plane)  # in the XZ plane
        points = adsk.core.ObjectCollection.create()  # object collection that contains points

        # Define the points the spline with fit through.
        naca_points = self.transformedPointsFromProfile(profile)

        self.rails[0].add(adsk.core.Point3D.create(*naca_points[0], profile.offset))
        self.rails[1].add(adsk.core.Point3D.create(*naca_points[profile.n-1], profile.offset))

        for x, y in naca_points:
            p = adsk.core.Point3D.create(x, y, 0)
            points.add(p)

        # draw the spline
        spline = sketch.sketchCurves.sketchFittedSplines.add(points)
        profile.sketch = sketch

    def generateProfiles(self):
        for profile in self.profiles:
            self.generateProfile(profile) 

        # generate rails
        design = self.app.activeProduct
        rootComp = design.rootComponent  # root component (contains sketches, volumnes, etc)
        verticalSketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        [verticalSketch.sketchCurves.sketchFittedSplines.add(pts) for pts in self.rails]

    # def points_from_dat(self, filename):
    #     with open(f'{DIR}\\{filename}', 'r') as f:
    #         lines = f.readlines()
    #     self.points = PointGenerator(lines).getPoints()
    
    def loftProfiles(self):
        # Lofts together all profiles
        # TODO: see if loft is the best way to do this
        design = self.app.activeProduct
        rootComp = design.rootComponent
        
        loftFeats = rootComp.features.loftFeatures
        loftInput = loftFeats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        loftSectionsObj = loftInput.loftSections
        [loftSectionsObj.add(sketch.profiles.item(0)) for sketch in [profile.sketch for profile in self.profiles]]

        loftInput.isSolid = True
        loftInput.isClosed = False
        loftInput.isTangentEdgesMerged = True
        loftFeats.add(loftInput)


def run(context):
    app = adsk.core.Application.get()
    
    interface = BladeGeneratorMain(app)
    
    # 1) Make the user input the config YAML file
    interface.prompt_config_file()

    # 2) Interpret the config file
    interface.interpret_config_file()

    # 3) Create the offset planes
    interface.createOffsetPlanes()

    # 4) Generate the profiles
    interface.generateProfiles()

    # 5) Link the profiles to form the final solid
    # interface.loftProfiles()
