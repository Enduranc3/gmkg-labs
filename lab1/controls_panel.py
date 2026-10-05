"""Панель керування: розміри деталі та параметри перетворень."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDoubleSpinBox, QGridLayout, QGroupBox, QLabel,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from core.matrix import (affine, point_symmetry, projective, rotation, scaling,
                         translation)
from detail_model import PARAMS
from scene_widget import START_POSITION


def spin(value, lo=-1000.0, hi=1000.0, step=1.0, decimals=1):
    box = QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    box.setMinimumWidth(70)
    return box


class ControlsPanel(QScrollArea):
    def __init__(self, model, scene, parent=None):
        super().__init__(parent)
        self.model = model
        self.scene = scene
        self.size_boxes = {}

        content = QWidget()
        self.layout_ = QVBoxLayout(content)
        self.layout_.addWidget(self.build_view_group())
        self.layout_.addWidget(self.build_size_group())
        self.layout_.addWidget(self.build_shift_group())
        self.layout_.addWidget(self.build_rotation_group())
        self.layout_.addWidget(self.build_symmetry_group())
        self.layout_.addWidget(self.build_scale_group())
        self.layout_.addWidget(self.build_affine_group())
        self.layout_.addWidget(self.build_projective_group())
        self.layout_.addStretch()

        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(400)

        scene.zoomChanged.connect(self.on_scene_zoom)
        self.update_markers()

    # ---------- групи елементів ----------

    def build_view_group(self):
        group = QGroupBox("Відображення")
        grid = QGridLayout(group)
        self.zoom = spin(self.scene.px_per_mm, 0.5, 30, 0.5)
        self.zoom.valueChanged.connect(self.scene.set_zoom)
        grid.addWidget(QLabel("Масштаб, px/мм"), 0, 0)
        grid.addWidget(self.zoom, 0, 1)
        btn_default = QPushButton("Деталь за замовчуванням")
        btn_default.clicked.connect(self.reset_sizes)
        btn_reset = QPushButton("Скинути перетворення деталі")
        btn_reset.clicked.connect(self.scene.reset_model_transform)
        grid.addWidget(btn_default, 1, 0, 1, 2)
        grid.addWidget(btn_reset, 2, 0, 1, 2)
        return group

    def build_size_group(self):
        group = QGroupBox("Розміри деталі, мм")
        grid = QGridLayout(group)
        for i, (key, (label, default, lo, hi, hint)) in enumerate(PARAMS.items()):
            box = spin(default, lo, hi)
            box.setToolTip(hint)
            box.valueChanged.connect(lambda value, k=key: self.on_size_changed(k, value))
            caption = QLabel(label)
            caption.setToolTip(hint)
            row, col = divmod(i, 2)
            grid.addWidget(caption, row, col * 2)
            grid.addWidget(box, row, col * 2 + 1)
            self.size_boxes[key] = box
        return group

    def build_shift_group(self):
        group = QGroupBox("Зсув (евклідове)")
        grid = QGridLayout(group)
        self.dx, self.dy = spin(20), spin(10)
        grid.addWidget(QLabel("dx"), 0, 0)
        grid.addWidget(self.dx, 0, 1)
        grid.addWidget(QLabel("dy"), 0, 2)
        grid.addWidget(self.dy, 0, 3)
        btn = QPushButton("Застосувати")
        btn.clicked.connect(lambda: self.scene.apply_model_transform(
            translation(self.dx.value(), self.dy.value())))
        grid.addWidget(btn, 1, 0, 1, 4)
        return group

    def build_rotation_group(self):
        group = QGroupBox("Обертання навколо точки (евклідове)")
        grid = QGridLayout(group)
        self.rot_x, self.rot_y = spin(100), spin(70)
        self.rot_angle = spin(45, -360, 360, 5)
        for box in (self.rot_x, self.rot_y):
            box.valueChanged.connect(self.update_markers)
        grid.addWidget(QLabel("x"), 0, 0)
        grid.addWidget(self.rot_x, 0, 1)
        grid.addWidget(QLabel("y"), 0, 2)
        grid.addWidget(self.rot_y, 0, 3)
        grid.addWidget(QLabel("кут, °"), 1, 0)
        grid.addWidget(self.rot_angle, 1, 1)
        btn = QPushButton("Застосувати")
        btn.clicked.connect(lambda: self.scene.apply_model_transform(
            rotation(self.rot_x.value(), self.rot_y.value(), self.rot_angle.value())))
        grid.addWidget(btn, 2, 0, 1, 4)
        return group

    def build_symmetry_group(self):
        group = QGroupBox("Симетрія відносно точки (афінне)")
        grid = QGridLayout(group)
        self.sym_x, self.sym_y = spin(100), spin(80)
        for box in (self.sym_x, self.sym_y):
            box.valueChanged.connect(self.update_markers)
        grid.addWidget(QLabel("x"), 0, 0)
        grid.addWidget(self.sym_x, 0, 1)
        grid.addWidget(QLabel("y"), 0, 2)
        grid.addWidget(self.sym_y, 0, 3)
        btn = QPushButton("Застосувати")
        btn.clicked.connect(lambda: self.scene.apply_model_transform(
            point_symmetry(self.sym_x.value(), self.sym_y.value())))
        grid.addWidget(btn, 1, 0, 1, 4)
        return group

    def build_scale_group(self):
        group = QGroupBox("Масштабування (афінне)")
        grid = QGridLayout(group)
        self.sx = spin(1.5, -10, 10, 0.1, 2)
        self.sy = spin(1.5, -10, 10, 0.1, 2)
        self.sc_x, self.sc_y = spin(START_POSITION[0]), spin(START_POSITION[1])
        grid.addWidget(QLabel("Sx"), 0, 0)
        grid.addWidget(self.sx, 0, 1)
        grid.addWidget(QLabel("Sy"), 0, 2)
        grid.addWidget(self.sy, 0, 3)
        grid.addWidget(QLabel("центр x"), 1, 0)
        grid.addWidget(self.sc_x, 1, 1)
        grid.addWidget(QLabel("центр y"), 1, 2)
        grid.addWidget(self.sc_y, 1, 3)
        btn = QPushButton("Застосувати")
        btn.clicked.connect(lambda: self.scene.apply_model_transform(
            scaling(self.sx.value(), self.sy.value(), self.sc_x.value(), self.sc_y.value())))
        grid.addWidget(btn, 2, 0, 1, 4)
        return group

    def build_affine_group(self):
        group = QGroupBox("Афінне перетворення системи координат")
        group.setCheckable(True)
        group.setChecked(False)
        grid = QGridLayout(group)
        self.affine_boxes = [spin(v, -100, 100, 0.1, 2) for v in (1, 0, 0, 1, 0, 0)]
        names = ("Xx", "Xy", "Yx", "Yy", "Ox", "Oy")
        for i, (name, box) in enumerate(zip(names, self.affine_boxes)):
            row, col = divmod(i, 2)
            grid.addWidget(QLabel(name), row, col * 2)
            grid.addWidget(box, row, col * 2 + 1)
            box.valueChanged.connect(self.update_affine)
        group.toggled.connect(self.update_affine)
        self.affine_group = group
        return group

    def build_projective_group(self):
        group = QGroupBox("Проективне перетворення системи координат")
        group.setCheckable(True)
        group.setChecked(False)
        grid = QGridLayout(group)
        defaults = (450, 0, 2, 0, 600, 1, 0, 0, 600)
        names = ("Xx", "Xy", "wX", "Yx", "Yy", "wY", "Ox", "Oy", "w0")
        self.projective_boxes = [spin(v, -5000, 5000) for v in defaults]
        for i, (name, box) in enumerate(zip(names, self.projective_boxes)):
            row, col = divmod(i, 3)
            grid.addWidget(QLabel(name), row, col * 2)
            grid.addWidget(box, row, col * 2 + 1)
            box.valueChanged.connect(self.update_projective)
        group.toggled.connect(self.update_projective)
        self.projective_group = group
        return group

    # ---------- обробники ----------

    def on_size_changed(self, key, value):
        self.model.set(key, value)
        self.sync_size_boxes()
        self.scene.update()

    def sync_size_boxes(self):
        """Показує значення після перевірки обмежень моделі."""
        for key, box in self.size_boxes.items():
            if abs(box.value() - self.model.p[key]) > 1e-9:
                box.blockSignals(True)
                box.setValue(self.model.p[key])
                box.blockSignals(False)

    def reset_sizes(self):
        self.model.reset()
        self.sync_size_boxes()
        self.scene.update()

    def update_affine(self):
        if self.affine_group.isChecked():
            self.scene.set_affine(affine(*(b.value() for b in self.affine_boxes)))
        else:
            self.scene.set_affine(None)

    def update_projective(self):
        if self.projective_group.isChecked():
            self.scene.set_projective(projective(*(b.value() for b in self.projective_boxes)))
        else:
            self.scene.set_projective(None)

    def update_markers(self):
        self.scene.set_marker("P", self.rot_x.value(), self.rot_y.value(), "#d62728")
        self.scene.set_marker("S", self.sym_x.value(), self.sym_y.value(), "#2ca02c")

    def on_scene_zoom(self, value):
        self.zoom.blockSignals(True)
        self.zoom.setValue(value)
        self.zoom.blockSignals(False)
