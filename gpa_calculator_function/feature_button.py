from PyQt5.QtWidgets import QPushButton, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

class FeatureButton(QPushButton): 
    def __init__(self, icon_path, text, parent=None, size_type="main"):
        super().__init__(parent)
        self.setObjectName("FeatureButton")
        self.setCursor(Qt.PointingHandCursor)
        
        # Set different sizes for main page vs booking page
        if size_type == "main":
            self.setFixedSize(350, 350)  # Square for main page
            container_size = 350
            icon_size = 150
            margins = (70, 70, 70, 70)
        else:  # booking page
            self.setFixedSize(350, 300)  # Rectangle for booking page
            container_size = 300
            icon_size = 120
            margins = (50, 50, 50, 30)

        # Container for icon + text
        container = QWidget(self)
        container.setGeometry(0, 0, self.width(), self.height())

        layout = QVBoxLayout(container)
        layout.setContentsMargins(*margins)
        layout.setSpacing(10)

        # Icon setup
        icon_label = QLabel()
        icon_label.setObjectName("iconLabel")
        icon_pixmap = QPixmap(icon_path).scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(text)
        text_label.setObjectName("textLabel")
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon_label)
        layout.addWidget(text_label)