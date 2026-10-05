"""Сцена: координатні осі з сіткою та деталь.

Ланцюжок перетворень для кожної точки:
    локальні координати деталі
      -> матриця деталі (зсув, обертання, симетрія, масштаб)   - лише для деталі
      -> афінне та/або проективне перетворення                 - для деталі і сітки
      -> екранні пікселі (масштаб px/мм + розворот осі Y)
"""
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from core.matrix import Matrix3, translation
from detail_model import CENTER

GRID_W, GRID_H, GRID_STEP = 200, 160, 10
START_POSITION = (40, 70)   # де на сітці стоїть центр отвору Ø15 на старті


class SceneWidget(QWidget):
    zoomChanged = Signal(float)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.model_matrix = translation(*START_POSITION)
        self.affine_matrix = None        # None - перетворення вимкнене
        self.projective_matrix = None
        self.markers = {}                # назва -> (x, y, колір)
        self.px_per_mm = 4.0
        self.offset_x, self.offset_y = 70.0, 60.0   # положення початку координат на екрані
        self._drag_pos = None
        self.setMinimumSize(700, 600)
        self.setMouseTracking(False)

    # ---------- керування станом ----------

    def apply_model_transform(self, matrix):
        """Додає перетворення до вже накопичених: M = M · T."""
        self.model_matrix = self.model_matrix @ matrix
        self.update()

    def reset_model_transform(self):
        self.model_matrix = translation(*START_POSITION)
        self.update()

    def set_affine(self, matrix):
        self.affine_matrix = matrix
        self.update()

    def set_projective(self, matrix):
        self.projective_matrix = matrix
        self.update()

    def set_zoom(self, px_per_mm):
        self.px_per_mm = px_per_mm
        self.update()

    def set_marker(self, name, x, y, color):
        self.markers[name] = (x, y, color)
        self.update()

    # ---------- перетворення координат ----------

    def scene_matrix(self):
        """Спільна для сітки і деталі матриця: афінна, потім проективна."""
        m = Matrix3()
        if self.affine_matrix is not None:
            m = m @ self.affine_matrix
        if self.projective_matrix is not None:
            m = m @ self.projective_matrix
        return m

    def to_screen(self, point):
        """Світові координати (мм) -> пікселі вікна.

        У Qt вісь Y напрямлена вниз, тому y береться з мінусом відносно
        нижнього краю - так вісь ординат на екрані дивиться вгору.
        """
        x, y = point
        return QPointF(self.offset_x + x * self.px_per_mm,
                       self.height() - self.offset_y - y * self.px_per_mm)

    def draw_polyline(self, painter, points, matrix):
        """Перетворює кожну точку матрицею і з'єднує сусідні точки відрізками."""
        prev = None
        for x, y in points:
            p = matrix.apply(x, y)
            cur = self.to_screen(p) if p is not None else None
            if prev is not None and cur is not None:
                painter.drawLine(prev, cur)
            prev = cur

    # ---------- малювання ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))
        scene = self.scene_matrix()
        self.draw_grid(painter, scene)
        self.draw_axes(painter, scene)
        self.draw_detail(painter, self.model_matrix @ scene)
        self.draw_markers(painter, scene)
        painter.end()

    def draw_grid(self, painter, scene):
        painter.setPen(QPen(QColor(205, 205, 205), 1))
        for x in range(0, GRID_W + 1, GRID_STEP):       # вертикальні лінії
            self.draw_polyline(painter, [(x, 0), (x, GRID_H)], scene)
        for y in range(0, GRID_H + 1, GRID_STEP):       # горизонтальні лінії
            self.draw_polyline(painter, [(0, y), (GRID_W, y)], scene)

    def draw_axes(self, painter, scene):
        painter.setPen(QPen(QColor(40, 40, 40), 1.6))
        ax, ay = GRID_W + 15, GRID_H + 15
        # Осі разом зі стрілками задані у світових координатах,
        # тому деформуються разом із сіткою при афінних/проективних перетвореннях
        self.draw_polyline(painter, [(0, 0), (ax, 0)], scene)
        self.draw_polyline(painter, [(ax - 6, 2.5), (ax, 0), (ax - 6, -2.5)], scene)
        self.draw_polyline(painter, [(0, 0), (0, ay)], scene)
        self.draw_polyline(painter, [(-2.5, ay - 6), (0, ay), (2.5, ay - 6)], scene)

        painter.setFont(QFont("Arial", 9))
        painter.setPen(QColor(60, 60, 60))
        for value in range(0, GRID_W + 1, 2 * GRID_STEP):
            self.draw_label(painter, scene, (value, 0), str(value), 0, 16)
        for value in range(2 * GRID_STEP, GRID_H + 1, 2 * GRID_STEP):
            self.draw_label(painter, scene, (0, value), str(value), -26, 4)
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        self.draw_label(painter, scene, (ax, 0), "X", 4, 18)
        self.draw_label(painter, scene, (0, ay), "Y", -18, 4)

    def draw_label(self, painter, scene, point, text, dx, dy):
        p = scene.apply(*point)
        if p is not None:
            s = self.to_screen(p)
            painter.drawText(QPointF(s.x() + dx - (4 if dx == 0 else 0), s.y() + dy), text)

    def draw_detail(self, painter, matrix):
        contour_pen = QPen(QColor(15, 15, 15), 2.2)
        contour_pen.setCapStyle(Qt.RoundCap)
        center_pen = QPen(QColor(90, 90, 200), 1, Qt.DashDotLine)
        for points, style in self.model.build():
            painter.setPen(center_pen if style == CENTER else contour_pen)
            self.draw_polyline(painter, points, matrix)

    def draw_markers(self, painter, scene):
        painter.setFont(QFont("Arial", 9))
        for name, (x, y, color) in self.markers.items():
            p = scene.apply(x, y)
            if p is None:
                continue
            s = self.to_screen(p)
            painter.setPen(QPen(QColor(color), 1))
            painter.setBrush(QColor(color))
            painter.drawEllipse(s, 3.5, 3.5)
            painter.drawText(QPointF(s.x() + 6, s.y() - 6), name)
        painter.setBrush(Qt.NoBrush)

    # ---------- миша: перетягування сцени і зум ----------

    def mousePressEvent(self, event):
        self._drag_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.position() - self._drag_pos
            self.offset_x += delta.x()
            self.offset_y -= delta.y()
            self._drag_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self.px_per_mm = min(max(self.px_per_mm * factor, 0.5), 30.0)
        self.zoomChanged.emit(self.px_per_mm)
        self.update()
