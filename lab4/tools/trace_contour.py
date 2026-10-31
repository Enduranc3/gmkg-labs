"""Допоміжний інструмент: оцифрування контуру №30 з PDF завдання.

Не потрібен для запуску програми - він один раз згенерував contour_data.py.

Рисунок варіанта у Lab3_MainTask.pdf збережений як векторна графіка: кожен штрих
(хмара, блискавка, краплі дощу) - замкнена ламана з сотень коротких відрізків.
Інструмент бере ці ламані, знаходить кутові точки і наближає кожну ділянку між
ними дугами кубічних парабол методом найменших квадратів (алгоритм Шнайдера):
якщо похибка дуги більша за допустиму - ділянка ділиться в точці найбільшої
похибки, і кожна половина наближається окремо.

Запуск (потрібні PyMuPDF і numpy):
    python tools/trace_contour.py "<шлях>/Lab3_MainTask.pdf" > contour_data.py
"""
import math
import sys

import fitz
import numpy as np

PAGE = 4                           # сторінка з контурами 19-30
CELL = fitz.Rect(450, 445, 560, 552)  # клітинка таблиці з контуром №30
WIDTH_CM = 14.0                    # ширина рисунка на сцені
TOLERANCE = 0.35                   # допустима похибка дуги, pt рисунка
CORNER_DEG = 55.0                  # поворот, більший за цей кут, - кутова точка
MAX_HANDLE = 6.0                   # найбільша довжина ланок AB і CD, pt рисунка

NAMES = {0: "Блискавка", 1: "Вістря блискавки (ліве)", 2: "Вістря блискавки (праве)",
         3: "Хмара: ліва завитка", 4: "Хмара: верхня хвиля",
         5: "Хмара: нижня хвиля", 6: "Хмара: права завитка"}


def read_outlines(pdf_path):
    """Білі заливки всередині клітинки - внутрішні контури штрихів."""
    page = fitz.open(pdf_path)[PAGE]
    result = []
    for d in page.get_drawings():
        if d.get("fill") == (1.0, 1.0, 1.0) and CELL.contains(d["rect"]):
            pts = [(it[1].x, it[1].y) for it in d["items"] if it[0] == "l"]
            result.append(np.array(pts))
    return result


def resample(pts, step):
    """Рівномірна розстановка точок по довжині замкненої ламаної."""
    closed = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    n = max(int(s[-1] / step), 12)
    t = np.linspace(0, s[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, s, closed[:, 0]), np.interp(t, s, closed[:, 1])])


def find_corners(pts, k):
    """Індекси точок, де напрямок ламаної різко змінюється (локальні максимуми)."""
    n = len(pts)
    ang = np.zeros(n)
    for i in range(n):
        a, b = pts[i] - pts[i - k], pts[(i + k) % n] - pts[i]
        cos = a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)
        ang[i] = math.degrees(math.acos(max(-1.0, min(1.0, cos))))
    corners = []
    for i in range(n):
        window = [ang[(i + j) % n] for j in range(-k, k + 1)]
        if ang[i] > CORNER_DEG and ang[i] == max(window):
            corners.append(i)
    return corners


def bezier(ctrl, u):
    u = np.asarray(u)[:, None]
    return ((1 - u) ** 3 * ctrl[0] + 3 * u * (1 - u) ** 2 * ctrl[1]
            + 3 * u ** 2 * (1 - u) * ctrl[2] + u ** 3 * ctrl[3])


def fit_segment(pts, t1, t2, tol):
    """Дуги, що наближають відкриту ділянку pts з дотичними t1 (на початку) і t2 (у кінці)."""
    if len(pts) < 4:
        d = np.linalg.norm(pts[-1] - pts[0]) / 3
        return [np.array([pts[0], pts[0] + t1 * d, pts[-1] + t2 * d, pts[-1]])]
    u = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    u /= u[-1]
    for _ in range(8):
        ctrl = least_squares(pts, u, t1, t2)
        err = np.linalg.norm(bezier(ctrl, u) - pts, axis=1)
        handle = max(np.linalg.norm(ctrl[1] - ctrl[0]), np.linalg.norm(ctrl[2] - ctrl[3]))
        if err.max() < tol and (handle < MAX_HANDLE or len(pts) < 8):
            return [ctrl]
        u = reparametrize(ctrl, pts, u)
    split = int(np.argmax(err[1:-1])) + 1 if err.max() >= tol else len(pts) // 2
    split = min(max(split, 2), len(pts) - 3)
    tc = pts[split - 1] - pts[split + 1]
    tc /= np.linalg.norm(tc)
    return (fit_segment(pts[:split + 1], t1, tc, tol)
            + fit_segment(pts[split:], -tc, t2, tol))


