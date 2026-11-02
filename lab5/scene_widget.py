"""Сцена: осі координат, сітка на площині y = 0, грановане тіло.

Усе малюється через одну матрицю проекції: кожна точка простору множиться на M,
а точка картинної площини (x', z') стає пікселем екрана. Вісь Z на екрані
спрямована вниз - так виглядає площина XOZ, якщо дивитись на неї зверху (з боку +Y).
"""
import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from core.matrix import dimetric_beta, dimetry_y0

DEFAULT_ALPHA = 30.0       # sin β = tg 30° = 1/√3, коефіцієнти 0,866 : 0,707 : 0,866
AXIS_LENGTH = 400
GRID_SIZE = 300
GRID_STEP = 50
OWN_AXIS_LENGTH = 60

EDGE_COLOR = QColor(10, 10, 10)
GRID_COLOR = QColor(232, 232, 232)
PIVOT_COLOR = QColor(214, 39, 40)
AXIS_COLORS = {"X": QColor(230, 20, 20), "Y": QColor(40, 200, 40), "Z": QColor(20, 20, 220)}


class SceneWidget(QWidget):
    def __init__(self, body, parent=None):
        super().__init__(parent)
        self.body = body
        self.alpha = DEFAULT_ALPHA
        self.beta_positive = False
        self.update_projection()
        self.zoom = 1.0                 # пікселів на одиницю
        self.pan_x, self.pan_y = 0.0, 0.0
        self.show_grid = True
        self.show_pivot = True
        self._drag_pos = None
        self.setMinimumSize(700, 600)

    # ---------- проекція ----------

    def update_projection(self):
        """Кут β обчислюється за α з умови диметрії, потрібен лише його знак."""
        beta = dimetric_beta(self.alpha)
        self.beta = beta if self.beta_positive else -beta
        self.projection = dimetry_y0(self.alpha, self.beta)

    def to_screen(self, point):
        """Точка простору -> проекція на площину y = 0 -> пікселі."""
        x, _, z = self.projection.apply(*point)
        return QPointF(self.width() / 2 + self.pan_x + x * self.zoom,
                       self.height() / 2 + self.pan_y + z * self.zoom)

    # ---------- малювання ----------

    def draw_segment(self, painter, a, b):
        painter.drawLine(self.to_screen(a), self.to_screen(b))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))
        if self.show_grid:
            self.draw_grid(painter)
        self.draw_axes(painter)
        self.draw_body(painter)
        if self.show_pivot:
            self.draw_pivot(painter)
        painter.end()

    def draw_grid(self, painter):
        painter.setPen(QPen(GRID_COLOR, 1))
        for v in range(-GRID_SIZE, GRID_SIZE + 1, GRID_STEP):
            self.draw_segment(painter, (v, 0, -GRID_SIZE), (v, 0, GRID_SIZE))
            self.draw_segment(painter, (-GRID_SIZE, 0, v), (GRID_SIZE, 0, v))

    def draw_axes(self, painter):
        origin = self.to_screen((0, 0, 0))
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        ends = {"X": (AXIS_LENGTH, 0, 0), "Y": (0, AXIS_LENGTH, 0), "Z": (0, 0, AXIS_LENGTH)}
        for name, end in ends.items():
            s = self.to_screen(end)
            painter.setPen(QPen(AXIS_COLORS[name], 1.6))
            painter.drawLine(origin, s)
            dx, dy = s.x() - origin.x(), s.y() - origin.y()
            length = math.hypot(dx, dy)
            if length > 1:                  # при α = 0 вісь Y проектується в точку
                dx, dy = dx / length, dy / length
                for side in (-1, 1):
                    painter.drawLine(s, QPointF(s.x() - 10 * dx + side * 4 * dy,
                                                s.y() - 10 * dy - side * 4 * dx))
            painter.drawText(s + QPointF(6, -6), name)

    def draw_body(self, painter):
        vertices = [self.to_screen(v) for v in self.body.world_vertices()]
        painter.setPen(QPen(EDGE_COLOR, 1.6))
        for a, b in self.body.edges:
            painter.drawLine(vertices[a], vertices[b])

    def draw_pivot(self, painter):
        """Центр обертання C і власні осі тіла, проведені з нього."""
        center = self.body.world_pivot()
        for name, end in zip("XYZ", self.body.own_axes(OWN_AXIS_LENGTH)):
            painter.setPen(QPen(AXIS_COLORS[name], 1.4, Qt.DashLine))
            self.draw_segment(painter, center, end)
        s = self.to_screen(center)
        painter.setPen(QPen(PIVOT_COLOR, 1))
        painter.setBrush(PIVOT_COLOR)
        painter.drawEllipse(s, 3.5, 3.5)
        painter.setBrush(Qt.NoBrush)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(s + QPointF(7, 14), "C")

    # ---------- миша ----------

    def mousePressEvent(self, event):
        self._drag_pos = event.position()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            pos = event.position()
            self.pan_x += pos.x() - self._drag_pos.x()
            self.pan_y += pos.y() - self._drag_pos.y()
            self._drag_pos = pos
            self.update()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self.zoom = min(max(self.zoom * factor, 0.2), 6.0)
        self.update()
