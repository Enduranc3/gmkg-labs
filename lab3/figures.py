"""Кінцева фігура анімації - сонце з променями.

Кожен контур хмари переходить в одну замкнену криву сонця з тією ж кількістю
дуг: найбільший контур - у диск, решта - у промені (витягнуті еліпси).
Дуги нової фігури будуються у формі Фергюсона (формула 1.3 методички): для
кожної дуги відомі кінці r(0), r(1) та похідні r'(0), r'(1), звідки реперні
точки кубічної параболи:  B = r(0) + r'(0) / 3,  C = r(1) - r'(1) / 3.
"""
import math

SUN_CENTER = (0.0, 0.5)
SUN_RADIUS = 3.2
RAY_DISTANCE = 5.0         # відстань від центру сонця до центру променя, см
RAY_LENGTH = 1.1           # піввісь променя вздовж радіуса, см
RAY_WIDTH = 0.3            # піввісь променя поперек, см
PHASES = 120               # скільки зсувів початкової точки перебирається


def ellipse(cx, cy, a, b, angle):
    """Еліпс P(s) і його похідна P'(s); s від 0 до 1 - один повний оберт."""
    ca, sa = math.cos(angle), math.sin(angle)
    k = 2 * math.pi

    def point(s):
        x, y = a * math.cos(k * s), b * math.sin(k * s)
        return cx + x * ca - y * sa, cy + x * sa + y * ca

    def derivative(s):
        dx, dy = -k * a * math.sin(k * s), k * b * math.cos(k * s)
        return dx * ca - dy * sa, dx * sa + dy * ca

    return point, derivative


def signed_area(points):
    """Орієнтована площа многокутника: > 0, якщо обхід проти годинникової стрілки."""
    n = len(points)
    return sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1]
               for i in range(n)) / 2


def centroid(points):
    return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))


def place_on_curve(points, curve):
    """Розкладає дуги контуру по замкненій кривій curve = (P, P').

    Частка параметра s на кожну дугу - середнє між рівним розподілом і часткою
    довжини її хорди у вихідному контурі (довгі дуги отримують більшу ділянку,
    але не більше половини кривої). Напрямок обходу зберігається, а початкова
    фаза обирається так, щоб вузлові точки пройшли найкоротший сумарний шлях.
    """
    point, derivative = curve
    anchors = points[0::3]
    n = len(anchors)
    chords = [math.dist(anchors[i], anchors[(i + 1) % n]) for i in range(n)]
    shares = [(c / sum(chords) + 1 / n) / 2 for c in chords]
    s = [sum(shares[:i]) for i in range(n)]
    direction = 1 if signed_area(anchors) > 0 else -1

    def travel(phase):
        return sum(math.dist(anchors[i], point(phase + direction * s[i])) ** 2 for i in range(n))

    phase = min((j / PHASES for j in range(PHASES)), key=travel)
    result = []
    for i in range(n):
        s0 = phase + direction * s[i]
        ds = direction * shares[i]
        p0, d0 = point(s0), derivative(s0)
        p1, d1 = point(s0 + ds), derivative(s0 + ds)
        # r'(u) = P'(s)·ds, бо s = s0 + u·ds
        result += [p0,
                   (p0[0] + d0[0] * ds / 3, p0[1] + d0[1] * ds / 3),
                   (p1[0] - d1[0] * ds / 3, p1[1] - d1[1] * ds / 3)]
    return result


def sun_figure(contours):
    """Реперні точки сонця для кожного контуру (та сама кількість точок)."""
    disc = max(range(len(contours)), key=lambda k: len(contours[k]))
    rays = [k for k in range(len(contours)) if k != disc]

    def polar_angle(k):
        x, y = centroid(contours[k])
        return math.atan2(y - SUN_CENTER[1], x - SUN_CENTER[0])

    # промені розставляються рівномірно в тому ж порядку, в якому контури
    # розташовані навколо центру, з найменшим поворотом
    rays.sort(key=polar_angle)
    m = len(rays)
    step = 2 * math.pi / m
    offset = math.atan2(sum(math.sin(polar_angle(k) - i * step) for i, k in enumerate(rays)),
                        sum(math.cos(polar_angle(k) - i * step) for i, k in enumerate(rays)))

    result = [None] * len(contours)
    result[disc] = place_on_curve(contours[disc], ellipse(*SUN_CENTER, SUN_RADIUS, SUN_RADIUS, 0))
    for i, k in enumerate(rays):
        angle = offset + i * step
        cx = SUN_CENTER[0] + RAY_DISTANCE * math.cos(angle)
        cy = SUN_CENTER[1] + RAY_DISTANCE * math.sin(angle)
        result[k] = place_on_curve(contours[k], ellipse(cx, cy, RAY_LENGTH, RAY_WIDTH, angle))
    return result