def least_squares(pts, u, t1, t2):
    """Довжини дотичних a1, a2, за яких сума квадратів відхилень мінімальна."""
    p0, p3 = pts[0], pts[-1]
    b0, b1, b2, b3 = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u ** 2 * (1 - u), u ** 3
    a1, a2 = np.outer(b1, t1), np.outer(b2, t2)
    rest = pts - (np.outer(b0 + b1, p0) + np.outer(b2 + b3, p3))
    c = np.array([[np.sum(a1 * a1), np.sum(a1 * a2)], [np.sum(a1 * a2), np.sum(a2 * a2)]])
    x = np.array([np.sum(a1 * rest), np.sum(a2 * rest)])
    chord = np.linalg.norm(p3 - p0)
    try:
        al1, al2 = np.linalg.solve(c, x)
    except np.linalg.LinAlgError:
        al1 = al2 = chord / 3
    if al1 < chord * 1e-3 or al2 < chord * 1e-3:
        al1 = al2 = chord / 3
    return np.array([p0, p0 + t1 * al1, p3 + t2 * al2, p3])


def reparametrize(ctrl, pts, u):
    """Один крок Ньютона: уточнення параметра u для кожної точки."""
    d1 = 3 * np.array([ctrl[1] - ctrl[0], ctrl[2] - ctrl[1], ctrl[3] - ctrl[2]])
    d2 = 2 * np.array([d1[1] - d1[0], d1[2] - d1[1]])
    q = bezier(ctrl, u) - pts
    uu = u[:, None]
    q1 = (1 - uu) ** 2 * d1[0] + 2 * uu * (1 - uu) * d1[1] + uu ** 2 * d1[2]
    q2 = (1 - uu) * d2[0] + uu * d2[1]
    num = np.sum(q * q1, axis=1)
    den = np.sum(q1 * q1 + q * q2, axis=1)
    new = u - np.where(np.abs(den) > 1e-12, num / den, 0)
    new[0], new[-1] = 0.0, 1.0
    return np.clip(np.maximum.accumulate(new), 0, 1)


def fit_closed(pts):
    pts = resample(pts, 0.12)
    n = len(pts)
    breaks = find_corners(pts, 6)
    corner = set(breaks)
    if len(breaks) < 2:                    # гладкий контур - розрізаємо штучно
        extra = [0, n // 2] if not breaks else [(breaks[0] + n // 2) % n]
        breaks = sorted(set(breaks + extra))
    arcs = []
    for j, a in enumerate(breaks):
        b = breaks[(j + 1) % len(breaks)]
        idx = [(a + i) % n for i in range(((b - a) % n) + 1)]
        seg = pts[idx]
        t1 = tangent(pts, a, forward=True, smooth=a not in corner)
        t2 = tangent(pts, b, forward=False, smooth=b not in corner)
        arcs += fit_segment(seg, t1, t2, TOLERANCE)
    return arcs


def tangent(pts, i, forward, smooth, k=3):
    n = len(pts)
    if smooth:
        t = pts[(i + k) % n] - pts[i - k]
        t = t if forward else -t
    else:
        t = pts[(i + k) % n] - pts[i] if forward else pts[i - k] - pts[i]
    return t / np.linalg.norm(t)


def plural(n):
    if n % 10 == 1 and n % 100 != 11:
        return "дуга"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "дуги"
    return "дуг"


def main():
    outlines = read_outlines(sys.argv[1])
    all_pts = np.vstack(outlines)
    lo, hi = all_pts.min(axis=0), all_pts.max(axis=0)
    k = WIDTH_CM / (hi[0] - lo[0])
    center = (lo + hi) / 2

    def to_cm(p):                          # pt -> см, вісь Y вгору, центр у початку координат
        return round(float((p[0] - center[0]) * k), 2), round(float((center[1] - p[1]) * k), 2)

    print('"""Реперні точки контуру №30 (хмара, блискавка, дощ), см.\n')
    print("Згенеровано tools/trace_contour.py. Кожен контур замкнений: точки йдуть як")
    print("A0, B0, C0, A1, B1, C1, ..., дуга i - це A_i, B_i, C_i, A_(i+1).")
    print('"""\n')
    print("CONTOURS = [")
    total = 0
    for i, outline in enumerate(outlines):
        arcs = fit_closed(outline)
        total += len(arcs)
        flat = [to_cm(p) for arc in arcs for p in arc[:3]]
        name = NAMES.get(i, "Крапля дощу")
        print(f"    # {name}: {len(arcs)} {plural(len(arcs))}")
        print("    [")
        for j in range(0, len(flat), 3):
            print("        " + ", ".join(f"({x}, {y})" for x, y in flat[j:j + 3]) + ",")
        print("    ],")
    print("]")
    print(f"# всього дуг: {total}", file=sys.stderr)


if __name__ == "__main__":
    main()
