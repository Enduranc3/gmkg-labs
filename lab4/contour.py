"""Гладкий криволінійний контур з дуг кубічних парабол (ЛР4, на основі ЛР3).

Кубічна парабола - це крива Безьє третього порядку. Кожна дуга задається
чотирма реперними точками A, B, C, D характеристичної ламаної:

    r(u) = (1-u)³·A + 3u(1-u)²·B + 3u²(1-u)·C + u³·D,   0 ≤ u ≤ 1.

Дуга виходить з точки A по дотичній AB і приходить у точку D по дотичній CD:
r'(0) = 3(B - A), r'(1) = 3(D - C). Параметр дуги - коефіцієнт довжини
дотичних k: B' = A + k·(B - A), C' = D + k·(C - D).

Гладкість 1-го порядку у точці з'єднання дуг r⁽¹⁾ і r⁽²⁾ (формули 4.4, 4.8):

    r₃⁽¹⁾ = r₀⁽²⁾,     T = 3(r₃⁽¹⁾ - r₂⁽¹⁾) / α₁ = 3(r₁⁽²⁾ - r₀⁽²⁾) / α₂,

тобто точки r₂⁽¹⁾, r₃⁽¹⁾ = r₀⁽²⁾ і r₁⁽²⁾ лежать на одній прямій, а α₁, α₂ -
довжини дотичних. Точки з'єднання бувають двох типів:
    вузлова точка - умова гладкості виконується: при зсуві крайньої реперної
        точки однієї дуги протилежна реперна точка сусідньої дуги
        повертається на продовження дотичної;
    точка зламу - умова гладкості не забезпечується, реперні точки
        рухаються незалежно.
"""
import math

from contour_data import CONTOURS
from figures import sun_figure

DEFAULT_K = 1.0            # коефіцієнт довжини дотичних за замовчуванням
DEFAULT_STEPS = 24         # кількість кроків параметра u на одній дузі
DEFAULT_U = 0.1            # параметр u точки r(u), яка показується на вибраній дузі
SMOOTH_ANGLE = 15.0        # з якого кута між дотичними (°) точка вважається точкою зламу
EPS = 1e-12


def cubic_point(a, b, c, d, u):
    """Точка кубічної параболи (кривої Безьє третього порядку) при параметрі u."""
    ja = (1 - u) ** 3
    jb = 3 * u * (1 - u) ** 2
    jc = 3 * u ** 2 * (1 - u)
    jd = u ** 3
    return (a[0] * ja + b[0] * jb + c[0] * jc + d[0] * jd,
            a[1] * ja + b[1] * jb + c[1] * jc + d[1] * jd)


def lerp(p, q, t):
    """Точка на відрізку PQ: P + (Q - P)·t."""
    return p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t


def unit(p, q):
    """Одиничний вектор напрямку PQ і довжина |PQ| (None, якщо точки збігаються)."""
    length = math.dist(p, q)
    if length < EPS:
        return None, 0.0
    return ((q[0] - p[0]) / length, (q[1] - p[1]) / length), length


def tangent_angle(c, a, b):
    """Кут (°) між дотичною C→A, з якою дуга приходить у точку A, і дотичною A→B,
    з якою виходить наступна дуга. 0° - гладке з'єднання."""
    t1, _ = unit(c, a)
    t2, _ = unit(a, b)
    if t1 is None or t2 is None:
        return 0.0
    cross = t1[0] * t2[1] - t1[1] * t2[0]
    dot = t1[0] * t2[0] + t1[1] * t2[1]
    return abs(math.degrees(math.atan2(cross, dot)))


