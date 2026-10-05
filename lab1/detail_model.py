"""Параметрична модель деталі за індивідуальним варіантом №1.

Локальна система координат деталі: початок - у центрі отвору Ø15 (pivot point),
вісь X напрямлена вздовж планки. Усі розміри - в міліметрах.
"""
from core.primitives import arc, circle, rectangle, segment

# key: (підпис, значення за замовчуванням, мінімум, максимум, підказка)
PARAMS = {
    "body_len":  ("Корпус L",      84, 20, 200, "Довжина корпусу (100 - 16 = 84)"),
    "body_h":    ("Корпус H",      64, 10, 200, "Висота корпусу"),
    "lug_off":   ("Вушко a",       16, 0, 100, "Відстань від центру Ø15 до лівого краю корпусу"),
    "lug_r":     ("Вушко R",       16, 2, 100, "Радіус дуги вушка = половина ширини планки"),
    "hole1_d":   ("Отвір D1",      15, 0, 198, "Діаметр отвору у вушку"),
    "bar_len":   ("Планка Lп",     84, 1, 300, "Довжина планки від центру Ø15"),
    "hole2_d":   ("Отвір D2",      10, 0, 198, "Діаметр правого отвору"),
    "hole2_off": ("Отвір D2: c",   25, 0, 200, "Відстань від центру Ø10 до правого краю корпусу"),
    "slot_w":    ("Паз: ширина",   40, 0, 200, "Ширина прямокутного паза"),
    "slot_h":    ("Паз: висота",   20, 0, 198, "Висота прямокутного паза"),
    "slot_off":  ("Паз: відступ",  36, 0, 200, "Відстань від правого краю паза до правого краю корпусу"),
    "rib_x":     ("Ребро: x",      30, 0, 300, "Положення ребра від центру Ø15"),
    "rib_w":     ("Ребро: товщ.",  10, 0, 100, "Товщина ребра"),
    "step_off":  ("Уступ: відступ", 23, 0, 200, "Відстань від уступу до правого краю корпусу"),
}

CONTOUR = "contour"   # основна (товста) лінія
CENTER = "center"     # осьова (штрих-пунктирна) лінія


class DetailModel:
    def __init__(self):
        self.p = {}
        self.reset()

    def reset(self):
        """Повернення до розмірів з креслення."""
        self.p = {key: float(v[1]) for key, v in PARAMS.items()}

    def set(self, key, value):
        self.p[key] = float(value)
        self.normalize()

    def normalize(self):
        """Обмеження, які не дають деталі "розвалитися" при зміні розмірів."""
        p = self.p
        p["lug_r"] = min(p["lug_r"], p["body_h"] / 2)
        p["hole1_d"] = min(p["hole1_d"], 2 * p["lug_r"] - 1)
        p["hole2_d"] = min(p["hole2_d"], 2 * p["lug_r"] - 1)
        p["slot_h"] = min(p["slot_h"], 2 * p["lug_r"] - 1)
        p["bar_len"] = min(max(p["bar_len"], p["lug_off"] + 1), p["lug_off"] + p["body_len"])
        for key in ("hole1_d", "hole2_d", "slot_h"):
            p[key] = max(p[key], 0.0)

    def build(self):
        """Повертає список (ламана, стиль лінії) у локальних координатах деталі.

        Усі точки обчислюються з поточних параметрів, тому при зміні будь-якого
        розміру сусідні елементи автоматично з'єднуються з новими краями.
        """
        p = self.p
        a, L, R = p["lug_off"], p["body_len"], p["lug_r"]
        top, bottom = p["body_h"] / 2, -p["body_h"] / 2
        x_left, x_right = a, a + L          # краї корпусу
        x_bar = p["bar_len"]                # правий край планки

        shapes = []

        def add(points, style=CONTOUR):
            if len(points) >= 2:
                shapes.append((points, style))

        # Вушко: дуга R від верхнього краю планки до нижнього через ліву точку
        add(arc(0, 0, R, 90, 270))
        # Планка: верхній край, правий торець, нижній край
        add([(0, R), (x_bar, R), (x_bar, -R), (0, -R)])

        # Корпус: ліва сторона перекрита планкою, тому малюється двома частинами
        add([(x_left, R), (x_left, top), (x_right, top),
             (x_right, bottom), (x_left, bottom), (x_left, -R)])

        # Видимі ребра корпусу над і під планкою
        for x in (p["rib_x"], p["rib_x"] + p["rib_w"], x_right - p["step_off"]):
            if x_left < x < x_right and R < top:
                add(segment((x, top), (x, R)))
                add(segment((x, -R), (x, bottom)))

        # Отвори і паз
        if p["hole1_d"] > 0:
            add(circle(0, 0, p["hole1_d"] / 2))
        x_hole2 = x_right - p["hole2_off"]
        if p["hole2_d"] > 0:
            add(circle(x_hole2, 0, p["hole2_d"] / 2))
        slot_x1 = x_right - p["slot_off"]
        slot_x0 = slot_x1 - p["slot_w"]
        if p["slot_w"] > 0 and p["slot_h"] > 0:
            add(rectangle(slot_x0, -p["slot_h"] / 2, slot_x1, p["slot_h"] / 2))

        # Осьові лінії
        add([(-R - 6, 0), (x_right + 6, 0)], CENTER)
        add([(0, -R - 4), (0, R + 4)], CENTER)
        add([(x_hole2, -R - 4), (x_hole2, R + 4)], CENTER)
        add([((x_left + x_right) / 2, bottom - 6), ((x_left + x_right) / 2, top + 6)], CENTER)
        return shapes
