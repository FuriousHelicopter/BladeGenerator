from __future__ import annotations
from .naca import NACA4

class ProfileConfig:
    def __init__(self, radial_offset: float, naca: NACA4, c: float, angle: float, colinear_offset: float):
        self.radial_offset = radial_offset
        self.naca = naca
        self.c = c
        self.angle = angle
        self.colinear_offset = colinear_offset

    def interpolate(self, other: ProfileConfig, t):
        return ProfileConfig(
            radial_offset = self.radial_offset + t * (other.radial_offset - self.radial_offset),
            naca = self.naca.interpolate(other.naca, t),
            c = self.c + t * (other.c - self.c),
            angle = self.angle + t * (other.angle - self.angle),
            colinear_offset = self.colinear_offset + t * (other.colinear_offset - self.colinear_offset)
        )
    
