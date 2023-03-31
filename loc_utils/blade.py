import adsk.core, adsk.fusion
import numpy as np

# Local imports
from .naca import NACA4
from .profile import Profile
from .profile_config import ProfileConfig

RAIL_NS = ["0", "X-1", "int(X//2)", "3*int(X//2)", "int(X//4)", "3*int(X//4)", "5*int(X//4)", "7*int(X//4)"] # where X is half the number of points in the profile

class Blade():
    def __init__(self, app, blade_config: dict, intermediate_profiles: int) -> None:
        # Blade configuration
        self.angle: float = blade_config['angle'] / 180 * np.pi
        self.profiles_dict: dict = blade_config['profiles']
        self.colinear_blade_offset: float = blade_config['colinear_blade_offset']
        self.intermediate_profiles: int = intermediate_profiles
        
        # API objects
        self.app = app
        self.ui = app.userInterface
        self.rails = [adsk.core.ObjectCollection.create() for _ in range(len(RAIL_NS))]  # len(RAIL_NS) extrusion rails, collection of Points
        
        self.rail_splines = []
        self.profiles_config: list[ProfileConfig] = []

    def __load_config(self) -> None:
        """Create profileConfig objects from the self.profiles_dict and create self.profilesConfig list."""
        for profile_config in self.profiles_dict:
            self.profiles_config.append(ProfileConfig(
                radial_offset = profile_config['offset'],
                naca = NACA4(profile_config['naca']),
                c = profile_config['c'],
                angle = profile_config['angle'],
                colinear_offset = profile_config['colinear_offset']
            ))

    def __interpolate_profiles(self) -> None:
        """Interpolate the profiles and complete the self.profilesConfig list."""
        if self.intermediate_profiles == 0:
            return
        for i in range(len(self.profiles_config) - 1):
            for j in range(self.intermediate_profiles):
                j += 1
                t = j / (self.intermediate_profiles + 1)
                self.profiles_config.append(self.profiles_config[i].interpolate(self.profiles_config[i + 1], t))
        self.profiles_config.sort(key=lambda x: x.radial_offset, reverse=False)
        

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
        for profile_config in self.profiles_config:
            res = Profile(
                plane = self.__createOffsetPlane(profile_config.radial_offset),
                naca = profile_config.naca,
                c = profile_config.c,
                angle = profile_config.angle,
                radial_offset = profile_config.radial_offset,
                colinear_offset = profile_config.colinear_offset
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
        for i, rail in enumerate(self.rails):
            j = eval(RAIL_NS[i].replace('X', 'profile.n'))
            rail.add(adsk.core.Point3D.create(*naca_points[j], profile.radial_offset))

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
        self.rail_splines = [self.verticalSketch.sketchCurves.sketchFittedSplines.add(rail_pts) for rail_pts in self.rails]

        
    
    def __loftProfiles(self) -> None:
        """Lofts together all profiles i.e. form the solid defined by the profiles"""

        design = self.app.activeProduct
        rootComp = design.rootComponent
        
        # Creating the different objects to call the loft function
        loftFeats = rootComp.features.loftFeatures
        loftInput = loftFeats.createInput(adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    
        # Create rails (guides) in order to avoid creating funny looking shapes when lofting
        loftRails = loftInput.centerLineOrRails
        for rail_spline in self.rail_splines:
            loftRails.addRail(rail_spline)

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
        self.__load_config()
        self.__interpolate_profiles()
        self.__createOffsetPlanesAndGenerateProfilesObject()
        self.__generateProfiles()
        self.__hideConstruction()
        self.__loftProfiles()
        self.__translateSelf()
        self.__rotateSelf()
        
