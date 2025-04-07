import os
import socket
import subprocess
import sys
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFileDialog, QMessageBox, QHBoxLayout,
    QFrame, QToolButton
)
from PyQt6.QtGui import QPixmap, QFont, QDesktopServices, QCursor
from PyQt6.QtCore import Qt, QUrl

# 🔧 Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)  # Ensure working directory is set correctly when launched via mouse

VIDEO_DIR = "C:/Videos"
VLC_PATH = r"C:\Program Files (x86)\VideoLAN\vlc.exe"
vlc = VLC_PATH  # ✅ Define this to avoid undefined reference

PROTOCOLS = {
    "SRT": "srt://{ip}:{port}?mode=listener",
    "RTSP": "rtsp://{ip}:{port}/stream",
    "RTMP": "rtmp://{ip}:{port}/live",
    "RTP": "rtp://{ip}:{port}"
}

FFMPEG_CMD = {
    "SRT": "ffmpeg -re -i \"{file}\" -c:v libx264 -f mpegts {url}",
    "RTSP": "ffmpeg -re -i \"{file}\" -c:v libx264 -f rtsp {url}",
    "RTMP": "ffmpeg -re -i \"{file}\" -c:v libx264 -f flv {url}",
    "RTP": "ffmpeg -re -i \"{file}\" -c:v libx264 -f rtp {url}"
}

def get_local_ips():
    ips = []
    hostname = socket.gethostname()
    try:
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if "." in ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception as e:
        print("Error getting IPs:", e)
    return ips if ips else ["127.0.0.1"]

class VideoStreamer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎥 Video Streamer Pro")
        self.setGeometry(400, 150, 620, 500)
        self.setStyleSheet("background-color: #f4f4f4;")
        self.process = None
        self.selected_file = None

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 🖼 Logo
        logo_label = QLabel()
        logo_path = os.path.join(BASE_DIR, "logo.png")
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            logo_label.setPixmap(pixmap.scaledToHeight(80))
        else:
            logo_label.setText("📺")  # fallback emoji
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # 📛 Title
        title = QLabel("Video Streaming Dashboard")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #333333; margin-bottom: 20px;")
        layout.addWidget(title)

        # 📂 Video selection
        self.video_label = QLabel("No video selected.")
        self.video_label.setFont(QFont("Arial", 10))
        self.video_label.setStyleSheet("color: #555; margin-top: 10px;")
        layout.addWidget(self.video_label)

        self.select_btn = QPushButton("🎞️ Select Video from C:/Videos")
        self.select_btn.clicked.connect(self.select_video)
        self.select_btn.setStyleSheet("padding: 8px; background-color: #ffffff; border: 1px solid #aaa;")
        layout.addWidget(self.select_btn)

        # 🌐 IP Selection
        ip_layout = QHBoxLayout()
        ip_label = QLabel("Select IP:")
        ip_label.setStyleSheet("margin-right: 10px;")
        self.ip_selector = QComboBox()
        self.ip_selector.addItems(get_local_ips())
        self.ip_selector.setStyleSheet("padding: 5px;")
        ip_layout.addWidget(ip_label)
        ip_layout.addWidget(self.ip_selector)
        layout.addLayout(ip_layout)

        # 🌐 Protocol and Port
        protocol_layout = QHBoxLayout()
        self.protocol_box = QComboBox()
        self.protocol_box.addItems(PROTOCOLS.keys())
        self.protocol_box.setStyleSheet("padding: 5px;")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Enter port (e.g., 9999)")
        self.port_input.setStyleSheet("padding: 5px;")
        protocol_layout.addWidget(self.protocol_box)
        protocol_layout.addWidget(self.port_input)
        layout.addLayout(protocol_layout)

        # ▶️ Buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 Start Streaming")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        self.start_btn.clicked.connect(self.start_stream)
        self.stop_btn = QPushButton("🛑 Stop")
        self.stop_btn.setStyleSheet("background-color: #d9534f; color: white; padding: 10px;")
        self.stop_btn.clicked.connect(self.stop_stream)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)

        # 📡 Playback Section
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        self.result_label = QLabel("Playback URL will appear here.")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("margin-top: 20px; font-weight: bold; color: #333333;")
        layout.addWidget(self.result_label)

        # 🔗 Clickable Playback URL
        self.url_field = QLabel()
        self.url_field.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.url_field.setOpenExternalLinks(False)
        self.url_field.setStyleSheet("color: blue; text-decoration: underline; margin-top: 10px;")
        self.url_field.mousePressEvent = self.launch_vlc
        layout.addWidget(self.url_field)

        # 📋 Copy Button
        url_copy_layout = QHBoxLayout()
        self.copy_btn = QToolButton()
        self.copy_btn.setText("📋 Copy Playback URL")
        self.copy_btn.clicked.connect(self.copy_url)
        url_copy_layout.addWidget(self.copy_btn)
        layout.addLayout(url_copy_layout)

        self.setLayout(layout)

    def select_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            VIDEO_DIR,
            "Video Files (*.mp4 *.mkv *.avi *.mov *.flv)"
        )
        if file_path:
            self.selected_file = file_path
            self.video_label.setText(f"🎬 Selected: {os.path.basename(file_path)}")

    def start_stream(self):
        if not self.selected_file:
            QMessageBox.warning(self, "Error", "Please select a video file.")
            return

        port = self.port_input.text().strip()
        if not port.isdigit():
            QMessageBox.warning(self, "Error", "Please enter a valid port number.")
            return

        protocol = self.protocol_box.currentText()
        ip = self.ip_selector.currentText()
        stream_url = PROTOCOLS[protocol].format(ip=ip, port=port)
        cmd = FFMPEG_CMD[protocol].format(file=self.selected_file, url=stream_url)

        self.stop_stream()

        try:
            self.process = subprocess.Popen(cmd, shell=True)
            self.result_label.setText(f"<b style='color:#0066cc'>✅ Streaming started:</b><br><code>{stream_url}</code>")
            self.url_field.setText(f"<a href='#'>{stream_url}</a>")
            self.url_field.setToolTip("Click to play in VLC")
        except Exception as e:
            QMessageBox.critical(self, "Failed", f"Failed to start stream: {str(e)}")

    def stop_stream(self):
        if self.process:
            self.process.terminate()
            self.process = None
            self.result_label.setText("<b style='color:#cc0000'>⛔ Streaming stopped.</b>")
            self.url_field.setText("")

    def copy_url(self):
        url = self.url_field.text()
        if url:
            clean_url = url.replace('<a href="#">', '').replace('</a>', '')
            QApplication.clipboard().setText(clean_url)
            QMessageBox.information(self, "Copied", "Playback URL copied to clipboard!")

    def launch_vlc(self, event):
        url = self.url_field.text().replace('<a href="#">', '').replace('</a>', '')
        if os.path.exists(vlc):
            try:
                subprocess.Popen([vlc, url])
            except Exception as e:
                QMessageBox.critical(self, "VLC Error", f"Could not launch VLC: {str(e)}")
        else:
            QMessageBox.warning(self, "VLC Not Found", f"VLC was not found at:\n{VLC_PATH}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = VideoStreamer()
    win.show()
    sys.exit(app.exec())
