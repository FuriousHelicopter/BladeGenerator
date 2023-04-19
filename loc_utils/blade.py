import adsk.core, adsk.fusion
from adsk.core import Point3D, Vector3D, Matrix3D, ObjectCollection, ValueInput
import numpy as np

# Local imports
from .naca import NACA4
from .profile import Profile
from .profile_config import ProfileConfig

RAIL_NS = ["0", "X-1"] # where X is half the number of points in the profile
# "int(X//2)", "3*int(X//2)", "int(X//4)", "3*int(X//4)", "5*int(X//4)", "7*int(X//4)"
class Blade():
    def __init__(self, app, blade_config: dict, intermediate_profiles: int, blade_no: int) -> None:
        # Blade configuration
        self.angle: float = blade_config['angle'] / 180 * np.pi
        self.profiles_dict: dict = blade_config['profiles']
        self.radial_blade_offset: float = blade_config['radial_blade_offset']
        self.vertical_blade_offset: float = blade_config.get('vertical_blade_offset', 0)
        self.intermediate_profiles: int = intermediate_profiles
        
        # API objects
        self.app = app
        self.ui = app.userInterface
        self.rails: list[ObjectCollection] = [ObjectCollection.create() for _ in range(len(RAIL_NS))]  # len(RAIL_NS) extrusion rails, collection of Points
        
        self.rail_splines = []
        self.profiles_config: list[ProfileConfig] = []
        self.profiles: list[Profile] = []

        self.min_outer_shaft_radius: float = None

        self.max_y: float = None
        self.min_y: float = None

        self.blade_no: int = blade_no

    def __load_config(self) -> None:
        """Creates profileConfig objects from the self.profiles_dict and create self.profilesConfig list."""
        for profile_config in self.profiles_dict:
            self.profiles_config.append(ProfileConfig(
                radial_offset = profile_config['radial_offset'],
                naca = NACA4(profile_config['naca']),
                c = profile_config['c'],
                angle = profile_config['angle'],
                colinear_offset = profile_config['colinear_offset']
            ))

    def __interpolate_profiles(self) -> None:
        """Interpolates the profiles and complete the self.profilesConfig list."""
        if self.intermediate_profiles == 0:
            return
        for i in range(len(self.profiles_config) - 1):
            for j in range(self.intermediate_profiles):
                j += 1
                t = j / (self.intermediate_profiles + 1)
                self.profiles_config.append(self.profiles_config[i].interpolate(self.profiles_config[i + 1], t))
        self.profiles_config.sort(key=lambda x: x.radial_offset, reverse=False)
        

    def __createOffsetPlane(self, radial_offset: float) -> adsk.fusion.ConstructionPlane:
        """Creates a new offset plane and return it."""
        design = self.app.activeProduct
        rootComp = design.rootComponent
        planes = rootComp.constructionPlanes
        planeInput = planes.createInput()
        planeInput.setByOffset(
            rootComp.xYConstructionPlane, 
            ValueInput.createByReal(radial_offset)
        )
        return planes.add(planeInput)

    def __createOffsetPlanesAndGenerateProfilesObject(self) -> None:
        """Creates all the offset planes from the interpretation of the self.profiles dict."""
        for i, profile_config in enumerate(self.profiles_config):
            profile_plane = self.__createOffsetPlane(profile_config.radial_offset)
            profile_plane.name = f"Plane for profile {i} in blade {self.blade_no}"
            res = Profile(
                plane = profile_plane,
                naca = profile_config.naca,
                c = profile_config.c,
                angle = profile_config.angle,
                radial_offset = profile_config.radial_offset,
                colinear_offset = profile_config.colinear_offset,
                profile_no = i
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
        points = ObjectCollection.create()  # object collection that contains points

        # Define the points the spline with fit through.
        naca_points = profile.getPoints()

        # Generating the rails points to guide the future loft (took the 2 outer points)
        for i, rail in enumerate(self.rails):
            j = eval(RAIL_NS[i].replace('X', 'profile.n'))
            rail.add(Point3D.create(*naca_points[j], profile.radial_offset))

        # Adding the points to the collection (i.e. to the sketch)
        for x, y in naca_points:
            p = Point3D.create(x, y, 0)
            points.add(p)

        # Drawing the spline
        sketch.sketchCurves.sketchFittedSplines.add(points)
        profile.sketch = sketch
        profile.sketch.name = f"Sketch for profile {profile.profile_no} in blade {self.blade_no}"

    def __generateProfiles(self) -> None:
        """Generates all the profiles in the 3D modeling from the self.config dict."""
        for profile in self.profiles:
            self.__generateProfile(profile) 

        # generate rails
        design = self.app.activeProduct
        rootComp = design.rootComponent  # root component (contains sketches, volumnes, etc)
        self.verticalSketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        self.verticalSketch.name = f"Rail sketch for blade {self.blade_no}"
        self.rail_splines = [self.verticalSketch.sketchCurves.sketchFittedSplines.add(rail_pts) for rail_pts in self.rails]

    def __hideConstruction(self) -> None:
        """Hides all the construction planes and sketches."""
        for profile in self.profiles:
            profile.plane.isLightBulbOn = False
            profile.sketch.isLightBulbOn = False
        self.verticalSketch.isLightBulbOn = False        
    
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
        self.entity.name = f"Blade {self.blade_no}"

    def __getInnerProfile(self) -> None:
        """Gets the inner profile of the blade."""
        self.inner_profile: Profile = min(self.profiles, key=lambda profile: profile.radial_offset)


    def __computeMinMaxValuesForMain(self) -> None:
        """Computes the minimum outer shaft radius corresponding to the blade configuration."""
        self.med_x: float = (np.max(self.inner_profile.points[::, 0]) + np.min(self.inner_profile.points[::, 0])) / 2
        self.max_y: float = np.max(self.inner_profile.points[::, 1])
        self.min_y: float = np.min(self.inner_profile.points[::, 1])
        self.min_r: float = self.inner_profile.radial_offset + self.radial_blade_offset
        farest_point = max([(x-self.med_x)**2 + (self.inner_profile.radial_offset + self.radial_blade_offset)**2 for (x, _) in self.inner_profile.points])
        self.min_outer_shaft_radius = np.sqrt(farest_point)
        

    def __translateSelf(self) -> None:
        """
        Translates the blade so that: 
        - the middle of the closest profile is at the origin 
        - offsets it by the specified blade radial offset
        - offsets it by the specified blade vertical offset
        """

        # Create the transform object.
        transform = Matrix3D.create()
        transform.translation = Vector3D.create(-self.med_x, self.vertical_blade_offset, self.radial_blade_offset)

        # Create a move feature
        moveFeats = self.app.activeProduct.rootComponent.features.moveFeatures
        toMove = ObjectCollection.create()
        toMove.add(self.entity)

        # Apply the transform
        moveInput = moveFeats.createInput(toMove, transform)
        moveFeats.add(moveInput)

    def __rotateSelf(self) -> None:
        """Rotates the blade around the X axis by self.angle degrees."""
        
        if self.angle == 0:
            # No need to rotate
            return

        # Create transform object
        transform = Matrix3D.create()
        transform.setToRotation(
            angle = self.angle,
            axis = Vector3D.create(0, 1, 0),
            origin = Point3D.create(0, 0, 0)
        )

        # Create a move feature
        moveFeats = self.app.activeProduct.rootComponent.features.moveFeatures
        toMove = ObjectCollection.create()
        toMove.add(self.entity)
        moveInput = moveFeats.createInput(toMove, transform)
        moveFeats.add(moveInput)

    


    def build(self) -> None:
        """Builds the blade from the config dict."""
        self.__load_config()
        self.__interpolate_profiles()
        self.__createOffsetPlanesAndGenerateProfilesObject()
        self.__generateProfiles()
        self.__hideConstruction()
        self.__loftProfiles()
        self.__getInnerProfile()
        self.__computeMinMaxValuesForMain()
        self.__translateSelf()
        self.__rotateSelf()
        
        
