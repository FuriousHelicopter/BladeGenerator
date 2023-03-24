import numpy as np
from .NACA import NACA4

# CONSTANTS

defaultAirfoilHalfCosine = True
defaultAirfoilFT = False

# END CONSTANTS



class PointGenerator:
    def __init__(self, NACA: NACA4, num_points: int = 100, finite_TE : bool = defaultAirfoilFT, half_cosine_spacing : bool = defaultAirfoilHalfCosine):        
        self.NACA: NACA4 = NACA
        self.num_points: int = num_points
        self.finite_TE = finite_TE
        self.half_cosine_spacing = half_cosine_spacing

    def __getPointsNACA4(self, NACA: NACA4, num_points: int):
        A0 = 0.2969
        A1 = -0.1260
        A2 = -0.3516
        A3 = 0.2843

        m = float(NACA.m) / 100.0
        p = float(NACA.p) / 10.0
        t = float(NACA.t) / 100.0

        A4 = -0.1036 # For zero thick TE
        if self.finite_TE:
            A4 = -0.1015 # For finite thick TE

        x = np.linspace(0.0, 1.0, num_points+1)
        if self.half_cosine_spacing:
            beta = np.linspace(0.0, np.pi, num_points+1)
            x: np.ndarray = 0.5*(1.0 - np.cos(beta)) # Half cosine based spacing

        yt: np.ndarray = 5 * t * (A0 * np.sqrt(x) + A1 * x + A2 * x**2 + A3 * x**3 + A4 * x**4)

        xc1: np.ndarray = x[x <= p]
        xc2: np.ndarray = x[x > p]

        if p == 0:
            xu = x
            yu = yt
            xl = x
            yl = -yt
            zc = np.zeros(len(x))

        else:
            yc1 = m / p**2 * xc1 * (2*p - xc1)
            yc2 = m / (1-p)**2 * (1-2*p + xc2) * (1-xc2)
            zc = np.concatenate((yc1, yc2))

            dyc1_dc = 2*m / p**2 * (p - xc1)
            dyc2_dc = 2*m / (1-p)**2 * (p - xc2)
            dyc_dc = np.concatenate((dyc1_dc, dyc2_dc))

            theta = np.arctan(dyc_dc)

            xu = x - yt * np.sin(theta)
            yu = zc + yt * np.cos(theta)

            xl = x + yt * np.sin(theta)
            yl = zc - yt * np.cos(theta)

        X = np.concatenate((xu[::-1], xl[1:]))
        Y = np.concatenate((yu[::-1], yl[1:]))

        ret = np.empty((len(X), 2))
        ret[:, 0] = X
        ret[:, 1] = Y
        return ret
            


    
    def getPoints(self) -> np.ndarray:
        return self.__getPointsNACA4(self.NACA, self.num_points)

        # string_list = self.dat[1:]
        # res = []
        # for i in range(len(string_list)):
        #     string_list[i] = string_list[i].strip().replace('  ', ' ')
        #     a = string_list[i].split(' ')
        #     res.append([float(a[0]), float(a[1])])
        # return np.array(res)
    
