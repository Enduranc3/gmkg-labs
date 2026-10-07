"""Декартів лист (варіант 1): x³ + y³ = 3axy.

Крива будується в полярній системі координат:
    r(φ) = 3a·cosφ·sinφ / (cos³φ + sin³φ),   0 ≤ φ ≤ π,
    x = r·cosφ,  y = r·sinφ.
При φ = 3π/4 знаменник дорівнює нулю - тут крива "йде на нескінченність",
тому область визначення розбивається на дві гілки.
"""
import math

from core.numeric import derivative, simpson

BREAK_DEG = 135.0          # 3π/4 - розрив кривої


class FoliumOfDescartes:
    def __init__(self, a=2.0):
        self.a = a

    # ---------- рівняння кривої ----------

    def r(self, phi):
        """Полярний радіус, формула (5) методички."""
        c, s = math.cos(phi), math.sin(phi)
        return 3 * self.a * c * s / (c ** 3 + s ** 3)

    def dr(self, phi):
        """Похідна r'(φ) за правилом диференціювання частки."""
        c, s = math.cos(phi), math.sin(phi)
        num, num_d = c * s, math.cos(2 * phi)
        den, den_d = c ** 3 + s ** 3, 3 * s * c * (s - c)
        return 3 * self.a * (num_d * den - num * den_d) / den ** 2

    def point(self, phi):
        """Перехід від полярних координат до декартових, формули (2), (4)."""
        r = self.r(phi)
        return r * math.cos(phi), r * math.sin(phi)

    def velocity(self, phi):
        """Похідні x'(φ), y'(φ) для кривої, заданої в полярній СК (формула 11)."""
        r, dr = self.r(phi), self.dr(phi)
        c, s = math.cos(phi), math.sin(phi)
        return dr * c - r * s, dr * s + r * c

    def acceleration(self, phi):
        """Другі похідні x''(φ), y''(φ) - чисельно з аналітичних перших."""
        return (derivative(lambda p: self.velocity(p)[0], phi),
                derivative(lambda p: self.velocity(p)[1], phi))

    # ---------- побудова ----------

    def branches(self, step_deg=0.25, r_max=200.0):
        """Цикл побудови кривої: φ змінюється від 0° до 180° з кроком step.

        На кроці φ = 135° точки не з'єднуються лінією (розрив кривої),
        а точки з |r| > r_max відкидаються, щоб не малювати "нескінченність".
        """
        result, current = [], []
        steps = int(round(180 / step_deg))
        for i in range(steps + 1):
            phi_deg = i * step_deg
            if abs(phi_deg - BREAK_DEG) < 1e-9:
                result.append(current)
                current = []
                continue
            phi = math.radians(phi_deg)
            if abs(self.r(phi)) > r_max:
                if current:
                    result.append(current)
                current = []
                continue
            current.append(self.point(phi))
        result.append(current)
        return [b for b in result if len(b) >= 2]

    def tangent_and_normal(self, phi, length):
        """Відрізки дотичної та нормалі довжиною 2·length з центром у точці кривої.

        Кутовий коефіцієнт дотичної f' = y'/x' (формула 12), рівняння
        дотичної y = y0 + f'(x - x0) (10), нормалі y = y0 - (x - x0)/f' (15).
        Замість другої точки при x = 0 береться одиничний вектор напрямку,
        тому відрізок завжди симетричний відносно точки дотику.
        """
        x0, y0 = self.point(phi)
        dx, dy = self.velocity(phi)
        norm = math.hypot(dx, dy)
        ux, uy = dx / norm, dy / norm          # напрямок дотичної
        nx, ny = -uy, ux                        # перпендикуляр - напрямок нормалі
        tangent = [(x0 - ux * length, y0 - uy * length), (x0 + ux * length, y0 + uy * length)]
        normal = [(x0 - nx * length, y0 - ny * length), (x0 + nx * length, y0 + ny * length)]
        return tangent, normal

    def slope(self, phi):
        dx, dy = self.velocity(phi)
        return math.inf if abs(dx) < 1e-12 else dy / dx

    def asymptote(self, half_length=200.0):
        """Похила асимптота x + y + a = 0, тобто y = kx + b, k = -1, b = -a (17)-(19)."""
        k, b = -1.0, -self.a
        return [(-half_length, k * -half_length + b), (half_length, k * half_length + b)]

    # ---------- розрахунки ----------

    def arc_length(self, phi_from, phi_to):
        """Довжина дуги в полярній СК, формула (20): ∫ sqrt(r² + r'²) dφ."""
        return simpson(lambda p: math.sqrt(self.r(p) ** 2 + self.dr(p) ** 2), phi_from, phi_to)

    def arc_from_origin(self, phi):
        """Довжина дуги від початку координат до точки φ вздовж своєї гілки."""
        deg = math.degrees(phi)
        if deg <= 90:
            return self.arc_length(0, phi)               # петля
        if deg < BREAK_DEG:
            return self.arc_length(math.pi / 2, phi)     # гілка в IV чверті
        return self.arc_length(phi, math.pi)             # гілка в II чверті

    def loop_length(self):
        return self.arc_length(0, math.pi / 2)

    def loop_area(self):
        """Площа петлі в полярній СК: S = 1/2 ∫ r² dφ, 0 ≤ φ ≤ π/2."""
        return simpson(lambda p: self.r(p) ** 2 / 2, 0, math.pi / 2)

    def asymptote_area(self):
        """Площа між гілками кривої та асимптотою (аналітично): 3a²/2."""
        return 1.5 * self.a ** 2

    def curvature_radius(self, phi):
        """R = (x'² + y'²)^(3/2) / |x'y'' - y'x''|."""
        dx, dy = self.velocity(phi)
        ddx, ddy = self.acceleration(phi)
        cross = dx * ddy - dy * ddx
        if abs(cross) < 1e-12:
            return math.inf
        return (dx * dx + dy * dy) ** 1.5 / abs(cross)

    def inflection_points(self, step_deg=0.1):
        """Пошук точок, де x'y'' - y'x'' (знак кривини) змінює знак.

        Для Декартового листа таких точок на скінченній частині кривої немає -
        кривина зберігає знак на кожній гілці.
        """
        found, prev = [], None
        steps = int(180 / step_deg)
        for i in range(1, steps):
            deg = i * step_deg
            if abs(deg - BREAK_DEG) < 2:            # околиця розриву
                prev = None
                continue
            phi = math.radians(deg)
            dx, dy = self.velocity(phi)
            ddx, ddy = self.acceleration(phi)
            cross = dx * ddy - dy * ddx
            if prev is not None and cross * prev < 0:
                found.append(self.point(phi))
            prev = cross
        return found
