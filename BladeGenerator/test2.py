from utils import *

import matplotlib.pyplot as plt

NACA = NACA4("2412")

points = PointGenerator(NACA, 500).getPoints()

plt.plot(points[:, 0], points[:, 1])
plt.axis('equal')
plt.show()
