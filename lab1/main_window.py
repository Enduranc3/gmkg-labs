from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QWidget

from controls_panel import ControlsPanel
from detail_model import DetailModel
from scene_widget import SceneWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР1. Лінійні перетворення - варіант 1")
        self.model = DetailModel()
        self.scene = SceneWidget(self.model)
        self.controls = ControlsPanel(self.model, self.scene)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.scene, stretch=1)
        layout.addWidget(self.controls)
        self.setCentralWidget(central)
        self.resize(1320, 860)
