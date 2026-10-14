"""Сцена: осі з сіткою, криволінійний контур, характеристична ламана, рухомі точки."""
import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from contour import cubic_point
from core.matrix import Matrix3

PICK_RADIUS = 8            # на якій відстані від точки (px) її можна схопити мишею

CURVE_COLOR = QColor(10, 10, 10)
ANCHOR_COLOR = QColor(10, 10, 10)
HANDLE_COLOR = QColor(40, 170, 40)
POLYGON_COLOR = QColor(170, 170, 170)
SELECTED_COLOR = QColor(30, 90, 230)


class SceneWidget(QWidget):
    zoomChanged = Signal(float)
    selectionChanged = Signal()

    def __init__(self, contour, parent=None):
        super().__init__(parent)
        self.contour = contour
        self.model_matrix = Matrix3()     # накопичені евклідові перетворення контуру
        self.px_per_cm = 42.0
        self.pan_x, self.pan_y = 0.0, 0.0
        self.show_grid = True
        self.show_polygon = True
        self.show_points = True
        self.rotation_point = (0.0, 0.0)
        self.selected = (6, 4)            # (контур, дуга) - вибрана дуга
        self._drag_point = None           # (контур, точка), яку зараз тягнуть
        self._drag_pos = None
        self.setMouseTracking(True)
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

    def to_world(self, pos):
        """Пікселі -> світові координати (обернене до to_screen)."""
        cx = self.width() / 2 + self.pan_x
        cy = self.height() / 2 + self.pan_y
        return (pos.x() - cx) / self.px_per_cm, (cy - pos.y()) / self.px_per_cm

    def visible_range(self):
        """Межі видимої області у світових координатах."""
        k = self.px_per_cm
        cx = self.width() / 2 + self.pan_x
        cy = self.height() / 2 + self.pan_y
        return (-cx / k, (self.width() - cx) / k, -(self.height() - cy) / k, cy / k)

    def draw_polyline(self, painter, points):
        painter.drawPolyline(QPolygonF([self.to_screen(p) for p in points]))

    def draw_dot(self, painter, point, color, radius=4, label=None):
        s = self.to_screen(point)
        painter.setPen(QPen(QColor(color), 1))
        painter.setBrush(QColor(color))
        painter.drawEllipse(s, radius, radius)
        painter.setBrush(Qt.NoBrush)
        if label:
            painter.drawText(QPointF(s.x() + 7, s.y() - 7), label)

    def world_points(self):
        """Реперні точки після евклідових перетворень: кожна множиться на матрицю."""
        m = self.model_matrix
        return [[m.apply(x, y) for x, y in points] for points in self.contour.control_points()]

    # ---------- малювання ----------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))
        if self.show_grid:
            self.draw_grid(painter)
            self.draw_axes(painter)
        self.draw_contour(painter)
        if self.show_grid:
            self.draw_dot(painter, self.rotation_point, "#d62728", 3.5, "P")
        painter.end()

    def draw_grid(self, painter):
        x0, x1, y0, y1 = self.visible_range()
        painter.setPen(QPen(QColor(232, 232, 232), 1))
        for x in range(math.floor(x0), math.ceil(x1) + 1):
            self.draw_polyline(painter, [(x, y0), (x, y1)])
        for y in range(math.floor(y0), math.ceil(y1) + 1):
            self.draw_polyline(painter, [(x0, y), (x1, y)])

    def draw_axes(self, painter):
        x0, x1, y0, y1 = self.visible_range()
        arrow = 10 / self.px_per_cm
        painter.setPen(QPen(QColor(220, 120, 120), 1.4))
        self.draw_polyline(painter, [(x0, 0), (x1, 0)])
        self.draw_polyline(painter, [(x1 - arrow, arrow / 2), (x1, 0), (x1 - arrow, -arrow / 2)])
        painter.setPen(QPen(QColor(110, 180, 110), 1.4))
        self.draw_polyline(painter, [(0, y0), (0, y1)])
        self.draw_polyline(painter, [(-arrow / 2, y1 - arrow), (0, y1), (arrow / 2, y1 - arrow)])

        painter.setPen(QColor(120, 120, 120))
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
        painter.setFont(QFont("Arial", 11, QFont.Bold))
        painter.drawText(self.to_screen((x1, 0)) + QPointF(-14, 20), "X")
        painter.drawText(self.to_screen((0, y1)) + QPointF(8, 16), "Y")

    def draw_contour(self, painter):
        c = self.contour
        contours = self.world_points()

        if self.show_polygon:
            # характеристична ламана кожної дуги: A - B - C - D
            painter.setPen(QPen(POLYGON_COLOR, 1))
            for points in contours:
                for i in range(len(points) // 3):
                    self.draw_polyline(painter, c.arc(points, i))

        for k, points in enumerate(contours):
            for i in range(len(points) // 3):
                selected = self.show_points and (k, i) == self.selected
                painter.setPen(QPen(SELECTED_COLOR if selected else CURVE_COLOR,
                                    2.4 if selected else 1.6))
                self.draw_polyline(painter, c.arc_polyline(*c.arc(points, i)))

        if self.show_points:
            for points in contours:
                for j, p in enumerate(points):
                    self.draw_dot(painter, p, ANCHOR_COLOR if j % 3 == 0 else HANDLE_COLOR, 3.2)
            self.draw_selected(painter, contours)

    def draw_selected(self, painter, contours):
        """Для вибраної дуги: хорда AD і точка дуги r(u) при заданому u."""
        k, i = self.selected
        a, b, cc, d = self.contour.arc(contours[k], i)
        painter.setPen(QPen(SELECTED_COLOR, 1, Qt.DashLine))
        self.draw_polyline(painter, [a, d])
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        self.draw_dot(painter, cubic_point(a, b, cc, d, self.contour.u), SELECTED_COLOR, 3.5, "r(u)")

    # ---------- миша ----------

    def pick_point(self, pos):
        """Найближча до курсора реперна точка (контур, номер) або None."""
        best, best_dist = None, PICK_RADIUS
        for k, points in enumerate(self.world_points()):
            for j, p in enumerate(points):
                s = self.to_screen(p)
                dist = math.hypot(s.x() - pos.x(), s.y() - pos.y())
                if dist <= best_dist:
                    best, best_dist = (k, j), dist
        return best

    def to_model(self, pos):
        """Курсор -> координати контуру до перетворень (множення на обернену матрицю)."""
        return self.model_matrix.inverse().apply(*self.to_world(pos))

    def mousePressEvent(self, event):
        pos = event.position()
        hit = self.pick_point(pos) if self.show_points else None
        if hit is not None:
            self._drag_point = hit
            self.selected = (hit[0], hit[1] // 3)
            self.selectionChanged.emit()
            self.update()
        self._drag_pos = pos

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._drag_point is not None:
            x0, y0 = self.to_model(self._drag_pos)
            x1, y1 = self.to_model(pos)
            self.contour.move_point(*self._drag_point, x1 - x0, y1 - y0)
            self.selectionChanged.emit()
        elif self._drag_pos is not None:
            self.pan_x += pos.x() - self._drag_pos.x()
            self.pan_y += pos.y() - self._drag_pos.y()
        else:
            near = self.show_points and self.pick_point(pos) is not None
            self.setCursor(Qt.PointingHandCursor if near else Qt.ArrowCursor)
            return
        self._drag_pos = pos
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag_point = None
        self._drag_pos = None

    def wheelEvent(self, event):
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self.px_per_cm = min(max(self.px_per_cm * factor, 5.0), 200.0)
        self.zoomChanged.emit(self.px_per_cm)
        self.update()
