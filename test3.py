import matplotlib.pyplot as plt
from BladeGenerator.point_generator import PointGenerator

def show(lines):
    for line in lines:
        print(line)

lines = []

with open('airfoil.dat', 'r') as f:
    lines = f.readlines()

points = PointGenerator(lines).getPoints()
plt.plot([i[0] for i in points], [i[1] for i in points])

