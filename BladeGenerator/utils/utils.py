class NACA4:
    def __init__(self, NACA_str: str):
        self.m = int(NACA_str[0])
        self.p = int(NACA_str[1])
        self.t = int(NACA_str[2:])

# class NACA5:
#     def __init__(self, NACA_str: str):
#         self.l = int(NACA_str[0])
#         self.p = int(NACA_str[1])
#         self.q = int(NACA_str[2])
#         self.t = int(NACA_str[3:])