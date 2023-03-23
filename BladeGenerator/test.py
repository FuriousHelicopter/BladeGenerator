def show(lines):
    for line in lines:
        print(line)

lines = []

with open('airfoil.dat', 'r') as f:
    lines = f.readlines()

res = []


show(res)