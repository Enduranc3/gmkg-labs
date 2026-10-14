"""Криволінійний контур з дуг кубічних парабол (варіант 1: метод 10, контур 30).

Кубічна парабола - це крива Безьє третього порядку. Кожна дуга задається
чотирма реперними точками A, B, C, D характеристичної ламаної:

    r(u) = (1-u)³·A + 3u(1-u)²·B + 3u²(1-u)·C + u³·D,   0 ≤ u ≤ 1.

Дуга виходить з точки A по дотичній AB і приходить у точку D по дотичній CD:
r'(0) = 3(B - A), r'(1) = 3(D - C). Параметр дуги - коефіцієнт довжини
дотичних k: точки B і C зсуваються вздовж ланок AB і CD,

    B' = A + k·(B - A),   C' = D + k·(C - D),

напрямки дотичних (і гладкість контуру у вузлах) при цьому не змінюються.
При k < 1 дуга притискається до хорди AD, при k > 1 - вигинається сильніше.
"""
from contour_data import CONTOURS
from figures import sun_figure

DEFAULT_K = 1.0            # коефіцієнт довжини дотичних за замовчуванням
DEFAULT_STEPS = 24         # кількість кроків параметра u на одній дузі
DEFAULT_U = 0.1            # параметр u точки r(u), яка показується на вибраній дузі


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


class CurvilinearContour:
    """Набір замкнених контурів. Точки контуру k: A0, B0, C0, A1, B1, C1, ...

    Дуга i контуру k - це точки 3i, 3i+1, 3i+2 і 3i+3 (остання береться
    за модулем, тому контур замкнений).
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

    # ---------- структура ----------

    def arc_count(self):
        return sum(len(c) // 3 for c in self.base)

    def point_count(self):
        return sum(len(c) for c in self.base)

    @staticmethod
    def arc(points, i):
        """Реперні точки A, B, C, D дуги i."""
        n = len(points)
        return points[3 * i], points[3 * i + 1], points[3 * i + 2], points[(3 * i + 3) % n]

    def control_points(self):
        """Поточні реперні точки: кожна рухається по своєму відрізку base -> target,
        потім точки B і C кожної дуги зсуваються вздовж дотичних на коефіцієнт k."""
        result = []
        for cb, ct, ks in zip(self.base, self.target, self.k):
            points = [lerp(p, q, self.t) for p, q in zip(cb, ct)]
            n = len(points)
            for i, k in enumerate(ks):
                a, d = points[3 * i], points[(3 * i + 3) % n]
                points[3 * i + 1] = lerp(a, points[3 * i + 1], k)
                points[3 * i + 2] = lerp(d, points[3 * i + 2], k)
            result.append(points)
        return result

    # ---------- побудова ----------

    def arc_polyline(self, a, b, c, d):
        """Цикл побудови дуги: u змінюється від 0 до 1 з кроком 1 / steps."""
        return [cubic_point(a, b, c, d, i / self.steps) for i in range(self.steps + 1)]

    # ---------- редагування ----------

    def move_point(self, k, j, dx, dy):
        """Зсув реперної точки j контуру k на (dx, dy).

        Вузлова точка A тягне за собою сусідні точки C попередньої та B наступної
        дуги, тому дотичні в ній зберігаються. Проміжна точка показується
        зсунутою вздовж дотичної в k разів, тому її зсув ділиться на k - точка
        йде точно за курсором. На проміжних кадрах анімації зсуваються і
        початкова, і кінцева фігура.
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
