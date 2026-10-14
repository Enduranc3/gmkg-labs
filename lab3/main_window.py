from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QWidget

from contour import CurvilinearContour
from controls_panel import ControlsPanel
from scene_widget import SceneWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР3. Криволінійний контур з дуг кубічних парабол (варіант 1)")
        self.contour = CurvilinearContour()
        self.scene = SceneWidget(self.contour)
        self.controls = ControlsPanel(self.contour, self.scene)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.scene, stretch=1)
        layout.addWidget(self.controls)
        self.setCentralWidget(central)
        self.resize(1320, 860)
