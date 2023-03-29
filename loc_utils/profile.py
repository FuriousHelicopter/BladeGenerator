import numpy as np
from .naca import NACA4
from .point_generator import PointGenerator

class Profile:
    def __init__(self, plane, naca: NACA4, c: float, angle: float, offset: float, n: int=100):
        self.plane = plane
        self.naca = naca
        self.c = c
        self.angle = angle
        self.sketch = None
        self.offset = offset
        self.n = n

    def __repr__(self):
        return f"Profile: offset={self.offset}, c={self.c}, angle={self.angle} \n from {self.naca.__repr__()}"
    
    def generatePoints(self):
        return PointGenerator(self.naca, num_points=self.n).getPoints()
    