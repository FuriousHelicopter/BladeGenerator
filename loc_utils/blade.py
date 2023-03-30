import adsk.core, adsk.fusion
import numpy as np

# Local imports
from .naca import NACA4
from .profile import Profile

class Blade():
    def __init__(self, app, blade_config: dict) -> None:
        # Blade configuration
        self.angle: float = blade_config['angle'] / 180 * np.pi
        self.profiles_dict: dict = blade_config['profiles']
        self.colinear_blade_offset: float = blade_config['colinear_blade_offset']
        
        # API objects
        self.app = app
        self.ui = app.userInterface
        self.rails = (adsk.core.ObjectCollection.create(), adsk.core.ObjectCollection.create())  # Two extrusion rails, collection of Points
        

    def __createOffsetPlane(self, offset) -> adsk.fusion.ConstructionPlane:
        """Create a new offset plane and return it."""
        design = self.app.activeProduct
        rootComp = design.rootComponent
        planes = rootComp.constructionPlanes
        planeInput = planes.createInput()
        planeInput.setByOffset(
            rootComp.xYConstructionPlane, 
            adsk.core.ValueInput.createByReal(offset)
        )
        return planes.add(planeInput)

    def __createOffsetPlanesAndGenerateProfilesObject(self) -> None:
        """Create all the offset planes from the interpretation of the self.profiles dict."""
        self.profiles = []
        for profile_config in self.profiles_dict:
            res = Profile(
                plane = self.__createOffsetPlane(profile_config['offset']),
                naca = NACA4(profile_config['naca']),
                c = profile_config['c'],
                angle = profile_config['angle'],
                offset = profile_config['offset'],
                colinear_offset = profile_config['colinear_offset']
            )
            self.profiles.append(res)

    def __generateProfile(self, profile: Profile) -> None:
        """Generates a profile in the 3D modeling from a profile object."""

        design = self.app.activeProduct
        rootComp = design.rootComponent  # root component (contains sketches, volumnes, etc)
        
        # Getting the plane object created earlier
        plane = profile.plane
        
        # Creating a sketch from the plane
        sketch = rootComp.sketches.add(plane)  # in the XZ plane
        # Creating a point collection
        points = adsk.core.ObjectCollection.create()  # object collection that contains points

        # Define the points the spline with fit through.
        naca_points = profile.getPoints()

        # Generating the rails points to guide the future loft (took the 2 outer points)
        self.rails[0].add(adsk.core.Point3D.create(*naca_points[0], profile.offset))
        self.rails[1].add(adsk.core.Point3D.create(*naca_points[profile.n-1], profile.offset))

        # Adding the points to the collection (i.e. to the sketch)
        for x, y in naca_points:
            p = adsk.core.Point3D.create(x, y, 0)
            points.add(p)

        # Drawing the spline
        sketch.sketchCurves.sketchFittedSplines.add(points)
        profile.sketch = sketch

    def __generateProfiles(self) -> None:
        """Generates all the profiles in the 3D modeling from the self.config dict."""
        for profile in self.profiles:
            self.__generateProfile(profile) 

        # generate rails
        design = self.app.activeProduct
        rootComp = design.rootComponent  # root component (contains sketches, volumnes, etc)
        self.verticalSketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        self.c1, self.c2 = [self.verticalSketch.sketchCurves.sketchFittedSplines.add(pts) for pts in self.rails]

        
    
    def __loftProfiles(self) -> None:
        """Lofts together all profiles i.e. form the solid defined by the profiles"""

        design = self.app.activeProduct
        rootComp = design.rootComponent
        
        # Creating the different objects to call the loft function
        loftFeats = rootComp.features.loftFeatures
        loftInput = loftFeats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    
        # Create rails (guides) in order to avoid creating funny looking shapes when lofting
        loftRails = loftInput.centerLineOrRails
        loftRails.addRail(self.c1)
        loftRails.addRail(self.c2)

        # Adding all the profiles to the loft
        loftSectionsObj = loftInput.loftSections
        [loftSectionsObj.add(sketch.profiles.item(0)) for sketch in [profile.sketch for profile in self.profiles]]

        # Setting the loft parameters
        loftInput.isSolid = True
        loftInput.isClosed = False
        loftInput.isTangentEdgesMerged = True

        # Creating the loft
        self.entity = loftFeats.add(loftInput).bodies.item(0)

    def __translateSelf(self) -> None:
        # radius_offsets = [profile.offset for profile in self.profiles]
        # closest_profile = self.profiles[np.argmin(radius_offsets)]
        closest_profile = min(self.profiles, key=lambda profile: profile.offset)
        closest_delta_x = np.max(closest_profile.points[::, 0]) - np.min(closest_profile.points[::, 0])
        print(closest_delta_x)
        moveFeats = self.app.activeProduct.rootComponent.features.moveFeatures
        toMove = adsk.core.ObjectCollection.create()
        toMove.add(self.entity)

        transform = adsk.core.Matrix3D.create()
        transform.translation = adsk.core.Vector3D.create(-closest_delta_x/2, 0, self.colinear_blade_offset)
        moveInput = moveFeats.createInput(toMove, transform)
        moveFeats.add(moveInput)

    def __rotateSelf(self) -> None:
        """Rotates the blade around the X axis by self.angle degrees."""
        # raise NotImplementedError("This method is not implemented yet.") # TODO : implement it, code generated by copilot below
        
        # Create transform object
        transform = adsk.core.Matrix3D.create()
        transform.setToRotation(
            angle = self.angle,
            axis = adsk.core.Vector3D.create(0, 1, 0),
            origin = adsk.core.Point3D.create(0, 0, 0)
        )

        # Create a move feature
        moveFeats = self.app.activeProduct.rootComponent.features.moveFeatures
        toMove = adsk.core.ObjectCollection.create()
        toMove.add(self.entity)
        moveInput = moveFeats.createInput(toMove, transform)
        moveFeats.add(moveInput)

    def __hideConstruction(self) -> None:
        """Hides all the construction planes and sketches."""
        for profile in self.profiles:
            profile.plane.isLightBulbOn = False
            profile.sketch.isLightBulbOn = False
        self.verticalSketch.isLightBulbOn = False


    def build(self) -> None:
        """Builds the blade from the config dict."""
        self.__createOffsetPlanesAndGenerateProfilesObject()
        self.__generateProfiles()
        self.__hideConstruction()
        self.__loftProfiles()
        self.__translateSelf()
        self.__rotateSelf()
        
