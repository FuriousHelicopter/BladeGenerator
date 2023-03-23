import numpy as np
from . import *

# CONSTANTS

defaultAirfoilHalfCosine = False
defaultAirfoilFT = False

# END CONSTANTS



class PointGenerator:
    def __init__(self, NACA: NACA4, num_points: int):
        self.NACA: NACA4 = NACA
        self.num_points: int = num_points

    @staticmethod
    def __getPointsNACA4(NACA: NACA4, num_points: int, finite_TE = defaultAirfoilFT, half_cosine_spacing = defaultAirfoilHalfCosine):
        A0 = 0.2969
        A1 = -0.1260
        A2 = -0.3516
        A3 = 0.2843

        m = float(NACA.m) / 100.0
        p = float(NACA.p) / 10.0
        t = float(NACA.t) / 100.0

        A4 = -0.1036 # For zero thick TE
        if finite_TE:
            A4 = -0.1015 # For finite thick TE

        x = np.linspace(0.0, 1.0, num_points+1)
        if half_cosine_spacing:
            beta = np.linspace(0.0, np.pi, num_points+1)
            x = [(0.5*(1.0-np.cos(xx))) for xx in beta]  # Half cosine based spacing

        yt = 5 * t * (A0 * np.sqrt(x) + A1 * x + A2 * np.power(x, 2) + A3 * np.power(x, 3) + A4 * np.power(x, 4))

        xc1 = x[x <= p]
        xc2 = x[x > p]

        if p == 0:
            xu = x
            yu = yt
            xl = x
            yl = -yt
            zc = np.zeros(len(x))

        else:
            yc1 = m / p**2 * x * (2*p - x)
            yc2 = m / (1-p)**2 * (1-2*p + x) * (1-x)
            zc = np.concatenate((yc1, yc2))

            dyc1_dc = 2*m / p**2 * (p - x)
            dyc2_dc = 2*m / (1-p)**2 * (p - x)
            dyc_dc = np.concatenate((dyc1_dc, dyc2_dc))

            theta = np.arctan(dyc_dc)

            xu = x - yt * np.sin(theta)
            yu = zc + yt * np.cos(theta)

            xl = x + yt * np.sin(theta)
            yl = zc - yt * np.cos(theta)

        X = xu[::-1] + xl[1:]
        Y = yu[::-1] + yl[1:]

        return np.concatenate((X, Y), axis=1).T
            


    
    def getPoints(self) -> np.ndarray:
        return PointGenerator.__getPointsNACA4(self.NACA, self.num_points)

        # string_list = self.dat[1:]
        # res = []
        # for i in range(len(string_list)):
        #     string_list[i] = string_list[i].strip().replace('  ', ' ')
        #     a = string_list[i].split(' ')
        #     res.append([float(a[0]), float(a[1])])
        # return np.array(res)
    
