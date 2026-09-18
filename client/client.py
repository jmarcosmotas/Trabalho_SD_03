import sys
import os
import mimetypes
import tempfile
import traceback
from pathlib import Path

import requests
from PySide6.QtCore import Qt, QUrl, QThread, Signal, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFileDialog, QComboBox, QDoubleSpinBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QGroupBox,
    QAbstractItemView, QSizePolicy, QStatusBar
)

BASE_URL = "http://localhost:8080/audios"

PROCESSING_TYPES = [
    ("normalizacao", "Normalização de volume"),
    ("mono", "Conversão para mono"),
    ("velocidade", "Alterar velocidade"),
    ("bitrate", "Reduzir taxa de bits"),
    ("converter", "Converter formato (mp3 <-> wav)"),
]

class Worker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception:
            self.error.emit(traceback.format_exc())


def run_in_thread(parent, fn, on_success, on_error, *args, **kwargs):
    """Cria e inicia uma thread para rodar fn(*args, **kwargs) sem travar a GUI."""
    thread = QThread(parent)
    worker = Worker(fn, *args, **kwargs)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(on_success)
    worker.error.connect(on_error)
    worker.finished.connect(thread.quit)
    worker.error.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    worker.error.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    parent._threads = getattr(parent, "_threads", [])
    parent._threads.append((thread, worker))

    def _cleanup(t=thread, w=worker):
        try:
            parent._threads.remove((t, w))
        except ValueError:
            pass

    thread.finished.connect(_cleanup)
    thread.start()
    return thread

def _raise_with_server_detail(resp):
    """Levanta o erro HTTP incluindo o campo 'detail' que o FastAPI devolveu,
    em vez de só o código de status genérico."""
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        detail = None
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text
        raise requests.exceptions.HTTPError(
            f"{exc}\n\nDetalhe retornado pelo servidor: {detail}"
        ) from None


def api_upload(file_path, processing_type, speed, bitrate):

    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        files = {"audio": (os.path.basename(file_path), f, content_type)}
        data = {"processing_type": processing_type}
        if speed is not None:
            data["speed"] = speed
        if bitrate is not None:
            data["bitrate"] = bitrate
        resp = requests.post(f"{BASE_URL}/receber-audio", files=files, data=data, timeout=120)
    _raise_with_server_detail(resp)
    return resp.json()


def api_list_all():
    resp = requests.get(f"{BASE_URL}/listar-todos-audios", timeout=30)
    _raise_with_server_detail(resp)
    return resp.json()


def api_get_metadata(audio_id):
    resp = requests.get(f"{BASE_URL}/busca-audio/{audio_id}", timeout=30)
    _raise_with_server_detail(resp)
    return resp.json()


def api_download_audio(audio_id, tipo, dest_path):
    resp = requests.get(f"{BASE_URL}/carregar-audio/{audio_id}/{tipo}", timeout=120)
    _raise_with_server_detail(resp)
    with open(dest_path, "wb") as f:
        f.write(resp.content)
    return dest_path


def api_download_image(audio_id, tipo):
    resp = requests.get(f"{BASE_URL}/carregar-imagem/{audio_id}/{tipo}", timeout=30)
    _raise_with_server_detail(resp)
    return resp.content


def api_delete(audio_id):
    resp = requests.delete(f"{BASE_URL}/deletar-audio/{audio_id}", timeout=30)
    _raise_with_server_detail(resp)
    return resp.json()


