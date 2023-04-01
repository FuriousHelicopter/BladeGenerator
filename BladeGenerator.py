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

class MainHandler():

    def __init__(self, app) -> None:
        self.app = app
        self.ui = app.userInterface
        self.blades : list[Blade] = []


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

    def generateBlades(self) -> None:
        blades_config = self.config['blades']
        intermediate_profiles: int = self.config['intermediate_profiles']
        for i, blade_config in enumerate(blades_config):
            self.blades.append(Blade(self.app, blade_config, intermediate_profiles, i))
        for blade in self.blades:
            blade.build()

    def generateShaftHole(self) -> None:
        """Generates the shaft cylinder."""

        # Gather & check inner shaft diameter data
        inner_shaft_diameter: float = self.config['inner_shaft_diameter']
        max_inner_radius = max([blade.min_r for blade in self.blades])
        if inner_shaft_diameter > 2*max_inner_radius:
            status = self.ui.messageBox(f'Inner shaft diameter ({inner_shaft_diameter}cm) is smaller than the blades inner profile ({2*max_inner_radius}cm). It will result in the shaft not possible to connect / non functionnal propeller. Do you want to stop process and correct the values ? (if yes, the process will terminate : you need to increase the radial offset of the blades so the min of them will be greater than the inner radius)', 'Warning', adsk.core.MessageBoxButtonTypes.YesNoButtonType)
            if status == adsk.core.DialogResults.DialogYes:
                self.ui.messageBox(f'Process aborted on incorrect inner shaft diameter!', 'Error', adsk.core.MessageBoxButtonTypes.OKButtonType)
                raise SystemExit(1, 'Incorrect inner shaft diameter')

        # Gather & check outer shaft diameter data
        min_outer_shaft_diameter: float = max([blade.min_outer_shaft_radius * 2 for blade in self.blades])
        outer_shaft_diameter_config: str = self.config['outer_shaft_diameter']
        outer_shaft_diameter: float = None
        if outer_shaft_diameter_config == 'auto':
            outer_shaft_diameter = min_outer_shaft_diameter
        else:
            outer_shaft_diameter: float = float(outer_shaft_diameter_config)
        if outer_shaft_diameter < min_outer_shaft_diameter:
            status = self.ui.messageBox(f'Outer shaft diameter ({outer_shaft_diameter}cm) is smaller than the blades inner profile ({min_outer_shaft_diameter}cm). It will result a non aerodynamic / non functionnal propeller. Do you want to continue ? (if no, the minimum value will be selected)', 'Warning', adsk.core.MessageBoxButtonTypes.YesNoButtonType)
            if status == adsk.core.DialogResults.DialogNo:
                outer_shaft_diameter = min_outer_shaft_diameter

        # Gather Y data
        max_y: float = max([blade.max_y for blade in self.blades])
        min_y: float = min([blade.min_y for blade in self.blades])
        delta_y: float = max_y - min_y
        offset_y: float = min_y
        

        root_comp = self.app.activeProduct.rootComponent

        # Create the offseted shaft construction plane
        planes = root_comp.constructionPlanes
        planeInput = planes.createInput()
        planeInput.setByOffset(
            root_comp.xZConstructionPlane, 
            adsk.core.ValueInput.createByReal(offset_y)
        )
        shaft_plane = planes.add(planeInput)
        shaft_plane.name = 'Shaft construction plane'

        # Create the shaft sketch
        shaft_sketch = root_comp.sketches.add(shaft_plane)
        shaft_sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), inner_shaft_diameter/2)
        shaft_sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), outer_shaft_diameter/2)
        shaft_sketch.name = 'Shaft sketch'

        # Extrude the shaft hole
        profile = shaft_sketch.profiles.item(1)
        extFeatures = root_comp.features.extrudeFeatures
        shaft_body = extFeatures.addSimple(profile, adsk.core.ValueInput.createByReal(delta_y), adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
        shaft_body.name = 'Shaft'
        
        

    

def run(context):
    app = adsk.core.Application.get()
    
    interface = MainHandler(app)
    
    # 1) Make the user input the config YAML file
    interface.prompt_config_file()

    # 2) Interpret the config file
    interface.interpret_config_file()

    # 3) Generate the blades
    interface.generateBlades()

    # 4) Generate the shaft hole
    interface.generateShaftHole()