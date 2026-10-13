import os
import sys
import threading
import subprocess
from PyQt5 import QtCore, QtGui, QtWidgets

from core.algorithms import AVAILABLE_ALGORITHMS
from core.processor import ResourcePackProcessor, ProcessingStats

DARK_STYLESHEET = """
QWidget {
    background-color: #181825;
    color: #cdd6f4;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}

QGroupBox {
    background-color: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #89b4fa;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: #1e1e2e;
}

QLineEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
}

QLineEdit:focus {
    border: 1px solid #89b4fa;
}

QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    color: #cdd6f4;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}

QPushButton:pressed {
    background-color: #585b70;
}

QPushButton#PrimaryButton {
    background-color: #89b4fa;
    color: #11111b;
    border: none;
    font-weight: bold;
    font-size: 14px;
    padding: 10px 20px;
}

QPushButton#PrimaryButton:hover {
    background-color: #b4befe;
}

QPushButton#PrimaryButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}

QPushButton#DangerButton {
    background-color: #f38ba8;
    color: #11111b;
    border: none;
    font-weight: bold;
}

QPushButton#DangerButton:hover {
    background-color: #eba0ac;
}

QComboBox, QSpinBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #cdd6f4;
}

QComboBox:hover, QSpinBox:hover {
    border-color: #89b4fa;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    selection-background-color: #89b4fa;
    selection-color: #11111b;
}

QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    height: 22px;
}

QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 6px;
}

QTextEdit {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 6px;
    color: #a6adc8;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    padding: 8px;
}

QLabel#DropZone {
    border: 2px dashed #45475a;
    border-radius: 10px;
    padding: 16px;
    background-color: #1e1e2e;
    color: #a6adc8;
    font-size: 13px;
    text-align: center;
}

QLabel#DropZone:hover {
    border-color: #89b4fa;
    color: #cdd6f4;
}
"""

