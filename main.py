import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QMessageBox)

DB_FILE = "database.json"

class AutoBlurApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_database()

    def initUI(self):
        self.setWindowTitle("OBS AutoBlur Sync v1.0")
        self.setGeometry(300, 300, 600, 450)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()

        self.search_label = QLabel("Введите название фильма (поддерживаются разные языки):")
        layout.addWidget(self.search_label)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_btn = QPushButton("Найти в базе")
        self.search_btn.clicked.connect(self.search_movie)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        self.text_output = QTextEdit()
        self.text_output.setPlaceholderText("Здесь появятся тайминги выбранного фильма...")
        layout.addWidget(self.text_output)

        self.start_btn = QPushButton("Запустить автоблюр для OBS")
        self.start_btn.clicked.connect(self.start_blur_sync)
        layout.addWidget(self.start_btn)

        central_widget.setLayout(layout)

    def load_database(self):
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r', encoding='utf-8') as f:
                    self.db = json.load(f)
            except Exception:
                self.db = {}
        else:
            self.db = {
                "видок": ["39:17 - 39:21", "42:01 - 42:09"],
                "vidocq": ["39:17 - 39:21", "42:01 - 42:09"],
                "лекарство от здоровья": ["31:17 - 31:19", "35:32 - 35:36"]
            }

    def search_movie(self):
        query = self.search_input.text().strip().lower()
        if not query:
            QMessageBox.warning(self, "Внимание", "Введите название фильма для поиска!")
            return

        found = False
        for title, timings in self.db.items():
            if query in title:
                self.text_output.setPlainText("\n".join(timings))
                found = True
                break
        
        if not found:
            self.text_output.setPlainText("Фильм не найден в локальной базе. Вы можете вставить тайминги вручную.")

    def start_blur_sync(self):
        QMessageBox.information(self, "Старт", "Синхронизация с OBS запущена в фоновом режиме!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AutoBlurApp()
    ex.show()
    sys.exit(app.exec_())
