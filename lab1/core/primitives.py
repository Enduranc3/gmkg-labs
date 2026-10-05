"""Побудова примітивів деталі: відрізків і дуг кола."""
import math


def segment(p1, p2):
    """Відрізок задається точками початку і кінця."""
    return [p1, p2]


def arc(cx, cy, r, deg_from, deg_to):
    """Дуга кола з центром (cx, cy) і радіусом r від кута deg_from до deg_to.

    Дуга будується посегментно з кроком 1 градус (формули 2-3):
    P_beg = (r*cos(γ) + x_cen, r*sin(γ) + y_cen),
    P_end = (r*cos(θ) + x_cen, r*sin(θ) + y_cen), θ = γ + 1°.
    Кути в обчисленнях переводяться в радіани.
    """
    points = []
    for i in range(int(deg_from), int(deg_to)):
        gamma = math.radians(i)
        theta = math.radians(i + 1)
        p_beg = (r * math.cos(gamma) + cx, r * math.sin(gamma) + cy)
        p_end = (r * math.cos(theta) + cx, r * math.sin(theta) + cy)
        if not points:
            points.append(p_beg)
        points.append(p_end)
    return points


def circle(cx, cy, r):
    """Повне коло - дуга від 0 до 360 градусів."""
    return arc(cx, cy, r, 0, 360)


def rectangle(x0, y0, x1, y1):
    """Замкнений прямокутник як ламана з п'яти точок."""
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
