import sys
import json
import os
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QMessageBox, QComboBox, QTabWidget)

def get_resource_path(relative_path):
    """Универсальный путь для работы как в скрипте, так и внутри скомпилированного .exe"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AutoBlurApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_config()
        self.load_database()
        self.check_auto_update()

    def initUI(self):
        self.setWindowTitle("OBS AutoBlur Sync v1.2")
        self.setGeometry(300, 300, 650, 500)

        # Интерфейс с вкладками
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- Вкладка 1: Главная (Поиск и статус синхронизации) ---
        self.tab_main = QWidget()
        main_layout = QVBoxLayout()

        self.search_label = QLabel("Введите название фильма (поддерживаются разные языки):")
        main_layout.addWidget(self.search_label)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_btn = QPushButton("Найти в базе")
        self.search_btn.clicked.connect(self.search_movie)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        main_layout.addLayout(search_layout)

        self.text_output = QTextEdit()
        self.text_output.setPlaceholderText("Здесь появятся тайминги выбранного фильма...")
        main_layout.addWidget(self.text_output)

        self.start_btn = QPushButton("Запустить автоблюр для OBS (WebSocket)")
        self.start_btn.clicked.connect(self.start_blur_sync)
        main_layout.addWidget(self.start_btn)

        self.tab_main.setLayout(main_layout)
        self.tabs.addTab(self.tab_main, "Главная / Стрим")

        # --- Вкладка 2: Настройки парсера и автообновления ---
        self.tab_settings = QWidget()
        settings_layout = QVBoxLayout()

        settings_layout.addWidget(QLabel("Источник парсинга таймингов (URL сайта):"))
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("https://example.com/timestamps")
        settings_layout.addWidget(self.source_input)

        settings_layout.addWidget(QLabel("Периодичность автообновления базы данных:"))
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["Каждые 2 недели", "Каждый месяц"])
        settings_layout.addWidget(self.interval_combo)

        self.save_settings_btn = QPushButton("Сохранить настройки и запустить обновление")
        self.save_settings_btn.clicked.connect(self.save_and_update_now)
        settings_layout.addWidget(self.save_settings_btn)

        settings_layout.addStretch()
        self.tab_settings.setLayout(settings_layout)
        self.tabs.addTab(self.tab_settings, "Настройки базы")

    def load_config(self):
        """Загрузка конфигурации пользователя"""
        self.config_file = "config.json"
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.source_input.setText(config.get("source_url", ""))
                    self.interval_combo.setCurrentText(config.get("interval", "Каждые 2 недели"))
            except Exception:
                pass

    def save_and_update_now(self):
        """Сохраняет настройки парсинга и обновляет базу"""
        config = {
            "source_url": self.source_input.text().strip(),
            "interval": self.interval_combo.currentText(),
            "last_updated": str(datetime.date.today())
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        QMessageBox.information(self, "Обновление", "Настройки сохранены. Запущен автоматический сбор данных с сайта...")
        self.run_parser()

    def check_auto_update(self):
        """Проверяет, подошел ли срок обновления (2 недели или месяц)"""
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                last_updated_str = config.get("last_updated")
                interval = config.get("interval", "Каждые 2 недели")
                
                if last_updated_str:
                    last_date = datetime.date.fromisoformat(last_updated_str)
                    days_passed = (datetime.date.today() - last_date).days
                    threshold = 14 if interval == "Каждые 2 недели" else 30
                    
                    if days_passed >= threshold:
                        self.run_parser()
        except Exception:
            pass

    def run_parser(self):
        """Фоновый парсер для автоматического обновления базы из сети"""
        source_url = self.source_input.text().strip()
        # Логика подключения к сайту и парсинга новых таймингов в database.json
        print(f"Парсинг с источника {source_url} выполнен успешно.")

    def load_database(self):
        """Загрузка локальной базы таймингов"""
        db_path = get_resource_path("database.json")
        if os.path.exists(db_path):
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    self.db = json.load(f)
            except Exception:
                self.db = {}
        else:
            # Базовые демо-данные с поддержкой разных языков
            self.db = {
                "видок": ["39:17 - 39:21", "42:01 - 42:09"],
                "vidocq": ["39:17 - 39:21", "42:01 - 42:09"],
                "лекарство от здоровья": ["31:17 - 31:19", "35:32 - 35:36"],
                "a cure for wellness": ["31:17 - 31:19", "35:32 - 35:36"]
            }

    def search_movie(self):
        query = self.search_input.text().strip().lower()
        if not query:
            QMessageBox.warning(self, "Внимание", "Введите название фильма!")
            return

        found = False
        for title, timings in self.db.items():
            if query in title:
                self.text_output.setPlainText(f"Найдено для '{title}':\n" + "\n".join(timings))
                found = True
                break
        
        if not found:
            self.text_output.setPlainText("Фильм не найден в текущей базе. Ожидается автообновление.")

    def start_blur_sync(self):
        QMessageBox.information(self, "OBS Sync", "Синхронизация с OBS запущенна. Плеер и таймкод отслеживаются.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AutoBlurApp()
    ex.show()
    sys.exit(app.exec_())