class CurvilinearContour:
    """Набір замкнених контурів. Точки контуру k: A0, B0, C0, A1, B1, C1, ...

    Дуга i контуру k - це точки 3i, 3i+1, 3i+2 і 3i+3 (остання береться
    за модулем, тому контур замкнений). Точка з'єднання дуг i-1 та i - це A_i
    (номер 3i), її сусідні реперні точки - C_(i-1) (3i-1) та B_i (3i+1).
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.base = [list(c) for c in CONTOURS]       # початковий контур (хмара)
        self.target = sun_figure(self.base)            # кінцева фігура анімації (сонце)
        self.k = [[DEFAULT_K] * (len(c) // 3) for c in self.base]
        self.t = 0.0                                   # кадр анімації: 0 - хмара, 1 - сонце
        self.steps = DEFAULT_STEPS
        self.u = DEFAULT_U
        self.detect_smooth()

    # ---------- структура ----------

    def arc_count(self):
        return sum(len(c) // 3 for c in self.base)

    def point_count(self):
        return sum(len(c) for c in self.base)

    def smooth_count(self):
        return sum(sum(row) for row in self.smooth)

    @staticmethod
    def arc(points, i):
        """Реперні точки A, B, C, D дуги i."""
        n = len(points)
        return points[3 * i], points[3 * i + 1], points[3 * i + 2], points[(3 * i + 3) % n]

    def node_of(self, k, j):
        """Точка з'єднання, до якої прилягає точка j контуру k: для A - вона сама,
        для B_i - початок дуги A_i, для C_i - кінець дуги A_(i+1)."""
        n = len(self.base[k])
        return (j, j - 1, (j + 1) % n)[j % 3]

    def opposite(self, k, j):
        """Протилежна крайня реперна точка сусідньої дуги відносно точки з'єднання:
        для B_i (3i+1) - C_(i-1) (3i-1), для C_i (3i+2) - B_(i+1) (3i+4)."""
        n = len(self.base[k])
        return (j - 2) % n if j % 3 == 1 else (j + 2) % n

    def is_smooth(self, k, j):
        """Чи є точка з'єднання j (кратна 3) вузловою, тобто гладкою."""
        return self.smooth[k][j // 3]

    # ---------- гладкість 1-го порядку ----------

    def detect_smooth(self):
        """Тип точок з'єднання вихідного контуру: якщо дотичні з обох боків
        розходяться менше ніж на SMOOTH_ANGLE - вузлова точка (і вона
        вирівнюється точно), інакше - точка зламу (вістря крапель, блискавки)."""
        self.smooth = []
        for points in self.base:
            n = len(points)
            self.smooth.append([tangent_angle(points[j - 1], points[j], points[(j + 1) % n])
                                < SMOOTH_ANGLE for j in range(0, n, 3)])
        for k, row in enumerate(self.smooth):
            for i, smooth in enumerate(row):
                if smooth:
                    for figure in (self.base, self.target):
                        self.align_node(figure[k], 3 * i)

    @staticmethod
    def align_node(points, j):
        """Робить з'єднання в точці A = points[j] гладким: обидві сусідні реперні
        точки C і B ставляться на спільну дотичну T, довжини |AC| = α₁/3 та
        |AB| = α₂/3 зберігаються. T - бісектриса напрямків C→A і A→B:
        T = (T₁ + T₂) / |T₁ + T₂|."""
        n = len(points)
        a, c, b = points[j], points[j - 1], points[(j + 1) % n]
        t1, len1 = unit(c, a)
        t2, len2 = unit(a, b)
        if t1 is None or t2 is None:
            return
        tx, ty = t1[0] + t2[0], t1[1] + t2[1]
        norm = math.hypot(tx, ty)
        if norm < 1e-6:                      # дотичні протилежні - повертаємо на 90°
            tx, ty, norm = -t2[1], t2[0], 1.0
        tx, ty = tx / norm, ty / norm
        points[j - 1] = (a[0] - tx * len1, a[1] - ty * len1)
        points[(j + 1) % n] = (a[0] + tx * len2, a[1] + ty * len2)

    @staticmethod
    def follow(points, j, o, a):
        """Умова гладкості (4.8) при зсуві реперної точки j: протилежна точка o
        ставиться на продовження дотичної за точку з'єднання a, на тій самій
        відстані від неї:  P_o = A - |A - P_o| · (P_j - A) / |P_j - A|."""
        t, _ = unit(points[a], points[j])
        if t is None:
            return
        length = math.dist(points[a], points[o])
        ax, ay = points[a]
        points[o] = (ax - t[0] * length, ay - t[1] * length)

    def set_smooth(self, k, j, smooth):
        """Перемикає тип точки з'єднання j. Ставши вузловою, точка одразу
        вирівнюється, щоб умова гладкості виконувалась."""
        self.smooth[k][j // 3] = smooth
        if smooth:
            for figure in (self.base, self.target):
                self.align_node(figure[k], j)

    def set_all_smooth(self, smooth):
        for k, row in enumerate(self.smooth):
            for i in range(len(row)):
                self.set_smooth(k, 3 * i, smooth)

    def control_points(self):
        """Поточні реперні точки: кожна рухається по своєму відрізку base -> target,
        потім точки B і C кожної дуги зсуваються вздовж дотичних на коефіцієнт k.

        На проміжних кадрах анімації інтерпольовані дотичні з двох боків вузла
        вже не обов'язково на одній прямій, тому вузлові точки вирівнюються ще
        раз - гладкість забезпечується на кожному кадрі."""
        result = []
        for cb, ct, ks, smooth in zip(self.base, self.target, self.k, self.smooth):
            points = [lerp(p, q, self.t) for p, q in zip(cb, ct)]
            n = len(points)
            for i, k in enumerate(ks):
                a, d = points[3 * i], points[(3 * i + 3) % n]
                points[3 * i + 1] = lerp(a, points[3 * i + 1], k)
                points[3 * i + 2] = lerp(d, points[3 * i + 2], k)
            if 0 < self.t < 1:
                for i, s in enumerate(smooth):
                    if s:
                        self.align_node(points, 3 * i)
            result.append(points)
        return result

    # ---------- побудова ----------

    def arc_polyline(self, a, b, c, d):
        """Цикл побудови дуги: u змінюється від 0 до 1 з кроком 1 / steps."""
        return [cubic_point(a, b, c, d, i / self.steps) for i in range(self.steps + 1)]

    # ---------- редагування ----------

    def move_point(self, k, j, dx, dy):
        """Зсув реперної точки j контуру k на (dx, dy).

        Точка з'єднання A тягне за собою сусідні точки C попередньої та B
        наступної дуги, тому дотичні в ній зберігаються. Крайня реперна точка
        B або C показується зсунутою вздовж дотичної в k разів, тому її зсув
        ділиться на k - точка йде точно за курсором. Якщо її точка з'єднання
        вузлова, протилежна реперна точка сусідньої дуги повертається слідом
        (функція 1 завдання); у точці зламу вона лишається на місці (функція 2).
        На проміжних кадрах анімації зсуваються і початкова, і кінцева фігура.
        """
        n = len(self.base[k])
        if j % 3:
            scale = self.k[k][j // 3]
            moved = [(j, dx / scale, dy / scale)]
        else:
            moved = [(i, dx, dy) for i in (j, (j - 1) % n, (j + 1) % n)]
        figures = [self.base] if self.t == 0 else [self.base, self.target]
        for figure in figures:
            for i, mx, my in moved:
                x, y = figure[k][i]
                figure[k][i] = (x + mx, y + my)
            if j % 3:
                node = self.node_of(k, j)
                if self.is_smooth(k, node):
                    self.follow(figure[k], j, self.opposite(k, j), node)
