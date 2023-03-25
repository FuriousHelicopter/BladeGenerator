from .naca import NACA4

class Profile:
    def __init__(self, plane, naca: NACA4, c: float, angle: float):
        self.plane = plane
        self.naca = naca
        self.c = c
        self.angle = angle
        self.sketch = None