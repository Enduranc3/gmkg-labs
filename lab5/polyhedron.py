"""Грановане тіло - ракета: шестигранний корпус, носова піраміда і три стабілізатори.

Тіло задається вершинами та гранями, ребра виводяться з граней. Вершини кожної
грані записані проти годинникової стрілки, якщо дивитись на неї ззовні.
"""
import math

from core.matrix import Matrix4, rotation_x, rotation_y, rotation_z, scaling, translation

SIDES = 6                  # кількість граней корпусу
FIN_FACES = (0, 2, 4)      # грані корпусу, на яких стоять стабілізатори

# Частки висоти тіла
HULL_BOTTOM = 0.08         # низ корпусу (кінці стабілізаторів стоять на площині y = 0)
FIN_ROOT = 0.22            # верх кореня стабілізатора
HULL_TOP = 0.80            # верх корпусу, вище - носова піраміда
FIN_REACH = 2.4            # виліт стабілізатора відносно радіуса корпусу

DEFAULTS = {"scale": 1.0, "height": 360.0, "width": 70.0, "depth": 70.0}


def rocket_vertices(width, height, depth):
    """Вершини тіла: 6 низу корпусу, 6 верху, вершина носа, 6 на рівні кореня
    стабілізаторів, 3 кінці стабілізаторів. Основа тіла стоїть на площині y = 0."""
    rx, rz = width / 2, depth / 2

    def around(angle, y, reach=1.0):
        a = math.radians(angle)
        return reach * rx * math.cos(a), y, reach * rz * math.sin(a)

    def ring(y):
        return [around(60 * k, y) for k in range(SIDES)]

    tips = [around(60 * k + 30, 0.0, FIN_REACH) for k in FIN_FACES]
    return (ring(HULL_BOTTOM * height) + ring(HULL_TOP * height) + [(0.0, height, 0.0)]
            + ring(FIN_ROOT * height) + tips)


def rocket_faces():
    """Грані тіла як списки номерів вершин."""
    bottom = list(range(SIDES))
    top = [SIDES + k for k in range(SIDES)]
    apex = 2 * SIDES
    root = [apex + 1 + k for k in range(SIDES)]
    tips = {k: root[0] + SIDES + i for i, k in enumerate(FIN_FACES)}

    faces = [bottom]
    for k in range(SIDES):
        n = (k + 1) % SIDES
        faces.append([top[k], apex, top[n]])
        if k in FIN_FACES:
            # грань корпусу над стабілізатором і чотири грані самого стабілізатора
            faces.append([root[k], top[k], top[n], root[n]])
            o = tips[k]
            faces += [[bottom[k], root[k], o], [root[k], root[n], o],
                      [root[n], bottom[n], o], [bottom[n], bottom[k], o]]
        else:
            faces.append([bottom[k], root[k], top[k], top[n], root[n], bottom[n]])
    return faces


def faces_to_edges(faces):
    """Ребра тіла: кожна пара сусідніх вершин грані, без повторів."""
    edges = set()
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1]):
            edges.add((min(a, b), max(a, b)))
    return sorted(edges)


class FacetedBody:
    """Параметри тіла, його положення у просторі та власний центр обертання."""

    def __init__(self):
        self.faces = rocket_faces()
        self.edges = faces_to_edges(self.faces)
        self.reset()

    def reset(self):
        self.scale = DEFAULTS["scale"]
        self.height = DEFAULTS["height"]
        self.width = DEFAULTS["width"]
        self.depth = DEFAULTS["depth"]
        self.offset = [0.0, 0.0, 0.0]
        self.rotation = Matrix4()      # накопичене обертання навколо власних осей

    def shift(self, dx, dy, dz):
        self.offset = [self.offset[0] + dx, self.offset[1] + dy, self.offset[2] + dz]

    def rotate(self, ax, ay, az):
        """Обертання навколо власних осей: нова матриця стоїть перед накопиченою,
        тому осі X, Y, Z рухаються разом із тілом."""
        self.rotation = rotation_x(ax) @ rotation_y(ay) @ rotation_z(az) @ self.rotation

    def pivot(self):
        """Точка всередині тіла, навколо якої воно обертається (до перетворень)."""
        return 0.0, self.height / 2, 0.0

    def model_matrix(self):
        """M = S(s) · T(−C) · R · T(C) · T(offset), де C - центр після масштабування:
        масштаб, зсув центру в початок координат, обертання, зсув назад, зсув тіла."""
        cx, cy, cz = (v * self.scale for v in self.pivot())
        return (scaling(self.scale) @ translation(-cx, -cy, -cz) @ self.rotation
                @ translation(cx, cy, cz) @ translation(*self.offset))

    def world_vertices(self):
        """Вершини тіла у просторі: кожна множиться на матрицю перетворень."""
        m = self.model_matrix()
        return [m.apply(*v) for v in rocket_vertices(self.width, self.height, self.depth)]

    def world_pivot(self):
        return self.model_matrix().apply(*self.pivot())

    def own_axes(self, length):
        """Кінці власних осей X, Y, Z, проведених із центру обертання."""
        cx, cy, cz = self.world_pivot()
        ends = []
        for axis in ((length, 0, 0), (0, length, 0), (0, 0, length)):
            x, y, z = self.rotation.apply(*axis)
            ends.append((cx + x, cy + y, cz + z))
        return ends
