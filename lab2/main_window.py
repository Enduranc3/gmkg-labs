from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QWidget

from controls_panel import DEFAULT_A, ControlsPanel
from folium import FoliumOfDescartes
from scene_widget import SceneWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР2. Чудові криві - Декартів лист (варіант 1)")
        self.curve = FoliumOfDescartes(DEFAULT_A)
        self.scene = SceneWidget(self.curve)
        self.controls = ControlsPanel(self.curve, self.scene)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.scene, stretch=1)
        layout.addWidget(self.controls)
        self.setCentralWidget(central)
        self.resize(1320, 860)
