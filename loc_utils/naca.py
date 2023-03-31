from __future__ import annotations
from typing import Union

class NACA4:
    def __init__(self, NACA_code: Union[str, int]):
        if type(NACA_code) == int:
            NACA_code = str(NACA_code)
        elif type(NACA_code) != str:
            raise TypeError("NACA code must be a string or an integer")
        self.m = int(NACA_code[0])
        self.p = int(NACA_code[1])
        self.t = int(NACA_code[2:])
        self.naca_code = int(NACA_code)

    @classmethod
    def buildFromParameters(cls, m: float, p: float, t: float):
        a = cls('0000')
        a.m = m
        a.p = p
        a.t = t
        return a

    def __repr__(self):
        return f"NACA4 profile : {self.naca_code}"
    
    def interpolate(self, other: NACA4, t):
        return NACA4.buildFromParameters(
            m = int(self.m + t * (other.m - self.m)),
            p = int(self.p + t * (other.p - self.p)),
            t = int(self.t + t * (other.t - self.t))
        )

# class NACA5:
#     def __init__(self, NACA_str: str):
#         self.l = int(NACA_str[0])
#         self.p = int(NACA_str[1])
#         self.q = int(NACA_str[2])
#         self.t = int(NACA_str[3:])