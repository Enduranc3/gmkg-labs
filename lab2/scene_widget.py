"""Сцена: осі з сіткою на чотири чверті, крива, дотична, нормаль, асимптота."""
import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from core.matrix import Matrix3


class SceneWidget(QWidget):
    zoomChanged = Signal(float)

    def __init__(self, curve, parent=None):
        super().__init__(parent)
        self.curve = curve
        self.model_matrix = Matrix3()     # накопичені евклідові перетворення кривої
        self.px_per_cm = 35.0
        self.pan_x, self.pan_y = 0.0, 0.0
        self.point_phi = math.radians(60)  # точка дотику
        self.line_length = 3.0             # половина довжини дотичної/нормалі, см
        self.show_point = True
        self.show_tangent = True
        self.show_normal = True
        self.show_asymptote = True
        self.rotation_point = (0.0, 0.0)
        self._drag_pos = None
        self.setMinimumSize(700, 600)

    # ---------- керування ----------

    def apply_model_transform(self, matrix):
        self.model_matrix = self.model_matrix @ matrix
        self.update()

    def reset_model_transform(self):
        self.model_matrix = Matrix3()
        self.update()

    # ---------- координати ----------

    def to_screen(self, point):
        """Світові координати (см) -> пікселі; вісь Y розвертається вгору."""
        x, y = point
        cx = self.width() / 2 + self.pan_x
        cy = self.height() / 2 + self.pan_y
        return QPointF(cx + x * self.px_per_cm, cy - y * self.px_per_cm)

    def visible_range(self):
        """Межі видимої області у світових координатах."""
        k = self.px_per_cm
        cx = self.width() / 2 + self.pan_x
        cy = self.height() / 2 + self.pan_y
        return (-cx / k, (self.width() - cx) / k, -(self.height() - cy) / k, cy / k)

    def draw_polyline(self, painter, points, matrix=None):
        """Кожна точка множиться на матрицю перетворень і з'єднується з попередньою."""
        prev = None
        for x, y in points:
            p = matrix.apply(x, y) if matrix is not None else (x, y)
            cur = self.to_screen(p) if p is not None else None
            if prev is not None and cur is not None:
                painter.drawLine(prev, cur)
            prev = cur

    def draw_dot(self, painter, point, color, radius=4, label=None):
        s = self.to_screen(point)
        painter.setPen(QPen(QColor(color), 1))
        painter.setBrush(QColor(color))
        painter.drawEllipse(s, radius, radius)
        painter.setBrush(Qt.NoBrush)
        if label:
            painter.drawText(QPointF(s.x() + 7, s.y() - 7), label)

    # ---------- малювання ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))
        self.draw_grid(painter)
        self.draw_axes(painter)
        self.draw_curve(painter)
        self.draw_dot(painter, self.rotation_point, "#d62728", 3.5, "P")
        painter.end()

    def draw_grid(self, painter):
        x0, x1, y0, y1 = self.visible_range()
        painter.setPen(QPen(QColor(225, 225, 225), 1))
        for x in range(math.floor(x0), math.ceil(x1) + 1):
            self.draw_polyline(painter, [(x, y0), (x, y1)])
        for y in range(math.floor(y0), math.ceil(y1) + 1):
            self.draw_polyline(painter, [(x0, y), (x1, y)])

    def draw_axes(self, painter):
        x0, x1, y0, y1 = self.visible_range()
        arrow = 10 / self.px_per_cm
        painter.setPen(QPen(QColor(200, 40, 40), 1.6))
        self.draw_polyline(painter, [(x0, 0), (x1, 0)])
        self.draw_polyline(painter, [(x1 - arrow, arrow / 2), (x1, 0), (x1 - arrow, -arrow / 2)])
        painter.setPen(QPen(QColor(40, 150, 40), 1.6))
        self.draw_polyline(painter, [(0, y0), (0, y1)])
        self.draw_polyline(painter, [(-arrow / 2, y1 - arrow), (0, y1), (arrow / 2, y1 - arrow)])

        painter.setPen(QColor(90, 90, 90))
        painter.setFont(QFont("Arial", 8))
        step = 1 if self.px_per_cm >= 25 else (2 if self.px_per_cm >= 12 else 5)
        for x in range(math.ceil(x0 / step) * step, math.floor(x1) + 1, step):
            if x:
                s = self.to_screen((x, 0))
                painter.drawText(QPointF(s.x() - 4, s.y() + 14), str(x))
        for y in range(math.ceil(y0 / step) * step, math.floor(y1) + 1, step):
            if y:
                s = self.to_screen((0, y))
                painter.drawText(QPointF(s.x() - 20, s.y() + 4), str(y))
        s = self.to_screen((0, 0))
        painter.drawText(QPointF(s.x() - 12, s.y() + 14), "0")
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.drawText(self.to_screen((x1, 0)) + QPointF(-14, 20), "X")
        painter.drawText(self.to_screen((0, y1)) + QPointF(8, 16), "Y")

    def draw_curve(self, painter):
        m = self.model_matrix
        x0, x1, y0, y1 = self.visible_range()
        reach = 2 * max(abs(x0), abs(x1), abs(y0), abs(y1)) + 50

        if self.show_asymptote:
            pen = QPen(QColor(0, 150, 150), 1.4, Qt.DashLine)
            painter.setPen(pen)
            self.draw_polyline(painter, self.curve.asymptote(reach), m)

        painter.setPen(QPen(QColor(10, 10, 10), 2))
        for branch in self.curve.branches(r_max=reach):
            self.draw_polyline(painter, branch, m)

        phi = self.point_phi
        tangent, normal = self.curve.tangent_and_normal(phi, self.line_length)
        if self.show_tangent:
            painter.setPen(QPen(QColor(30, 80, 220), 1.8))
            self.draw_polyline(painter, tangent, m)
        if self.show_normal:
            painter.setPen(QPen(QColor(230, 120, 0), 1.8))
            self.draw_polyline(painter, normal, m)
        if self.show_point or self.show_tangent or self.show_normal:
            self.draw_dot(painter, m.apply(*self.curve.point(phi)), "#1a9a1a", 4)

    # ---------- миша ----------

    def mousePressEvent(self, event):
        self._drag_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.position() - self._drag_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self._drag_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self.px_per_cm = min(max(self.px_per_cm * factor, 5.0), 150.0)
        self.zoomChanged.emit(self.px_per_cm)
        self.update()
