class PointGenerator:
    def __init__(self, dat):
        self.dat = dat

    def getPoints(self) -> list[list[float]]:
        string_list = self.dat[1:]
        res = []
        for i in range(len(string_list)):
            string_list[i] = string_list[i].strip().replace('  ', ' ')
            a = string_list[i].split(' ')
            res.append([float(a[0]), float(a[1])])
        return res