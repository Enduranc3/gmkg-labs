"""Панель керування: параметри фігури, зсув та обертання, анімація, проекція, інформація."""
import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox,
                               QLabel, QLayout, QPushButton, QScrollArea, QSpinBox,
                               QVBoxLayout, QWidget)

from polyhedron import DEFAULTS
from scene_widget import DEFAULT_ALPHA

STANDARD_ALPHA = math.degrees(math.asin(1 / 3))    # коефіцієнти 0,943 : 0,471 : 0,943
ISOMETRIC_ALPHA = math.degrees(math.atan(1 / math.sqrt(2)))    # sin β = 1/√2, тобто 45°
ALPHA_LIMIT = 44.0     # при |α| = 45° кут β = 90°, і осі X та Z збігаються на проекції

# Параметри фігури: атрибут -> (підпис, мінімум поля, максимум поля, крок, анімація від, до)
PARAMETERS = {
    "scale": ("Масштаб", 0.2, 4.0, 0.1, 0.6, 1.6),
    "height": ("Висота", 40.0, 600.0, 10.0, 200.0, 480.0),
    "width": ("Ширина", 20.0, 300.0, 5.0, 40.0, 140.0),
    "depth": ("Глибина", 20.0, 300.0, 5.0, 40.0, 140.0),
}


def spin(value, lo=-1000.0, hi=1000.0, step=1.0, decimals=2):
    box = QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    box.setMinimumWidth(80)
    return box


def xyz_row(grid, row, boxes):
    for i, (name, box) in enumerate(zip(("Ox", "Oy", "Oz"), boxes)):
        grid.addWidget(QLabel(name), row, 2 * i)
        grid.addWidget(box, row, 2 * i + 1)


