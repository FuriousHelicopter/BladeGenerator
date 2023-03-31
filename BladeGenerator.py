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
        for blade_config in blades_config:
            self.blades.append(Blade(self.app, blade_config))
        for blade in self.blades:
            blade.build()
        

    

    

def run(context):
    app = adsk.core.Application.get()
    
    interface = MainHandler(app)
    
    # 1) Make the user input the config YAML file
    interface.prompt_config_file()

    # 2) Interpret the config file
    interface.interpret_config_file()

    # 3) Generate the blades
    interface.generateBlades()


    # <---- DEPRECATED ----> TODO : move to BladeGenerator class

    # # 3) Create the offset planes
    # interface.createOffsetPlanes()

    # # 4) Generate the profiles
    # interface.generateProfiles()

    # # 5) Link the profiles to form the final solid
    # interface.loftProfiles()

    # <---- !DEPRECATED ---->