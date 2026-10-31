import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # світла схема і в темній темі ОС - інакше сірі підказки на панелі не видно
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
