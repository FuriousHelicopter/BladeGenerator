from .naca import NACA4

class Profile:
    def __init__(self, plane, naca: NACA4, c: float, angle: float, offset: float):
        self.plane = plane
        self.naca = naca
        self.c = c
        self.angle = angle
        self.sketch = None
        self.offset = offset

    def __repr__(self):
        return f"Profile: offset={self.offset}, c={self.c}, angle={self.angle} \n from {self.naca.__repr__()}"