class UpscaleWorker(QtCore.QThread):
    progress_signal = QtCore.pyqtSignal(int, int, str, str)
    finished_signal = QtCore.pyqtSignal(object)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, input_path: str, output_path: str, algorithm: str, workers: int):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.algorithm = algorithm
        self.workers = workers
        self.cancel_event = threading.Event()

    def run(self):
        def cb(current, total, filename, status):
            self.progress_signal.emit(current, total, filename, status)

        try:
            processor = ResourcePackProcessor(
                algorithm=self.algorithm,
                num_workers=self.workers,
                progress_callback=cb,
                cancel_event=self.cancel_event
            )
            stats = processor.process(self.input_path, self.output_path)
            self.finished_signal.emit(stats)
        except InterruptedError:
            self.error_signal.emit("Vorgang wurde vom Benutzer abgebrochen.")
        except Exception as e:
            self.error_signal.emit(str(e))

    def cancel(self):
        self.cancel_event.set()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Texturepack Upscaler (32x / 48x / 64x)")
        self.resize(760, 680)
        self.setMinimumSize(680, 580)
        self.setAcceptDrops(True)

        self.worker: UpscaleWorker = None
        self.last_output_dir = ""

        self.init_ui()

    def init_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Title
        header_layout = QtWidgets.QHBoxLayout()
        title_box = QtWidgets.QVBoxLayout()
        title = QtWidgets.QLabel("Minecraft Texturepack Upscaler")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89b4fa;")
        subtitle = QtWidgets.QLabel("Intelligentes, verlustfreies Hochskalieren von Texturen, CTM-Glas & Animationen")
        subtitle.setStyleSheet("color: #a6adc8; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Drag and drop hint label
        self.drop_label = QtWidgets.QLabel("Ziehe ein Ressourcenpaket (.zip oder Ordner) hier hinein")
        self.drop_label.setObjectName("DropZone")
        self.drop_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.drop_label)

        # Path Selection Group
        path_group = QtWidgets.QGroupBox("Dateipfade")
        path_layout = QtWidgets.QGridLayout(path_group)
        path_layout.setSpacing(10)

        # Input
        path_layout.addWidget(QtWidgets.QLabel("Quell-Paket:"), 0, 0)
        self.input_edit = QtWidgets.QLineEdit()
        self.input_edit.setPlaceholderText("Pfad zum Original-Ressourcenpaket (.zip oder Ordner)...")
        self.input_edit.textChanged.connect(self.on_input_changed)
        path_layout.addWidget(self.input_edit, 0, 1)

        btn_in_folder = QtWidgets.QPushButton("Ordner...")
        btn_in_folder.clicked.connect(self.browse_input_folder)
        path_layout.addWidget(btn_in_folder, 0, 2)

        btn_in_zip = QtWidgets.QPushButton("ZIP Datei...")
        btn_in_zip.clicked.connect(self.browse_input_zip)
        path_layout.addWidget(btn_in_zip, 0, 3)

        # Output
        path_layout.addWidget(QtWidgets.QLabel("Ziel-Paket:"), 1, 0)
        self.output_edit = QtWidgets.QLineEdit()
        self.output_edit.setPlaceholderText("Pfad zum Zielpaket (Ordner oder .zip)...")
        path_layout.addWidget(self.output_edit, 1, 1)

        btn_out_folder = QtWidgets.QPushButton("Zielordner...")
        btn_out_folder.clicked.connect(self.browse_output_folder)
        path_layout.addWidget(btn_out_folder, 1, 2)

        btn_out_zip = QtWidgets.QPushButton("Ziel-ZIP...")
        btn_out_zip.clicked.connect(self.browse_output_zip)
        path_layout.addWidget(btn_out_zip, 1, 3)

        main_layout.addWidget(path_group)

        # Settings Group
        settings_group = QtWidgets.QGroupBox("Einstellungen & Skalierung")
        settings_layout = QtWidgets.QGridLayout(settings_group)
        settings_layout.setSpacing(10)

        settings_layout.addWidget(QtWidgets.QLabel("Algorithmus:"), 0, 0)
        self.algo_combo = QtWidgets.QComboBox()
        for key, data in AVAILABLE_ALGORITHMS.items():
            self.algo_combo.addItem(f"{data['name']}", key)
        self.algo_combo.currentIndexChanged.connect(self.on_algo_changed)
        settings_layout.addWidget(self.algo_combo, 0, 1)

        self.algo_desc = QtWidgets.QLabel(AVAILABLE_ALGORITHMS["scale2x"]["description"])
        self.algo_desc.setStyleSheet("color: #a6adc8; font-size: 11px;")
        self.algo_desc.setWordWrap(True)
        settings_layout.addWidget(self.algo_desc, 1, 1)

        settings_layout.addWidget(QtWidgets.QLabel("CPU-Threads:"), 2, 0)
        thread_box = QtWidgets.QHBoxLayout()
        self.spin_threads = QtWidgets.QSpinBox()
        cpu_max = min(64, (os.cpu_count() or 4) * 2)
        self.spin_threads.setRange(1, cpu_max)
        self.spin_threads.setValue(min(28, (os.cpu_count() or 4) + 4))
        thread_box.addWidget(self.spin_threads)
        thread_label = QtWidgets.QLabel(f"(Erkannt: {os.cpu_count()} logische Kerne)")
        thread_label.setStyleSheet("color: #a6adc8; font-size: 11px;")
        thread_box.addWidget(thread_label)
        thread_box.addStretch()
        settings_layout.addLayout(thread_box, 2, 1)

        main_layout.addWidget(settings_group)

        # Progress Section
        self.status_label = QtWidgets.QLabel("Bereit zum Starten.")
        self.status_label.setStyleSheet("color: #cdd6f4; font-weight: 500;")
        main_layout.addWidget(self.status_label)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Log Output Box
        self.log_edit = QtWidgets.QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(150)
        self.log_edit.setPlaceholderText("Verlauf und Logausgabe erscheinen hier...")
        main_layout.addWidget(self.log_edit)

        # Action Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_open_out = QtWidgets.QPushButton("Zielordner öffnen")
        self.btn_open_out.setEnabled(False)
        self.btn_open_out.clicked.connect(self.open_output_dir)
        btn_layout.addWidget(self.btn_open_out)

        btn_layout.addStretch()

        self.btn_cancel = QtWidgets.QPushButton("Abbrechen")
        self.btn_cancel.setObjectName("DangerButton")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_processing)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_start = QtWidgets.QPushButton("Upscaling starten")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.clicked.connect(self.start_processing)
        btn_layout.addWidget(self.btn_start)

        main_layout.addLayout(btn_layout)

    # Drag & Drop Handlers
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_label.setStyleSheet("border-color: #89b4fa; color: #89b4fa;")

    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent):
        self.drop_label.setStyleSheet("")

    def dropEvent(self, event: QtGui.QDropEvent):
        self.drop_label.setStyleSheet("")
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.exists(path):
                self.input_edit.setText(path)

    def browse_input_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Quell-Ressourcenpaket auswählen")
        if folder:
            self.input_edit.setText(folder)

    def browse_input_zip(self):
        zip_file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Quell-Ressourcenpaket (ZIP) auswählen", "", "ZIP-Archive (*.zip)"
        )
        if zip_file:
            self.input_edit.setText(zip_file)

    def browse_output_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Zielordner auswählen")
        if folder:
            self.output_edit.setText(folder)

    def browse_output_zip(self):
        zip_file, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Zielpaket als ZIP speichern", "", "ZIP-Archive (*.zip)"
        )
        if zip_file:
            self.output_edit.setText(zip_file)

    def on_algo_changed(self):
        algo_key = self.algo_combo.currentData()
        if algo_key in AVAILABLE_ALGORITHMS:
            self.algo_desc.setText(AVAILABLE_ALGORITHMS[algo_key]["description"])
            self.update_auto_output()

    def on_input_changed(self):
        self.update_auto_output()

    def update_auto_output(self):
        inp = self.input_edit.text().strip()
        if not inp:
            return
        algo_key = self.algo_combo.currentData()
        factor = AVAILABLE_ALGORITHMS.get(algo_key, {}).get("factor", 2)
        target_res = factor * 16

        base, ext = os.path.splitext(inp)
        tag = f"_{target_res}x"
        if ext.lower() == ".zip":
            self.output_edit.setText(f"{base}{tag}.zip")
        else:
            self.output_edit.setText(f"{inp}{tag}")

    def log(self, text: str):
        self.log_edit.append(text)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start_processing(self):
        inp = self.input_edit.text().strip()
        out = self.output_edit.text().strip()

        if not inp or not os.path.exists(inp):
            QtWidgets.QMessageBox.warning(self, "Ungültiger Pfad", "Bitte wähle ein existierendes Quellpaket aus.")
            return

        if not out:
            QtWidgets.QMessageBox.warning(self, "Ungültiger Pfad", "Bitte gib einen gültigen Zielpfad an.")
            return

        algo_key = self.algo_combo.currentData()
        workers = self.spin_threads.value()

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_open_out.setEnabled(False)
        self.input_edit.setEnabled(False)
        self.output_edit.setEnabled(False)
        self.algo_combo.setEnabled(False)
        self.spin_threads.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_edit.clear()

        self.log(f"Starte Upscaling mit Algorithmus '{AVAILABLE_ALGORITHMS[algo_key]['name']}'...")
        self.log(f"Quelle: {inp}")
        self.log(f"Ziel:   {out}")
        self.log(f"Threads: {workers}")
        self.status_label.setText("Vorbereitung...")

        self.worker = UpscaleWorker(inp, out, algo_key, workers)
        self.worker.progress_signal.connect(self.on_worker_progress)
        self.worker.finished_signal.connect(self.on_worker_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.start()

    def on_worker_progress(self, current: int, total: int, filename: str, status: str):
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.status_label.setText(f"{status} - {filename}")

    def on_worker_finished(self, stats: ProcessingStats):
        self.progress_bar.setValue(100)
        self.status_label.setText("Erfolgreich abgeschlossen!")
        self.log("=" * 50)
        self.log("Vorgang erfolgreich beendet!")
        self.log(f"Dauer:               {stats.elapsed_seconds:.2f} Sekunden")
        self.log(f"Texturen skaliert:   {stats.upscaled_images}")
        self.log(f"Colormaps geschützt: {stats.colormaps_preserved}")
        self.log(f"Dateien kopiert:     {stats.other_files_copied}")
        if stats.errors > 0:
            self.log(f"Warnungen/Fehler:    {stats.errors}")
        self.log(f"Ausgabe:             {stats.output_path}")
        self.log("=" * 50)

        self.last_output_dir = stats.output_path if os.path.isdir(stats.output_path) else os.path.dirname(stats.output_path)
        self.btn_open_out.setEnabled(True)
        self.reset_ui_state()

        QtWidgets.QMessageBox.information(
            self,
            "Upscaling abgeschlossen",
            f"Das Ressourcenpaket wurde erfolgreich hochskaliert!\n\n"
            f"Texturen: {stats.upscaled_images}\n"
            f"Dauer: {stats.elapsed_seconds:.2f}s\n\n"
            f"Gespeichert unter:\n{stats.output_path}"
        )

    def on_worker_error(self, err_msg: str):
        self.status_label.setText("Abgebrochen oder Fehler.")
        self.log(f"FEHLER: {err_msg}")
        self.reset_ui_state()
        QtWidgets.QMessageBox.critical(self, "Fehler", f"Es ist ein Fehler aufgetreten:\n{err_msg}")

    def cancel_processing(self):
        if self.worker and self.worker.isRunning():
            self.status_label.setText("Breche ab...")
            self.worker.cancel()

    def reset_ui_state(self):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.input_edit.setEnabled(True)
        self.output_edit.setEnabled(True)
        self.algo_combo.setEnabled(True)
        self.spin_threads.setEnabled(True)

    def open_output_dir(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            subprocess.run(["explorer", self.last_output_dir])

def launch_gui():
    # Enable High DPI support
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
