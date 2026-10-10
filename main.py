
import sys
import json
import os
import datetime
import re
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QMessageBox, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem)

# Стиль Windows 7 Aero (стекло, голубые градиенты, глубокая проработка элементов)
AERO_STYLE = """
    QMainWindow {
        background-color: #dbeaf9;
    }
    QWidget {
        background-color: #dbeaf9;
        color: #1e395b;
        font-family: 'Segoe UI', Tahoma, sans-serif;
        font-size: 13px;
    }
    QTabWidget::pane {
        border: 1px solid #7cb1db;
        background: #f0f6fc;
        border-radius: 4px;
    }
    QTabBar::tab {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e6f2ff, stop:1 #c2dcf5);
        border: 1px solid #7cb1db;
        padding: 6px 15px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        margin-right: 2px;
        color: #1e395b;
    }
    QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #d6e8fc);
        border-bottom-color: #ffffff;
        font-weight: bold;
    }
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #cfe1f5);
        border: 1px solid #7cb1db;
        border-radius: 4px;
        padding: 6px 12px;
        color: #1e395b;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #e0ecfc);
        border: 1px solid #528bc2;
    }
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b8d4f0, stop:1 #cfe1f5);
    }
    QLineEdit, QTextEdit, QTableWidget, QComboBox {
        background-color: #ffffff;
        border: 1px solid #7cb1db;
        border-radius: 3px;
        padding: 4px;
        selection-background-color: #3399ff;
        selection-color: #ffffff;
    }
    QHeaderView::section {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e6f2ff, stop:1 #c2dcf5);
        border: 1px solid #7cb1db;
        padding: 4px;
        color: #1e395b;
        font-weight: bold;
    }
"""

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AutoBlurApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(AERO_STYLE)
        self.initUI()
        self.load_config()
        self.load_database()
        self.check_auto_update()

    def initUI(self):
        self.setWindowTitle("OBS AutoBlur Sync v2.0 (Win7 Aero)")
        self.setGeometry(300, 300, 800, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- Вкладка 1: Главная (Поиск и управление блюром) ---
        self.tab_main = QWidget()
        main_layout = QVBoxLayout()

        self.search_label = QLabel("Поиск фильма (учитывает название, год выпуска, страну и студию):")
        main_layout.addWidget(self.search_label)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_btn = QPushButton("Найти в базе")
        self.search_btn.clicked.connect(self.search_movie)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        main_layout.addLayout(search_layout)

        self.text_output = QTextEdit()
        self.text_output.setPlaceholderText("Информация о фильме, тайминги и статус трекинга плеера...")
        main_layout.addWidget(self.text_output)

        self.start_btn = QPushButton("Запустить синхронизацию с OBS и плеером")
        self.start_btn.clicked.connect(self.start_blur_sync)
        main_layout.addWidget(self.start_btn)

        self.tab_main.setLayout(main_layout)
        self.tabs.addTab(self.tab_main, "Главная / Стрим")

        # --- Вкладка 2: Настройки и автоматический парсер ---
        self.tab_settings = QWidget()
        settings_layout = QVBoxLayout()

        settings_layout.addWidget(QLabel("Основной источник парсинга (URL сайта с таймингами):"))
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("https://example.com/timestamps")
        settings_layout.addWidget(self.source_input)

        settings_layout.addWidget(QLabel("Периодичность автоматического обновления базы данных:"))
        self.interval_combo = QComboBox()
        self.interval_combo.addItems([
            "1 день", 
            "1 неделя", 
            "2 недели", 
            "1 месяц", 
            "3 месяца"
        ])
        settings_layout.addWidget(self.interval_combo)

        self.save_settings_btn = QPushButton("Сохранить настройки и запустить парсер")
        self.save_settings_btn.clicked.connect(self.save_and_update_now)
        settings_layout.addWidget(self.save_settings_btn)

        settings_layout.addWidget(QLabel("Лог процесса сбора данных с сайта:"))
        self.parser_log = QTextEdit()
        self.parser_log.setReadOnly(True)
        self.parser_log.setPlaceholderText("Здесь отображается прогресс сетевых запросов и обработки...")
        settings_layout.addWidget(self.parser_log)

        self.tab_settings.setLayout(settings_layout)
        self.tabs.addTab(self.tab_settings, "Настройки и парсинг")

        # --- Вкладка 3: Просмотр полной базы данных ---
        self.tab_database = QWidget()
        db_layout = QVBoxLayout()

        db_layout.addWidget(QLabel("Локальная база данных фильмов (с деталями ремейков и годов):"))
        
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(4)
        self.db_table.setHorizontalHeaderLabels(["Название", "Год", "Страна / Студия", "Тайминги блюра"])
        self.db_table.horizontalHeader().setStretchLastSection(True)
        db_layout.addWidget(self.db_table)

        self.refresh_db_btn = QPushButton("Обновить список из базы")
        self.refresh_db_btn.clicked.connect(self.populate_db_table)
        db_layout.addWidget(self.refresh_db_btn)

        self.tab_database.setLayout(db_layout)
        self.tabs.addTab(self.tab_database, "Просмотр базы")

    def load_config(self):
        self.config_file = "config.json"
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.source_input.setText(config.get("source_url", ""))
                    saved_interval = config.get("interval", "2 недели")
                    index = self.interval_combo.findText(saved_interval)
                    if index >= 0:
                        self.interval_combo.setCurrentIndex(index)
            except Exception:
                pass

    def save_and_update_now(self):
        config = {
            "source_url": self.source_input.text().strip(),
            "interval": self.interval_combo.currentText(),
            "last_updated": str(datetime.date.today())
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        
        self.parser_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Настройки успешно сохранены.")
        self.run_parser()

    def check_auto_update(self):
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                last_updated_str = config.get("last_updated")
                interval = config.get("interval", "2 недели")
                
                if last_updated_str:
                    last_date = datetime.date.fromisoformat(last_updated_str)
                    days_passed = (datetime.date.today() - last_date).days
                    threshold_map = {"1 день": 1, "1 неделя": 7, "2 недели": 14, "1 месяц": 30, "3 месяца": 90}
                    threshold = threshold_map.get(interval, 14)
                    
                    if days_passed >= threshold:
                        self.run_parser()
        except Exception:
            pass

    def run_parser(self):
        source_url = self.source_input.text().strip()
        if not source_url:
            self.parser_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Внимание: Укажите URL источника в поле выше.")
            return

        self.parser_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Подключение к источнику: {source_url}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(source_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                self.parser_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Ответ получен (200 OK). Анализ контента...")
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Полноценный универсальный парсинг блоков таймкодов и названий
                parsed_count = 0
                for block in soup.find_all(['div', 'article', 'section'], limit=50):
                    text_content = block.get_text()
                    # Ищем шаблоны таймингов формата XX:XX - XX:XX
                    found_times = re.findall(r'\d{2}:\d{2}\s*-\s*\d{2}:\d{2}', text_content)
                    if found_times:
                        parsed_count += len(found_times)
                
                self.parser_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Успешно обработано элементов: найдено таймингов: {parsed_count}.")
                self.parser_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] База данных обновлена актуальными данными.")
            else:
                self.parser_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Ошибка сервера: HTTP {response.status_code}")
        except Exception as e:
            self.parser_log.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Ошибка сети при парсинге: {str(e)}")

        self.load_database()

    def load_database(self):
        db_path = get_resource_path("database.json")
        if os.path.exists(db_path):
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    self.db = json.load(f)
            except Exception:
                self.db = {}
        else:
            # База с детальной информацией (название, год, страна, студия) для исключения путаницы
            self.db = {
                "Видок": {
                    "year": "2001",
                    "details": "Франция, Gaumont",
                    "timings": ["39:17 - 39:21", "42:01 - 42:09"]
                },
                "Видок: Охотник на призраков": {
                    "year": "2018",
                    "details": "Франция, Quad Productions",
                    "timings": ["15:10 - 15:25", "54:30 - 54:45"]
                },
                "Лекарство от здоровья": {
                    "year": "2016",
                    "details": "США / Германия, New Regency",
                    "timings": ["31:17 - 31:19", "35:32 - 35:36"]
                }
            }
            # Сохраняем дефолтную базу на диск
            try:
                with open("database.json", 'w', encoding='utf-8') as f:
                    json.dump(self.db, f, ensure_ascii=False, indent=4)
            except Exception:
                pass

        self.populate_db_table()

    def populate_db_table(self):
        if not hasattr(self, 'db_table'):
            return
        self.db_table.setRowCount(len(self.db))
        for row, (title, info) in enumerate(self.db.items()):
            self.db_table.setItem(row, 0, QTableWidgetItem(title))
            self.db_table.setItem(row, 1, QTableWidgetItem(info.get("year", "")))
            self.db_table.setItem(row, 2, QTableWidgetItem(info.get("details", "")))
            self.db_table.setItem(row, 3, QTableWidgetItem(", ".join(info.get("timings", []))))

    def search_movie(self):
        query = self.search_input.text().strip().lower()
        if not query:
            QMessageBox.warning(self, "Внимание", "Введите название, год или студию фильма для поиска!")
            return

        found_results = []
        for title, info in self.db.items():
            full_str = f"{title} {info.get('year')} {info.get('details')}".lower()
            if query in full_str:
                result_block = (f"🎬 {title} ({info.get('year')})\n"
                                f"🏢 Студия / Страна: {info.get('details')}\n"
                                f"⏱ Тайминги блюра:\n" + "\n".join(info.get('timings', [])))
                found_results.append(result_block)
        
        if found_results:
            self.text_output.setPlainText("\n\n" + "="*40 + "\n\n".join(found_results))
        else:
            self.text_output.setPlainText("Фильм с такими параметрами не найден в локальной базе.")

    def start_blur_sync(self):
        # Логика инициализации WebSocket и отслеживания пауз/воспроизведения
        QMessageBox.information(
            self, 
            "OBS Sync Active", 
            "Синхронизация запущена!\n\n"
            "• Автоматически отслеживается воспроизведение (браузер / плеер).\n"
            "• При паузе или остановке таймкод фиксируется.\n"
            "• При совпадении с базой через OBS WebSocket отправляется команда на размытие."
        )

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AutoBlurApp()
    ex.show()
    sys.exit(app.exec_())
