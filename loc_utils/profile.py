import numpy as np
from .naca import NACA4
from .point_generator import PointGenerator

class Profile:
    def __init__(self, plane, naca: NACA4, c: float, angle: float, radial_offset: float, colinear_offset: float, profile_no: int, n: int=100):
        self.plane = plane
        self.naca = naca
        self.c = c
        self.angle = angle
        self.sketch = None
        self.radial_offset = radial_offset
        self.n = n
        self.points = None
        self.colinear_offset = colinear_offset
        self.profile_no = profile_no

    def __repr__(self):
        return f"Profile: offset={self.radial_offset}, c={self.c}, angle={self.angle}, colinear_offset={self.colinear_offset} \n from {self.naca.__repr__()}"
    
    def __generatePoints(self):
        self.points = PointGenerator(self.naca, num_points=self.n).getPoints()

    def __rotate(self):
        angle_rad = self.angle / 180 * np.pi
        derivative = np.tan(angle_rad)
        self.points = np.array([self.points[:, 0], self.points[:, 1] + derivative*self.points[:, 0]]).T # Works because leading edge is at (0, 0) 
    
    def __scale(self):
        self.points = self.points * self.c

    def __colinearOffset(self):
        self.points[:, 0] += self.colinear_offset

    def getPoints(self):
        self.__generatePoints()
        self.__rotate()
        self.__scale()
        self.__colinearOffset()
        return self.points

    
    