import adsk.core, adsk.fusion, traceback
from .point_generator import PointGenerator


DIR = "C:\\Repositories\\BladeGenerator\\BladeGenerator\\"


class NACAInterface():
    def __init__(self, ui) -> None:
        self.naca : list[int] = []
        self.
        self.ui = ui

    def promptNACA(self) -> None:
        naca_str = ''
        while len(str(naca_str)) != 4:
            naca_str, status = self.ui.inputBox('Enter NACA airfoil', 'NACA')
            if status:
                raise SystemExit(0)
            self.naca = [int(i) for i in naca_str]

    

def run(context):
    ui = None
    try: 
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Make the user enter a NACA input
        interface = NACAInterface(ui)
        interface.promptNACA()
        print(interface.naca)

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct

        # Get the root component of the active design.
        rootComp = design.rootComponent

        # Create a new sketch on the xy plane.
        sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)

        # Create an object collection for the points.
        points = adsk.core.ObjectCollection.create()

        # Define the points the spline with fit through.
        with open(f'{DIR}airfoil.dat', 'r') as f:
            lines = f.readlines()
        
        for x, y in PointGenerator(lines).getPoints():
            points.add(adsk.core.Point3D.create(x, y, 0))

        # Create the spline.
        spline = sketch.sketchCurves.sketchFittedSplines.add(points)

        # Get spline fit points
        fitPoints = spline.fitPoints
        
        # Get the second fit point
        fitPoint = fitPoints.item(1)
        
        # If there is no the relative tangent handle, activate the tangent handle
        line = spline.getTangentHandle(fitPoint)
        if line is None:
             line = spline.activateTangentHandle(fitPoint)
                
        # Get the tangent handle           
        gottenLine = spline.getTangentHandle(fitPoint)
        
        # Delete the tangent handle
        gottenLine.deleteMe()

        # Activate the curvature handle
        # If the curvature handle activated. the relative tangentHandle is activated automatically
        activatedArc = spline.activateCurvatureHandle(fitPoint)
        
        # Get curvature handle and tangent handle
        gottenArc = spline.getCurvatureHandle(fitPoint)
        gottenLine = spline.getTangentHandle(fitPoint)
        
        # Delete curvature handle
        gottenArc.deleteMe();

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))