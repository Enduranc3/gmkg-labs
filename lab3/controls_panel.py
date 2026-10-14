"""Панель керування: відображення, параметри дуг, анімація, перетворення, інформація."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox,
                               QLabel, QPushButton, QScrollArea, QSlider, QSpinBox,
                               QVBoxLayout, QWidget)

from contour import DEFAULT_K, cubic_point
from core.matrix import rotation, translation

T_STEP = 0.01          # зміна кадру анімації t за один тік таймера


def spin(value, lo=-1000.0, hi=1000.0, step=1.0, decimals=2):
    box = QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    box.setMinimumWidth(80)
    return box


def arc_type(k):
    if abs(k - DEFAULT_K) < 1e-9:
        return "дуга контуру без змін"
    if k < DEFAULT_K:
        return "дотичні коротші - дуга ближче до хорди AD"
    return "дотичні довші - дуга вигинається сильніше"


class ControlsPanel(QScrollArea):
    def __init__(self, contour, scene, parent=None):
        super().__init__(parent)
        self.contour = contour
        self.scene = scene
        self.t_direction = 1           # куди зараз рухається кадр t під час анімації
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.on_frame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.build_view_group())
        layout.addWidget(self.build_arc_group())
        layout.addWidget(self.build_animation_group())
        layout.addWidget(self.build_transform_group())
        layout.addWidget(self.build_info_group())
        layout.addStretch()
        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(400)

        scene.zoomChanged.connect(self.on_scene_zoom)
        scene.selectionChanged.connect(self.refresh)
        self.refresh()

    # ---------- групи ----------

    def build_view_group(self):
        group = QGroupBox("Відображення")
        grid = QGridLayout(group)
        self.zoom = spin(self.scene.px_per_cm, 5, 200, 5, 1)
        self.zoom.valueChanged.connect(self.on_zoom)
        grid.addWidget(QLabel("Масштаб, px/см"), 0, 0)
        grid.addWidget(self.zoom, 0, 1)

        self.checks = {}
        for i, (attr, text) in enumerate((("show_polygon", "Характеристична ламана"),
                                          ("show_points", "Реперні точки"),
                                          ("show_grid", "Осі та сітка"))):
            box = QCheckBox(text)
            box.setChecked(getattr(self.scene, attr))
            box.toggled.connect(lambda checked, a=attr: self.on_check(a, checked))
            grid.addWidget(box, 1 + i // 2, i % 2)
            self.checks[attr] = box
        hint = QLabel("Точки перетягуються мишею: чорна (вузлова) тягне\n"
                      "за собою сусідні зелені, зелена рухається сама.")
        hint.setStyleSheet("color: #555;")
        grid.addWidget(hint, 3, 0, 1, 2)
        btn = QPushButton("Контур за замовчуванням")
        btn.clicked.connect(self.set_defaults)
        grid.addWidget(btn, 4, 0, 1, 2)
        return group

    def build_arc_group(self):
        group = QGroupBox("Дуги кубічних парабол (кривих Безьє 3-го порядку)")
        grid = QGridLayout(group)
        hint = QLabel("r(u) = (1−u)³·A + 3u(1−u)²·B + 3u²(1−u)·C + u³·D\n"
                      "B' = A + k·(B − A),  C' = D + k·(C − D)")
        hint.setStyleSheet("color: #555;")
        grid.addWidget(hint, 0, 0, 1, 2)
        self.selected_label = QLabel()
        grid.addWidget(self.selected_label, 1, 0, 1, 2)
        self.k_box = spin(DEFAULT_K, 0.2, 2.0, 0.1, 2)
        self.k_box.valueChanged.connect(self.on_k_changed)
        grid.addWidget(QLabel("Довжина дотичних k вибраної дуги"), 2, 0)
        grid.addWidget(self.k_box, 2, 1)
        self.type_label = QLabel()
        self.type_label.setWordWrap(True)
        grid.addWidget(self.type_label, 3, 0, 1, 2)
        btn_all = QPushButton("Це k для всіх дуг")
        btn_all.clicked.connect(self.apply_k_to_all)
        btn_reset = QPushButton("k = 1 для всіх дуг")
        btn_reset.clicked.connect(lambda: self.set_all_k(DEFAULT_K))
        grid.addWidget(btn_all, 4, 0)
        grid.addWidget(btn_reset, 4, 1)
        self.steps_box = QSpinBox()
        self.steps_box.setRange(1, 200)
        self.steps_box.setValue(self.contour.steps)
        self.steps_box.valueChanged.connect(self.on_steps_changed)
        grid.addWidget(QLabel("Кроків параметра u на дузі"), 5, 0)
        grid.addWidget(self.steps_box, 5, 1)
        self.u_box = spin(self.contour.u, 0.0, 1.0, 0.05, 2)
        self.u_box.valueChanged.connect(self.on_u_changed)
        grid.addWidget(QLabel("Параметр u точки r(u)"), 6, 0)
        grid.addWidget(self.u_box, 6, 1)
        return group

    def build_animation_group(self):
        group = QGroupBox("Анімація: хмара → сонце")
        grid = QGridLayout(group)
        self.t_slider = QSlider(Qt.Horizontal)
        self.t_slider.setRange(0, 1000)
        self.t_slider.valueChanged.connect(lambda v: self.set_t(v / 1000))
        grid.addWidget(QLabel("Кадр t"), 0, 0)
        grid.addWidget(self.t_slider, 0, 1)
        self.t_label = QLabel("0.00")
        grid.addWidget(self.t_label, 0, 2)
        self.btn_anim = QPushButton("Старт анімації")
        self.btn_anim.clicked.connect(self.toggle_animation)
        grid.addWidget(self.btn_anim, 1, 0, 1, 3)
        hint = QLabel("Кожна реперна точка рухається по своєму відрізку:\n"
                      "P(t) = P₀ + (P₁ − P₀)·t,  0 ≤ t ≤ 1")
        hint.setStyleSheet("color: #555;")
        grid.addWidget(hint, 2, 0, 1, 3)
        return group

    def build_transform_group(self):
        group = QGroupBox("Евклідові перетворення контуру")
        grid = QGridLayout(group)
        self.dx, self.dy = spin(3), spin(-2)
        grid.addWidget(QLabel("dx"), 0, 0)
        grid.addWidget(self.dx, 0, 1)
        grid.addWidget(QLabel("dy"), 0, 2)
        grid.addWidget(self.dy, 0, 3)
        btn_shift = QPushButton("Зсув")
        btn_shift.clicked.connect(lambda: self.transform(
            translation(self.dx.value(), self.dy.value())))
        grid.addWidget(btn_shift, 1, 0, 1, 4)

        self.rot_x, self.rot_y = spin(2), spin(-2)
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
        btn_rot.clicked.connect(lambda: self.transform(
            rotation(self.rot_x.value(), self.rot_y.value(), self.rot_angle.value())))
        grid.addWidget(btn_rot, 4, 0, 1, 4)
        btn_reset = QPushButton("Скинути перетворення")
        btn_reset.clicked.connect(lambda: self.transform(None))
        grid.addWidget(btn_reset, 5, 0, 1, 4)
        self.update_rotation_point()
        return group

    def build_info_group(self):
        group = QGroupBox("Інформація")
        layout = QVBoxLayout(group)
        self.info = QLabel()
        self.info.setTextFormat(Qt.RichText)
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        return group

    # ---------- обробники ----------

    def on_zoom(self, value):
        self.scene.px_per_cm = value
        self.scene.update()

    def on_scene_zoom(self, value):
        self.zoom.blockSignals(True)
        self.zoom.setValue(value)
        self.zoom.blockSignals(False)

    def on_check(self, attr, checked):
        setattr(self.scene, attr, checked)
        self.scene.update()

    def on_k_changed(self, value):
        k, i = self.scene.selected
        self.contour.k[k][i] = value
        self.refresh()

    def set_all_k(self, value):
        self.contour.k = [[value] * len(row) for row in self.contour.k]
        self.refresh()

    def apply_k_to_all(self):
        self.set_all_k(self.k_box.value())

    def on_steps_changed(self, value):
        self.contour.steps = value
        self.scene.update()

    def on_u_changed(self, value):
        self.contour.u = value
        self.refresh()

    def transform(self, matrix):
        if matrix is None:
            self.scene.reset_model_transform()
        else:
            self.scene.apply_model_transform(matrix)
        self.refresh()

    def update_rotation_point(self):
        self.scene.rotation_point = (self.rot_x.value(), self.rot_y.value())
        self.scene.update()

    def set_defaults(self):
        self.timer.stop()
        self.update_anim_button()
        self.contour.reset()
        self.t_slider.setValue(0)
        self.steps_box.setValue(self.contour.steps)
        self.u_box.setValue(self.contour.u)
        self.transform(None)

    # ---------- анімація ----------

    def set_t(self, t):
        self.contour.t = t
        self.t_label.setText(f"{t:.2f}")
        self.refresh()

    def toggle_animation(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start()
        self.update_anim_button()

    def update_anim_button(self):
        self.btn_anim.setText(("Стоп" if self.timer.isActive() else "Старт") + " анімації")

    def on_frame(self):
        """Один кадр анімації: t рухається між 0 і 1 туди й назад."""
        t = self.contour.t + self.t_direction * T_STEP
        if t >= 1:
            t, self.t_direction = 1.0, -1
        elif t <= 0:
            t, self.t_direction = 0.0, 1
        self.t_slider.setValue(round(t * 1000))

    # ---------- інформація ----------

    def refresh(self):
        c, (k, i) = self.contour, self.scene.selected
        value = c.k[k][i]
        self.selected_label.setText(f"Вибрана дуга: контур {k + 1}, дуга {i + 1} "
                                    "(клік по її точці)")
        self.k_box.blockSignals(True)
        self.k_box.setValue(value)
        self.k_box.blockSignals(False)
        self.type_label.setText(f"k = {value:.2f} — {arc_type(value)}")

        points = self.scene.world_points()
        arc = c.arc(points[k], i)
        coords = ", ".join(f"{name}({x:.2f}; {y:.2f})" for name, (x, y) in zip("ABCD", arc))
        x, y = cubic_point(*arc, c.u)
        rows = [
            ("Контурів", str(len(c.base))),
            ("Дуг кубічних парабол", str(c.arc_count())),
            ("Реперних точок", str(c.point_count())),
            ("Точок кривої на кадр", str(c.arc_count() * (c.steps + 1))),
            ("Реперні точки вибраної дуги", coords),
            (f"Точка r({c.u:.2f})", f"({x:.2f}; {y:.2f})"),
        ]
        self.info.setText("<table cellspacing='3'>" + "".join(
            f"<tr><td><b>{name}:</b></td><td>{value}</td></tr>" for name, value in rows) + "</table>")
        self.scene.update()
