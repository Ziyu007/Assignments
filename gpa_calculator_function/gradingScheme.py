from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt
from styles.gpa_styles import gpa_styles

class GradingSchemePage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setStyleSheet(gpa_styles())
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Grading Scheme")
        title.setObjectName("gpaHeader")
        layout.addWidget(title)

        # Description
        desc = QLabel("Grade to quality point conversion table for GPA computation")
        desc.setObjectName("gpaSubheader")
        layout.addWidget(desc)

        # Grading Table - COMPACT VERSION
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setRowCount(9)
        self.table.setHorizontalHeaderLabels(["Marks", "Grade", "Quality Points"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Set compact row heights
        for row in range(9):
            self.table.setRowHeight(row, 57)
        
        # Set table data
        grading_data = [
            ("90 - 100", "A+", "4.00"),
            ("80 - 89", "A", "4.00"),
            ("75 - 79", "A-", "3.67"),
            ("70 - 74", "B+", "3.33"),
            ("65 - 69", "B", "3.00"),
            ("60 - 64", "B-", "2.67"),
            ("55 - 59", "C+", "2.33"),
            ("50 - 54", "C", "2.00"),
            ("0 - 49", "F", "0.00")
        ]

        for row, (marks, grade, points) in enumerate(grading_data):
            self.table.setItem(row, 0, QTableWidgetItem(marks))
            self.table.setItem(row, 1, QTableWidgetItem(grade))
            self.table.setItem(row, 2, QTableWidgetItem(points))
            
            for col in range(3):
                self.table.item(row, col).setTextAlignment(Qt.AlignCenter)

        # Set fixed height to prevent scrolling
        self.table.setFixedHeight(580)
        self.table.setStyleSheet("""
            /* Table styles */
            QTableWidget {
                font-size: 16px;
            }

            QTableWidget::item {
                font-size: 16px;
            }
                                 
            QHeaderView::section {
                font-size: 18px;
            }
        """)
        
        layout.addWidget(self.table)

        # Add some stretch to center everything
        layout.addStretch()

    def go_back(self):
        """Navigate back to previous page"""
        self.parent.pages.setCurrentWidget(self.parent.feature_grid_page)
        self.parent.pages.removeWidget(self)
        self.deleteLater()