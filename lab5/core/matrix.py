"""Матриці перетворень 4x4 для тривимірної графіки.

Точка записується в однорідних координатах вектором-рядком P = [x, y, z, 1],
а будь-яке перетворення зводиться до множення P' = P · M (формула 5.4).
Усі матриці побудовані власноруч, без використання QMatrix4x4.
"""
import math


class Matrix4:
    def __init__(self, rows=None):
        # За замовчуванням - одинична матриця
        if rows is None:
            rows = [[1.0, 0.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0]]
        self.m = [[float(v) for v in row] for row in rows]

    def __matmul__(self, other):
        """Добуток матриць self · other (спочатку self, потім other)."""
        a, b = self.m, other.m
        return Matrix4([[sum(a[i][k] * b[k][j] for k in range(4))
                         for j in range(4)]
                        for i in range(4)])

    def apply(self, x, y, z):
        """Перетворення точки: [x' y' z' w] = [x y z 1] · M, результат ділиться на w."""
        m = self.m
        xw = x * m[0][0] + y * m[1][0] + z * m[2][0] + m[3][0]
        yw = x * m[0][1] + y * m[1][1] + z * m[2][1] + m[3][1]
        zw = x * m[0][2] + y * m[1][2] + z * m[2][2] + m[3][2]
        w = x * m[0][3] + y * m[1][3] + z * m[2][3] + m[3][3]
        return xw / w, yw / w, zw / w

    def __repr__(self):
        return "\n".join(" ".join(f"{v:9.3f}" for v in row) for row in self.m)


def translation(dx, dy, dz):
    """Матриця зсуву."""
    return Matrix4([[1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [dx, dy, dz, 1]])


def scaling(s):
    """Матриця рівномірного масштабування відносно початку координат."""
    return Matrix4([[s, 0, 0, 0],
                    [0, s, 0, 0],
                    [0, 0, s, 0],
                    [0, 0, 0, 1]])


def rotation_x(angle_deg):
    """Матриця обертання навколо осі X (вигляд як у формулі триметрії методички)."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return Matrix4([[1, 0, 0, 0],
                    [0, c, s, 0],
                    [0, -s, c, 0],
                    [0, 0, 0, 1]])


def rotation_y(angle_deg):
    """Матриця обертання навколо осі Y (вигляд як у формулі триметрії методички)."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return Matrix4([[c, 0, -s, 0],
                    [0, 1, 0, 0],
                    [s, 0, c, 0],
                    [0, 0, 0, 1]])


def rotation_z(angle_deg):
    """Матриця обертання навколо осі Z."""
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return Matrix4([[c, s, 0, 0],
                    [-s, c, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])


def ortho_y0():
    """Матриця ортографічної проекції на площину y = 0 (формула 5.6)."""
    return Matrix4([[1, 0, 0, 0],
                    [0, 0, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])


def dimetric_beta(alpha_deg):
    """Кут β (°) за кутом α з умови диметрії: sin²β = sin²α / (1 − sin²α) (формула 5.11).

    Рівняння дає два значення β = ±arcsin|tg α|, тут повертається додатне.
    Розв'язок існує лише при |α| < 45°, інакше |tg α| > 1.
    """
    s2 = math.sin(math.radians(alpha_deg)) ** 2
    return math.degrees(math.asin(math.sqrt(s2 / (1 - s2))))


def dimetry_y0(alpha_deg, beta_deg):
    """Матриця диметричної проекції на площину y = 0: M = Rx(β) · Rz(α) · M_орт(y = 0).

    У кінцевому вигляді:
        |  cos α          0   0       0 |
        | −cos β·sin α    0   sin β   0 |
        |  sin β·sin α    0   cos β   0 |
        |  0              0   0       1 |
    """
    return rotation_x(beta_deg) @ rotation_z(alpha_deg) @ ortho_y0()
