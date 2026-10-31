"""Матриці перетворень 3x3 для двовимірної графіки.

Точка записується в однорідних координатах вектором-рядком P = [x, y, 1],
а будь-яке перетворення зводиться до множення P' = P · T (формула 6).
Усі матриці побудовані власноруч, без використання QTransform.
"""
import math

EPS = 1e-9


class Matrix3:
    def __init__(self, rows=None):
        # За замовчуванням - одинична матриця (формула 4)
        if rows is None:
            rows = [[1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0]]
        self.m = [[float(v) for v in row] for row in rows]

    def __matmul__(self, other):
        """Добуток матриць self · other (спочатку self, потім other)."""
        a, b = self.m, other.m
        return Matrix3([[sum(a[i][k] * b[k][j] for k in range(3))
                         for j in range(3)]
                        for i in range(3)])

    def apply(self, x, y):
        """Перетворення точки за формулами (8)-(9).

        Повертає None, якщо вага w <= 0 - точка опинилась "за горизонтом"
        проективного перетворення і не може бути відображена.
        """
        m = self.m
        xw = x * m[0][0] + y * m[1][0] + m[2][0]
        yw = x * m[0][1] + y * m[1][1] + m[2][1]
        w = x * m[0][2] + y * m[1][2] + m[2][2]
        if w <= EPS:
            return None
        return xw / w, yw / w

    def inverse(self):
        """Обернена матриця через алгебраїчні доповнення: T⁻¹ = adj(T) / det(T)."""
        m = self.m

        def minor(i, j):
            r = [k for k in range(3) if k != i]
            c = [k for k in range(3) if k != j]
            return m[r[0]][c[0]] * m[r[1]][c[1]] - m[r[0]][c[1]] * m[r[1]][c[0]]

        det = sum((-1) ** j * m[0][j] * minor(0, j) for j in range(3))
        return Matrix3([[(-1) ** (i + j) * minor(j, i) / det for j in range(3)]
                        for i in range(3)])

    def __repr__(self):
        return "\n".join(" ".join(f"{v:9.3f}" for v in row) for row in self.m)


def translation(dx, dy):
    """Матриця зсуву (формула 11)."""
    return Matrix3([[1, 0, 0],
                    [0, 1, 0],
                    [dx, dy, 1]])


def rotation(px, py, angle_deg):
    """Матриця обертання на кут angle навколо довільної точки P (формула 12).

    Користувач задає кут у градусах, а в обчисленнях використовуються радіани.
    """
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return Matrix3([[c, s, 0],
                    [-s, c, 0],
                    [-px * (c - 1) + py * s, -px * s - py * (c - 1), 1]])


def scaling(sx, sy, px=0.0, py=0.0):
    """Матриця масштабування (формула 13) відносно точки P.

    При P = (0, 0) збігається з формулою (13), інакше - це
    зсув у початок координат, масштабування і зсув назад.
    """
    return Matrix3([[sx, 0, 0],
                    [0, sy, 0],
                    [px * (1 - sx), py * (1 - sy), 1]])


def point_symmetry(px, py):
    """Матриця симетрії відносно точки P (формула 14)."""
    return Matrix3([[-1, 0, 0],
                    [0, -1, 0],
                    [2 * px, 2 * py, 1]])


def affine(xx, xy, yx, yy, ox, oy):
    """Матриця афінного перетворення (формула 16).

    X(xx, xy), Y(yx, yy) - нові одиничні вектори осей, O(ox, oy) - новий початок.
    """
    return Matrix3([[xx, xy, 0],
                    [yx, yy, 0],
                    [ox, oy, 1]])


def projective(xx, xy, wx, yx, yy, wy, ox, oy, w0):
    """Матриця проективного перетворення (формула 17).

    Xend, Yend - кінці осей, O - початок координат, wx, wy, w0 - їх ваги.
    """
    return Matrix3([[xx * wx, xy * wx, wx],
                    [yx * wy, yy * wy, wy],
                    [ox * w0, oy * w0, w0]])