# ---------------------------------------------------------------------------
# Janela principal
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cliente de Processamento de Áudio")
        self.resize(980, 640)

        self.selected_file_path = None
        self.current_audio_id = None
        self.current_row_original_ext = ""

        # Player de áudio
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

        self._build_ui()
        self.setStatusBar(QStatusBar())
        self.refresh_history()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        main_layout.addWidget(self._build_left_panel(), 1)
        main_layout.addWidget(self._build_right_panel(), 2)

    def _build_left_panel(self):
        box = QGroupBox("Enviar novo áudio")
        layout = QVBoxLayout(box)

        self.btn_select = QPushButton("Selecionar arquivo de áudio...")
        self.btn_select.clicked.connect(self.on_select_file)
        layout.addWidget(self.btn_select)

        self.lbl_file_name = QLabel("Nenhum arquivo selecionado")
        self.lbl_file_name.setWordWrap(True)
        layout.addWidget(self.lbl_file_name)

        info_grid = QGridLayout()
        info_grid.addWidget(QLabel("Formato:"), 0, 0)
        self.lbl_info_format = QLabel("-")
        info_grid.addWidget(self.lbl_info_format, 0, 1)

        info_grid.addWidget(QLabel("Tamanho:"), 1, 0)
        self.lbl_info_size = QLabel("-")
        info_grid.addWidget(self.lbl_info_size, 1, 1)

        info_grid.addWidget(QLabel("Duração:"), 2, 0)
        self.lbl_info_duration = QLabel("-")
        info_grid.addWidget(self.lbl_info_duration, 2, 1)
        layout.addLayout(info_grid)

        layout.addWidget(QLabel("Tipo de processamento:"))
        self.combo_processing = QComboBox()
        for key, label in PROCESSING_TYPES:
            self.combo_processing.addItem(label, key)
        self.combo_processing.currentIndexChanged.connect(self.on_processing_type_changed)
        layout.addWidget(self.combo_processing)

        self.spin_speed = QDoubleSpinBox()
        self.spin_speed.setRange(0.5, 2.0)
        self.spin_speed.setSingleStep(0.05)
        self.spin_speed.setValue(1.0)
        self.spin_speed.setPrefix("Velocidade: ")
        self.spin_speed.setToolTip("O servidor aceita apenas valores entre 0.5 e 2.0")
        layout.addWidget(self.spin_speed)

        self.spin_bitrate = QSpinBox()
        self.spin_bitrate.setRange(32, 192)
        self.spin_bitrate.setSingleStep(16)
        self.spin_bitrate.setValue(128)
        self.spin_bitrate.setSuffix(" kbps")
        self.spin_bitrate.setToolTip("O servidor aceita apenas valores entre 32 e 192 kbps")
        layout.addWidget(self.spin_bitrate)

        self.btn_upload = QPushButton("Enviar para o servidor")
        self.btn_upload.clicked.connect(self.on_upload)
        self.btn_upload.setEnabled(False)
        layout.addWidget(self.btn_upload)

        layout.addStretch()
        self.on_processing_type_changed()
        return box

    def _build_right_panel(self):
        container = QWidget()
        layout = QVBoxLayout(container)

        # ---- Histórico ----
        hist_box = QGroupBox("Histórico de áudios")
        hist_layout = QVBoxLayout(hist_box)

        top_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Atualizar lista")
        self.btn_refresh.clicked.connect(self.refresh_history)
        top_row.addWidget(self.btn_refresh)
        top_row.addStretch()
        self.btn_delete = QPushButton("Excluir selecionado")
        self.btn_delete.clicked.connect(self.on_delete_selected)
        self.btn_delete.setEnabled(False)
        top_row.addWidget(self.btn_delete)
        hist_layout.addLayout(top_row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Arquivo original", "Arquivo processado"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        hist_layout.addWidget(self.table)

        layout.addWidget(hist_box, 2)

        # ---- Detalhes / reprodução ----
        detail_box = QGroupBox("Detalhes e reprodução")
        detail_layout = QVBoxLayout(detail_box)

        self.lbl_detail = QLabel("Selecione um item do histórico para ver detalhes.")
        self.lbl_detail.setWordWrap(True)
        detail_layout.addWidget(self.lbl_detail)

        players_row = QHBoxLayout()

        original_col = QVBoxLayout()
        self.btn_play_original = QPushButton("▶ Reproduzir original")
        self.btn_play_original.clicked.connect(lambda: self.on_play("original"))
        self.btn_play_original.setEnabled(False)
        original_col.addWidget(self.btn_play_original)
        self.img_original = QLabel("Sem forma de onda")
        self.img_original.setAlignment(Qt.AlignCenter)
        self.img_original.setMinimumHeight(120)
        self.img_original.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        original_col.addWidget(self.img_original)
        players_row.addLayout(original_col)

        processed_col = QVBoxLayout()
        self.btn_play_processed = QPushButton("▶ Reproduzir processado")
        self.btn_play_processed.clicked.connect(lambda: self.on_play("processed"))
        self.btn_play_processed.setEnabled(False)
        processed_col.addWidget(self.btn_play_processed)
        self.img_processed = QLabel("Sem forma de onda")
        self.img_processed.setAlignment(Qt.AlignCenter)
        self.img_processed.setMinimumHeight(120)
        self.img_processed.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        processed_col.addWidget(self.img_processed)
        players_row.addLayout(processed_col)

        detail_layout.addLayout(players_row)

        self.btn_stop = QPushButton("⏹ Parar reprodução")
        self.btn_stop.clicked.connect(self.player.stop)
        detail_layout.addWidget(self.btn_stop)

        layout.addWidget(detail_box, 1)
        return container

    # ------------------------------------------------------------------
    # Seleção / envio de arquivo
    # ------------------------------------------------------------------
    def on_processing_type_changed(self):
        key = self.combo_processing.currentData()
        self.spin_speed.setVisible(key == "velocidade")
        self.spin_bitrate.setVisible(key == "bitrate")

    def on_select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar áudio", "",
            "Áudios (*.mp3 *.wav *.flac *.ogg *.m4a);;Todos os arquivos (*)"
        )
        if not path:
            return
        self.selected_file_path = path
        self.lbl_file_name.setText(Path(path).name)

        size_bytes = os.path.getsize(path)
        self.lbl_info_size.setText(self._format_size(size_bytes))
        self.lbl_info_format.setText(Path(path).suffix.lstrip(".").upper() or "-")

        # duração aproximada via QMediaPlayer local (probe rápido)
        self.lbl_info_duration.setText("carregando...")
        probe_player = QMediaPlayer()
        probe_output = QAudioOutput()
        probe_player.setAudioOutput(probe_output)
        probe_output.setVolume(0)

        def on_duration_changed(duration_ms, p=probe_player, o=probe_output):
            if duration_ms > 0:
                self.lbl_info_duration.setText(self._format_duration(duration_ms))
                p.stop()
                p.deleteLater()
                o.deleteLater()

        probe_player.durationChanged.connect(on_duration_changed)
        probe_player.setSource(QUrl.fromLocalFile(path))

        self.btn_upload.setEnabled(True)

    def on_upload(self):
        if not self.selected_file_path:
            return
        processing_type = self.combo_processing.currentData()
        speed = self.spin_speed.value() if processing_type == "velocidade" else None
        bitrate = self.spin_bitrate.value() if processing_type == "bitrate" else None

        self.btn_upload.setEnabled(False)
        self.statusBar().showMessage("Enviando áudio para o servidor...")

        run_in_thread(
            self, api_upload,
            self.on_upload_success, self.on_upload_error,
            self.selected_file_path, processing_type, speed, bitrate
        )

    def on_upload_success(self, result):
        self.btn_upload.setEnabled(True)
        self.statusBar().showMessage(
            f"Áudio enviado com sucesso (id={result.get('id')}, "
            f"processamento={result.get('processing_type')})", 8000
        )
        self.refresh_history()

    def on_upload_error(self, error_text):
        self.btn_upload.setEnabled(True)
        self.statusBar().showMessage("Falha ao enviar áudio.", 8000)
        QMessageBox.critical(self, "Erro no envio", error_text)

    # ------------------------------------------------------------------
    # Histórico
    # ------------------------------------------------------------------
    def refresh_history(self):
        self.statusBar().showMessage("Carregando histórico...")
        run_in_thread(self, api_list_all, self.on_history_loaded, self.on_history_error)

    def on_history_loaded(self, audios):
        self.statusBar().showMessage(f"{len(audios)} áudio(s) encontrado(s).", 5000)
        self.table.setRowCount(0)
        for row_idx, audio in enumerate(audios):
            self.table.insertRow(row_idx)
            audio_id = str(audio.get("id", ""))
            original = str(audio.get("path_file_original", "") or "")
            processed = str(audio.get("path_file_processed", "") or "")

            id_item = QTableWidgetItem(audio_id)
            id_item.setData(Qt.UserRole, audio_id)
            self.table.setItem(row_idx, 0, id_item)
            self.table.setItem(row_idx, 1, QTableWidgetItem(original))
            self.table.setItem(row_idx, 2, QTableWidgetItem(processed))

    def on_history_error(self, error_text):
        self.statusBar().showMessage("Falha ao carregar histórico.", 8000)
        QMessageBox.critical(self, "Erro ao listar áudios", error_text)

    def on_row_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.btn_delete.setEnabled(False)
            self.btn_play_original.setEnabled(False)
            self.btn_play_processed.setEnabled(False)
            return

        row = rows[0].row()
        audio_id = self.table.item(row, 0).data(Qt.UserRole)
        self.current_audio_id = audio_id
        self.btn_delete.setEnabled(True)
        self.lbl_detail.setText("Carregando detalhes...")

        run_in_thread(self, api_get_metadata, self.on_metadata_loaded, self.on_metadata_error, audio_id)
        run_in_thread(self, api_download_image, self.on_image_loaded, self.on_image_error, audio_id, "original")
        run_in_thread(self, api_download_image, self.on_processed_image_loaded, self.on_image_error, audio_id, "processed")

    def on_metadata_loaded(self, meta):
        self.current_row_original_ext = meta.get("extensao", "") or ""
        text = (
            f"Nome: {meta.get('nome_original', '-')}{meta.get('extensao', '')}\n"
            f"Formato: {meta.get('mime_type', '-')}    "
            f"Tamanho: {self._format_size(meta.get('size_bytes', 0) or 0)}\n"
            f"Duração: {meta.get('duration_sec', '-')} s    "
            f"Sample rate: {meta.get('sample_rate', '-')} Hz    "
            f"Canais: {meta.get('channels', '-')}\n"
            f"Bitrate: {meta.get('bitrate', '-')}    "
            f"Processamento: {meta.get('processing_type', '-')}\n"
            f"Enviado em: {meta.get('data_time', '-')}"
        )
        self.lbl_detail.setText(text)
        self.btn_play_original.setEnabled(True)
        self.btn_play_processed.setEnabled(True)

    def on_metadata_error(self, error_text):
        self.lbl_detail.setText("Não foi possível carregar os detalhes deste áudio.")
        self.btn_play_original.setEnabled(False)
        self.btn_play_processed.setEnabled(False)

    def on_image_loaded(self, image_bytes):
        self._set_pixmap(self.img_original, image_bytes)

    def on_processed_image_loaded(self, image_bytes):
        self._set_pixmap(self.img_processed, image_bytes)

    def on_image_error(self, error_text):
        pass  # nem todo áudio processado terá waveform disponível de imediato

    def _set_pixmap(self, label, image_bytes):
        pixmap = QPixmap()
        if pixmap.loadFromData(image_bytes):
            label.setPixmap(pixmap.scaledToWidth(300, Qt.SmoothTransformation))
        else:
            label.setText("Forma de onda indisponível")

    # ------------------------------------------------------------------
    # Reprodução
    # ------------------------------------------------------------------
    def on_play(self, tipo):
        if not self.current_audio_id:
            return
        self.statusBar().showMessage(f"Baixando áudio ({tipo}) para reprodução...")
        ext = self.current_row_original_ext or ".audio"
        dest = os.path.join(tempfile.gettempdir(), f"{self.current_audio_id}_{tipo}{ext}")
        run_in_thread(
            self, api_download_audio,
            self.on_play_download_success, self.on_play_download_error,
            self.current_audio_id, tipo, dest
        )

    def on_play_download_success(self, dest_path):
        self.statusBar().showMessage("Reproduzindo...", 4000)
        self.player.setSource(QUrl.fromLocalFile(dest_path))
        self.player.play()

    def on_play_download_error(self, error_text):
        self.statusBar().showMessage("Falha ao baixar áudio para reprodução.", 8000)
        QMessageBox.critical(self, "Erro na reprodução", error_text)

    # ------------------------------------------------------------------
    # Exclusão
    # ------------------------------------------------------------------
    def on_delete_selected(self):
        if not self.current_audio_id:
            return
        confirm = QMessageBox.question(
            self, "Confirmar exclusão",
            "Deseja mover este áudio para a lixeira do servidor?"
        )
        if confirm != QMessageBox.Yes:
            return
        run_in_thread(self, api_delete, self.on_delete_success, self.on_delete_error, self.current_audio_id)

    def on_delete_success(self, result):
        self.statusBar().showMessage("Áudio movido para a lixeira.", 6000)
        self.current_audio_id = None
        self.lbl_detail.setText("Selecione um item do histórico para ver detalhes.")
        self.btn_play_original.setEnabled(False)
        self.btn_play_processed.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.refresh_history()

    def on_delete_error(self, error_text):
        self.statusBar().showMessage("Falha ao excluir áudio.", 8000)
        QMessageBox.critical(self, "Erro ao excluir", error_text)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _format_size(size_bytes):
        size_bytes = size_bytes or 0
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def _format_duration(duration_ms):
        total_seconds = int(duration_ms / 1000)
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()