class ControlsPanel(QScrollArea):
    def __init__(self, body, scene, parent=None):
        super().__init__(parent)
        self.body = body
        self.scene = scene
        self.anim_t = 0.0              # положення параметра між мінімумом і максимумом
        self.anim_direction = 1        # куди зараз змінюється параметр
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.on_frame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(self.build_figure_group())
        layout.addWidget(self.build_transform_group())
        layout.addWidget(self.build_animation_group())
        layout.addWidget(self.build_projection_group())
        layout.addWidget(self.build_view_group())
        layout.addWidget(self.build_info_group())
        layout.addStretch()
        # панель довша за вікно - вміст не стискається, а прокручується
        layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(400)
        self.refresh()

    # ---------- групи ----------

    def build_figure_group(self):
        group = QGroupBox("Параметри фігури")
        grid = QGridLayout(group)
        self.figure_boxes = {}
        for row, (attr, (text, lo, hi, step, *_)) in enumerate(PARAMETERS.items()):
            box = spin(DEFAULTS[attr], lo, hi, step)
            box.valueChanged.connect(lambda value, a=attr: self.on_parameter(a, value))
            grid.addWidget(QLabel(text), row, 0)
            grid.addWidget(box, row, 1)
            self.figure_boxes[attr] = box
        return group

    def build_transform_group(self):
        group = QGroupBox("Евклідові перетворення фігури")
        grid = QGridLayout(group)
        grid.addWidget(QLabel("Зсув, од."), 0, 0, 1, 6)
        self.shift_boxes = [spin(100, step=10), spin(100, step=10), spin(0, step=10)]
        xyz_row(grid, 1, self.shift_boxes)
        grid.addWidget(QLabel("Обертання навколо власних осей, °"), 2, 0, 1, 6)
        self.rotate_boxes = [spin(0, -360, 360, 5), spin(90, -360, 360, 5), spin(0, -360, 360, 5)]
        xyz_row(grid, 3, self.rotate_boxes)
        btn_apply = QPushButton("Застосувати")
        btn_apply.clicked.connect(self.apply_transform)
        grid.addWidget(btn_apply, 4, 0, 1, 6)
        btn_default = QPushButton("За замовчуванням")
        btn_default.clicked.connect(self.set_defaults)
        grid.addWidget(btn_default, 5, 0, 1, 6)
        return group

    def build_animation_group(self):
        group = QGroupBox("Анімація")
        grid = QGridLayout(group)
        self.anim_parameter = QComboBox()
        for attr, (text, *_) in PARAMETERS.items():
            self.anim_parameter.addItem(text, attr)
        self.anim_parameter.setCurrentIndex(self.anim_parameter.findData("height"))
        self.anim_parameter.currentIndexChanged.connect(self.on_anim_parameter)
        grid.addWidget(QLabel("Параметр"), 0, 0, 1, 2)
        grid.addWidget(self.anim_parameter, 0, 2, 1, 4)
        self.anim_min, self.anim_max = spin(0), spin(0)
        grid.addWidget(QLabel("Від"), 1, 0)
        grid.addWidget(self.anim_min, 1, 1, 1, 2)
        grid.addWidget(QLabel("до"), 1, 3)
        grid.addWidget(self.anim_max, 1, 4, 1, 2)
        self.anim_frames = QSpinBox()
        self.anim_frames.setRange(2, 1000)
        self.anim_frames.setValue(60)
        grid.addWidget(QLabel("Кадрів від мінімуму до максимуму"), 2, 0, 1, 4)
        grid.addWidget(self.anim_frames, 2, 4, 1, 2)
        grid.addWidget(QLabel("Зсув за кадр, од."), 3, 0, 1, 6)
        self.anim_shift = [spin(1.5, step=0.5), spin(0, step=0.5), spin(0, step=0.5)]
        xyz_row(grid, 4, self.anim_shift)
        grid.addWidget(QLabel("Обертання за кадр, °"), 5, 0, 1, 6)
        self.anim_rotate = [spin(0, -90, 90, 0.5), spin(3, -90, 90, 0.5), spin(0, -90, 90, 0.5)]
        xyz_row(grid, 6, self.anim_rotate)
        self.btn_anim = QPushButton("Старт анімації")
        self.btn_anim.clicked.connect(self.toggle_animation)
        grid.addWidget(self.btn_anim, 7, 0, 1, 6)
        hint = QLabel("Зсув змінює напрямок разом із параметром,\n"
                      "тому фігура не виходить за межі сцени.")
        hint.setStyleSheet("color: #555;")
        grid.addWidget(hint, 8, 0, 1, 6)
        self.on_anim_parameter()
        return group

    def build_projection_group(self):
        group = QGroupBox("Параметри проекції: диметрія на площину y = 0")
        grid = QGridLayout(group)
        hint = QLabel("M = Rx(β) · Rz(α) · M_орт(y = 0)\n"
                      "sin²β = sin²α / (1 − sin²α), тобто sin β = ±tg α")
        hint.setStyleSheet("color: #555;")
        grid.addWidget(hint, 0, 0, 1, 3)
        self.alpha_box = spin(self.scene.alpha, -ALPHA_LIMIT, ALPHA_LIMIT, 1.0)
        self.alpha_box.valueChanged.connect(self.on_alpha)
        grid.addWidget(QLabel("α - кут навколо осі Z, °"), 1, 0, 1, 2)
        grid.addWidget(self.alpha_box, 1, 2)
        grid.addWidget(QLabel("β - кут навколо осі X, °"), 2, 0, 1, 2)
        self.beta_label = QLabel()
        grid.addWidget(self.beta_label, 2, 2)
        self.beta_box = QCheckBox("Додатний кут β (спостерігач з боку −Z)")
        self.beta_box.toggled.connect(self.on_beta_sign)
        grid.addWidget(self.beta_box, 3, 0, 1, 3)
        presets = (("Диметрія\n0,94 : 0,47 : 0,94", STANDARD_ALPHA),
                   ("Ізометрія\nα = 35,26°", ISOMETRIC_ALPHA),
                   ("Вид зверху\nα = 0°", 0.0))
        for i, (text, value) in enumerate(presets):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _, v=value: self.alpha_box.setValue(v))
            grid.addWidget(btn, 4, i)
        return group

    def build_view_group(self):
        group = QGroupBox("Відображення")
        grid = QGridLayout(group)
        for i, (attr, text) in enumerate((("show_grid", "Сітка на площині y = 0"),
                                          ("show_pivot", "Центр C і власні осі"))):
            box = QCheckBox(text)
            box.setChecked(getattr(self.scene, attr))
            box.toggled.connect(lambda checked, a=attr: self.on_check(a, checked))
            grid.addWidget(box, 0, i)
        hint = QLabel("Сцена перетягується мишею, масштаб - коліщатком.")
        hint.setStyleSheet("color: #555;")
        grid.addWidget(hint, 1, 0, 1, 2)
        return group

    def build_info_group(self):
        group = QGroupBox("Інформація")
        layout = QVBoxLayout(group)
        self.info = QLabel()
        self.info.setTextFormat(Qt.RichText)
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        self.matrix_label = QLabel()
        self.matrix_label.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        layout.addWidget(self.matrix_label)
        return group

    # ---------- обробники ----------

    def on_parameter(self, attr, value):
        setattr(self.body, attr, value)
        self.refresh()

    def apply_transform(self):
        self.body.shift(*(box.value() for box in self.shift_boxes))
        self.body.rotate(*(box.value() for box in self.rotate_boxes))
        self.refresh()

    def set_defaults(self):
        """Повертає фігуру та проекцію до початкового стану."""
        self.timer.stop()
        self.update_anim_button()
        self.body.reset()
        for attr, box in self.figure_boxes.items():
            self.set_silently(box, getattr(self.body, attr))
        self.beta_box.setChecked(False)
        self.alpha_box.setValue(DEFAULT_ALPHA)
        self.refresh()

    def on_alpha(self, value):
        self.scene.alpha = value
        self.scene.update_projection()
        self.refresh()

    def on_beta_sign(self, checked):
        self.scene.beta_positive = checked
        self.scene.update_projection()
        self.refresh()

    def on_check(self, attr, checked):
        setattr(self.scene, attr, checked)
        self.scene.update()

    @staticmethod
    def set_silently(box, value):
        box.blockSignals(True)
        box.setValue(value)
        box.blockSignals(False)

    # ---------- анімація ----------

    def on_anim_parameter(self):
        _, lo, hi, step, start, end = PARAMETERS[self.anim_parameter.currentData()]
        for box, value in ((self.anim_min, start), (self.anim_max, end)):
            box.setRange(lo, hi)
            box.setSingleStep(step)
            box.setValue(value)

    def toggle_animation(self):
        if self.timer.isActive():
            self.timer.stop()
        else:
            # анімація продовжується з поточного значення параметра
            lo, hi = self.anim_min.value(), self.anim_max.value()
            value = getattr(self.body, self.anim_parameter.currentData())
            self.anim_t = min(max((value - lo) / (hi - lo), 0.0), 1.0) if hi != lo else 0.0
            self.timer.start()
        self.update_anim_button()

    def update_anim_button(self):
        self.btn_anim.setText(("Стоп" if self.timer.isActive() else "Старт") + " анімації")

    def on_frame(self):
        """Один кадр анімації: параметр змінюється між мінімумом і максимумом туди
        й назад, водночас фігура зсувається та обертається на заданий оффсет."""
        self.anim_t += self.anim_direction / self.anim_frames.value()
        direction = self.anim_direction
        if self.anim_t >= 1:
            self.anim_t, self.anim_direction = 1.0, -1
        elif self.anim_t <= 0:
            self.anim_t, self.anim_direction = 0.0, 1
        attr = self.anim_parameter.currentData()
        lo, hi = self.anim_min.value(), self.anim_max.value()
        value = lo + (hi - lo) * self.anim_t
        setattr(self.body, attr, value)
        self.set_silently(self.figure_boxes[attr], value)
        self.body.shift(*(direction * box.value() for box in self.anim_shift))
        self.body.rotate(*(box.value() for box in self.anim_rotate))
        self.refresh()

    # ---------- інформація ----------

    def refresh(self):
        scene, body = self.scene, self.body
        self.beta_label.setText(f"{scene.beta:.2f}")
        vertices, edges, faces = len(body.world_vertices()), len(body.edges), len(body.faces)
        cx, cy, cz = body.world_pivot()
        rows = [
            ("Вершин / ребер / граней", f"{vertices} / {edges} / {faces}"),
            ("V − E + F", str(vertices - edges + faces)),
            ("Зсув фігури", "({:.1f}; {:.1f}; {:.1f})".format(*body.offset)),
            ("Центр обертання C", f"({cx:.1f}; {cy:.1f}; {cz:.1f})"),
        ]
        for name, axis in (("X", (1, 0, 0)), ("Y", (0, 1, 0)), ("Z", (0, 0, 1))):
            x, _, z = scene.projection.apply(*axis)
            rows.append((f"U'<sub>{name}</sub> (x'; z'), довжина",
                         f"({x:.3f}; {z:.3f}), {math.hypot(x, z):.3f}"))
        self.info.setText("<table cellspacing='3'>" + "".join(
            f"<tr><td><b>{name}:</b></td><td>{value}</td></tr>" for name, value in rows) + "</table>")
        self.matrix_label.setText("Матриця проекції M:\n" + repr(scene.projection))
        scene.update()
