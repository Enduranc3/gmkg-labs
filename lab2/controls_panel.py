"""Панель керування: параметри кривої, анімація, дотична/нормаль, розрахунки, перетворення."""
import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox,
                               QLabel, QPushButton, QScrollArea, QSlider,
                               QVBoxLayout, QWidget)

from core.matrix import rotation, translation
from folium import BREAK_DEG

DEFAULT_A = 2.0
DEFAULT_PHI = 60.0
A_STEP = 0.05          # зміна параметра a за один кадр анімації
PHI_STEP = 0.5         # зміна кута точки за один кадр анімації, градуси


def spin(value, lo=-1000.0, hi=1000.0, step=1.0, decimals=2):
    box = QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    box.setMinimumWidth(80)
    return box


def fmt(value):
    return "∞" if math.isinf(value) else f"{value:.4f}"


class ControlsPanel(QScrollArea):
    def __init__(self, curve, scene, parent=None):
        super().__init__(parent)
        self.curve = curve
        self.scene = scene
        self.a_direction = 1        # куди зараз рухається a під час анімації
        self.animate_a = False
        self.animate_point = False
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.on_frame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.build_view_group())
        layout.addWidget(self.build_curve_group())
        layout.addWidget(self.build_animation_group())
        layout.addWidget(self.build_point_group())
        layout.addWidget(self.build_info_group())
        layout.addWidget(self.build_transform_group())
        layout.addStretch()
        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(400)

        scene.zoomChanged.connect(self.on_scene_zoom)
        self.refresh()

    # ---------- групи ----------

    def build_view_group(self):
        group = QGroupBox("Відображення")
        grid = QGridLayout(group)
        self.zoom = spin(self.scene.px_per_cm, 5, 150, 5, 1)
        self.zoom.valueChanged.connect(self.on_zoom)
        grid.addWidget(QLabel("Масштаб, px/см"), 0, 0)
        grid.addWidget(self.zoom, 0, 1)
        btn = QPushButton("Параметри за замовчуванням")
        btn.clicked.connect(self.set_defaults)
        grid.addWidget(btn, 1, 0, 1, 2)
        return group

    def build_curve_group(self):
        group = QGroupBox("Декартів лист: x³ + y³ = 3axy")
        grid = QGridLayout(group)
        self.a_box = spin(DEFAULT_A, 0.1, 20, 0.1)
        self.a_box.valueChanged.connect(self.on_a_changed)
        grid.addWidget(QLabel("Параметр a, см"), 0, 0)
        grid.addWidget(self.a_box, 0, 1)
        hint = QLabel("r = 3a·cosφ·sinφ / (cos³φ + sin³φ),  0 ≤ φ ≤ π\n"
                      "розрив при φ = 3π/4 (135°)")
        hint.setStyleSheet("color: #555;")
        grid.addWidget(hint, 1, 0, 1, 2)
        return group

    def build_animation_group(self):
        group = QGroupBox("Анімація")
        grid = QGridLayout(group)
        self.a_min, self.a_max = spin(1, 0.1, 20, 0.5), spin(6, 0.1, 20, 0.5)
        grid.addWidget(QLabel("a від"), 0, 0)
        grid.addWidget(self.a_min, 0, 1)
        grid.addWidget(QLabel("до"), 0, 2)
        grid.addWidget(self.a_max, 0, 3)
        self.btn_anim_a = QPushButton("Старт анімації параметра a")
        self.btn_anim_a.clicked.connect(self.toggle_animate_a)
        self.btn_anim_point = QPushButton("Старт руху точки по кривій")
        self.btn_anim_point.clicked.connect(self.toggle_animate_point)
        grid.addWidget(self.btn_anim_a, 1, 0, 1, 4)
        grid.addWidget(self.btn_anim_point, 2, 0, 1, 4)
        return group

    def build_point_group(self):
        group = QGroupBox("Точка кривої, дотична, нормаль, асимптота")
        grid = QGridLayout(group)
        self.phi_box = spin(DEFAULT_PHI, 0, 180, 1, 1)
        self.phi_slider = QSlider(Qt.Horizontal)
        self.phi_slider.setRange(0, 1800)
        self.phi_slider.setValue(int(DEFAULT_PHI * 10))
        self.phi_box.valueChanged.connect(self.on_phi_box)
        self.phi_slider.valueChanged.connect(lambda v: self.phi_box.setValue(v / 10))
        grid.addWidget(QLabel("Кут φ точки, °"), 0, 0)
        grid.addWidget(self.phi_box, 0, 1)
        grid.addWidget(self.phi_slider, 1, 0, 1, 2)
        self.length_box = spin(self.scene.line_length, 0.5, 50, 0.5)
        self.length_box.valueChanged.connect(self.on_length)
        grid.addWidget(QLabel("Півдовжина прямих, см"), 2, 0)
        grid.addWidget(self.length_box, 2, 1)

        self.checks = {}
        for i, (attr, text) in enumerate((("show_point", "Точка"), ("show_tangent", "Дотична"),
                                          ("show_normal", "Нормаль"), ("show_asymptote", "Асимптота"))):
            box = QCheckBox(text)
            box.setChecked(getattr(self.scene, attr))
            box.toggled.connect(lambda checked, a=attr: self.on_check(a, checked))
            grid.addWidget(box, 3 + i // 2, i % 2)
            self.checks[attr] = box
        return group

    def build_info_group(self):
        group = QGroupBox("Розрахунки")
        layout = QVBoxLayout(group)
        self.info = QLabel()
        self.info.setTextFormat(Qt.RichText)
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        return group

    def build_transform_group(self):
        group = QGroupBox("Евклідові перетворення кривої")
        grid = QGridLayout(group)
        self.dx, self.dy = spin(2), spin(1)
        grid.addWidget(QLabel("dx"), 0, 0)
        grid.addWidget(self.dx, 0, 1)
        grid.addWidget(QLabel("dy"), 0, 2)
        grid.addWidget(self.dy, 0, 3)
        btn_shift = QPushButton("Зсув")
        btn_shift.clicked.connect(lambda: self.scene.apply_model_transform(
            translation(self.dx.value(), self.dy.value())))
        grid.addWidget(btn_shift, 1, 0, 1, 4)

        self.rot_x, self.rot_y = spin(-2), spin(2)
        self.rot_angle = spin(90, -360, 360, 5, 1)
        for box in (self.rot_x, self.rot_y):
            box.valueChanged.connect(self.update_rotation_point)
        grid.addWidget(QLabel("Px"), 2, 0)
        grid.addWidget(self.rot_x, 2, 1)
        grid.addWidget(QLabel("Py"), 2, 2)
        grid.addWidget(self.rot_y, 2, 3)
        grid.addWidget(QLabel("кут, °"), 3, 0)
        grid.addWidget(self.rot_angle, 3, 1)
        btn_rot = QPushButton("Обертання навколо точки P")
        btn_rot.clicked.connect(lambda: self.scene.apply_model_transform(
            rotation(self.rot_x.value(), self.rot_y.value(), self.rot_angle.value())))
        grid.addWidget(btn_rot, 4, 0, 1, 4)
        btn_reset = QPushButton("Скинути перетворення")
        btn_reset.clicked.connect(self.scene.reset_model_transform)
        grid.addWidget(btn_reset, 5, 0, 1, 4)
        self.update_rotation_point()
        return group

    # ---------- обробники ----------

    def on_zoom(self, value):
        self.scene.px_per_cm = value
        self.scene.update()

    def on_scene_zoom(self, value):
        self.zoom.blockSignals(True)
        self.zoom.setValue(value)
        self.zoom.blockSignals(False)

    def on_a_changed(self, value):
        self.curve.a = value
        self.refresh()

    def on_phi_box(self, value):
        # точка φ = 135° не належить кривій - перескакуємо її
        if abs(value - BREAK_DEG) < 0.5:
            value = BREAK_DEG + (0.5 if value >= BREAK_DEG else -0.5)
        self.scene.point_phi = math.radians(value)
        self.phi_slider.blockSignals(True)
        self.phi_slider.setValue(int(round(value * 10)))
        self.phi_slider.blockSignals(False)
        self.refresh()

    def on_length(self, value):
        self.scene.line_length = value
        self.scene.update()

    def on_check(self, attr, checked):
        setattr(self.scene, attr, checked)
        self.scene.update()

    def update_rotation_point(self):
        self.scene.rotation_point = (self.rot_x.value(), self.rot_y.value())
        self.scene.update()

    def set_defaults(self):
        self.animate_a = self.animate_point = False
        self.update_timer()
        self.a_box.setValue(DEFAULT_A)
        self.phi_box.setValue(DEFAULT_PHI)
        self.scene.reset_model_transform()

    # ---------- анімація ----------

    def toggle_animate_a(self):
        self.animate_a = not self.animate_a
        self.update_timer()

    def toggle_animate_point(self):
        self.animate_point = not self.animate_point
        self.update_timer()

    def update_timer(self):
        self.btn_anim_a.setText(("Стоп" if self.animate_a else "Старт") + " анімації параметра a")
        self.btn_anim_point.setText(("Стоп" if self.animate_point else "Старт") + " руху точки по кривій")
        if self.animate_a or self.animate_point:
            self.timer.start()
        else:
            self.timer.stop()

    def on_frame(self):
        """Один кадр анімації."""
        if self.animate_a:
            # a рухається між межами: дійшли до краю - змінюємо напрямок
            a = self.curve.a + self.a_direction * A_STEP
            if a >= self.a_max.value():
                a, self.a_direction = self.a_max.value(), -1
            elif a <= self.a_min.value():
                a, self.a_direction = self.a_min.value(), 1
            self.a_box.setValue(a)
        if self.animate_point:
            phi = self.phi_box.value() + PHI_STEP
            self.phi_box.setValue(0 if phi > 180 else phi)

    # ---------- розрахунки ----------

    def refresh(self):
        c, phi = self.curve, self.scene.point_phi
        x0, y0 = c.point(phi)
        k = c.slope(phi)
        if math.isinf(k):
            tangent_eq, normal_eq = f"x = {x0:.3f}", f"y = {y0:.3f}"
        elif abs(k) < 1e-9:
            tangent_eq, normal_eq = f"y = {y0:.3f}", f"x = {x0:.3f}"
        else:
            tangent_eq = f"y = {y0:.3f} + {k:.3f}·(x − {x0:.3f})"
            normal_eq = f"y = {y0:.3f} − (x − {x0:.3f}) / {k:.3f}"
        inflections = c.inflection_points()
        infl_text = (", ".join(f"({x:.2f}; {y:.2f})" for x, y in inflections) if inflections
                     else "немає (x'y'' − y'x'' не змінює знак)")
        rows = [
            ("Точка дотику", f"φ = {math.degrees(phi):.1f}°, ({x0:.3f}; {y0:.3f})"),
            ("Похідна f' = y'/x'", fmt(k)),
            ("Дотична", tangent_eq),
            ("Нормаль", normal_eq),
            ("Асимптота", f"x + y + {c.a:.2f} = 0"),
            ("Радіус кривини в точці", fmt(c.curvature_radius(phi)) + " см"),
            ("Довжина дуги від O до точки", f"{c.arc_from_origin(phi):.4f} см"),
            ("Довжина петлі", f"{c.loop_length():.4f} см"),
            ("Площа петлі (½∫r²dφ)", f"{c.loop_area():.4f} см²"),
            ("Площа між кривою та асимптотою", f"3a²/2 = {c.asymptote_area():.4f} см²"),
            ("Точки перегину", infl_text),
        ]
        self.info.setText("<table cellspacing='3'>" + "".join(
            f"<tr><td><b>{name}:</b></td><td>{value}</td></tr>" for name, value in rows) + "</table>")
        self.scene.update()
