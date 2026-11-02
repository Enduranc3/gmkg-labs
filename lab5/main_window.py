from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QWidget

from controls_panel import ControlsPanel
from polyhedron import FacetedBody
from scene_widget import SceneWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР5. Проекціювання: диметрія на площину y = 0 (варіант 1)")
        self.body = FacetedBody()
        self.scene = SceneWidget(self.body)
        self.controls = ControlsPanel(self.body, self.scene)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.scene, stretch=1)
        layout.addWidget(self.controls)
        self.setCentralWidget(central)
        self.resize(1320, 860)
