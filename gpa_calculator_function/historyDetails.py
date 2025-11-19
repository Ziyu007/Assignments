from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout, QPushButton, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from datetime import datetime
from styles.gpa_styles import gpa_styles

class GPAHistoryDetails(QWidget):
    def __init__(self, parent, record):
        super().__init__()
        self.record = record
        self.parent = parent

        self.setStyleSheet(gpa_styles())
        self.init_ui()

    def init_ui(self):
        # Create main layout for THIS widget (self)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create a container widget for the scroll area
        container_widget = QWidget()
        scroll_area.setWidget(container_widget)
        
        # Layout for the container widget - DON'T create another layout for self
        container_layout = QVBoxLayout(container_widget)  # This is for container_widget, not self
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("History Details")
        title.setObjectName("gpaHeader")
        container_layout.addWidget(title)
        container_layout.addSpacing(10)

        # Date
        date_obj = datetime.fromisoformat(self.record['timestamp'].replace('Z', '+00:00'))
        date_label = QLabel(f"Date: {date_obj.strftime('%Y-%m-%d %H:%M')}")
        container_layout.addWidget(date_label)
        container_layout.addSpacing(10)

        # Results section
        results_group = QGroupBox("Results")
        results_group.setObjectName("resultGroup")
        results_group.setContentsMargins(10, 20, 10, 10)
        results_layout = QGridLayout(results_group)
        results_layout.setSpacing(15)
        results_layout.setContentsMargins(15, 15, 15, 15)

        results_layout.addWidget(QLabel("Input CGPA:"), 0, 0)
        results_layout.addWidget(QLabel(f"{self.record['current_cgpa']:.2f}"), 0, 1)

        results_layout.addWidget(QLabel("Completed Credits:"), 1, 0)
        results_layout.addWidget(QLabel(str(self.record['completed_credits'])), 1, 1)

        results_layout.addWidget(QLabel("Semester Credits:"), 2, 0)
        results_layout.addWidget(QLabel(str(self.record['semester_credits'])), 2, 1)

        results_layout.addWidget(QLabel("GPA:"), 3, 0)
        results_layout.addWidget(QLabel(f"{self.record['gpa']:.2f}"), 3, 1)

        results_layout.addWidget(QLabel("Total Credits:"), 4, 0)
        results_layout.addWidget(QLabel(str(self.record['total_credits'])), 4, 1)

        results_layout.addWidget(QLabel("CGPA:"), 5, 0)
        results_layout.addWidget(QLabel(f"{self.record['cgpa']:.2f}"), 5, 1)

        container_layout.addWidget(results_group)
        container_layout.addSpacing(15)

        # Courses section
        courses_group = QGroupBox("Courses")
        courses_group.setObjectName("courseGroup")
        courses_group.setContentsMargins(10, 20, 10, 10)
        courses_layout = QVBoxLayout(courses_group)
        courses_layout.setSpacing(15)
        courses_layout.setContentsMargins(15, 15, 15, 15)

        if self.record['courses_data']:
            for course in self.record['courses_data']:
                course_text = f"{course['name'].upper()} - {course['credits']} credits - Grade: {course['grade']}"
                course_label = QLabel(course_text)
                courses_layout.addWidget(course_label)
        else:
            courses_layout.addWidget(QLabel("No course data available"))

        container_layout.addWidget(courses_group)
        container_layout.addSpacing(15)

        # Performance Comparison Chart
        chart_group = QGroupBox("Performance Comparison")
        chart_group.setObjectName("chartGroup")
        chart_group.setContentsMargins(10, 20, 10, 10)
        chart_layout = QVBoxLayout(chart_group)
        chart_layout.setSpacing(10)
        chart_layout.setContentsMargins(15, 15, 15, 15)

        # Get the values FIRST
        semester_gpa = self.record['gpa']
        current_cgpa = self.record['current_cgpa']
        new_cgpa = self.record['cgpa']

        # Create grid for aligned content
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        def create_bar(value, max_value=4.0):
            bar_length = 20
            filled = int((value / max_value) * bar_length)
            return "█" * filled + "░" * (bar_length - filled)

        # Add rows
        metrics = [
            ("Semester GPA", semester_gpa),
            ("Previous CGPA", current_cgpa),
            ("New CGPA", new_cgpa)
        ]

        for row, (name, value) in enumerate(metrics, 1):
            grid_layout.addWidget(QLabel(name), row, 0)
            
            # Create bar label with monospace font for proper alignment
            bar_label = QLabel(create_bar(value))
            bar_label.setFont(QFont("Monospace", 9))  # Monospace for consistent width
            grid_layout.addWidget(bar_label, row, 1)
            
            value_label = QLabel(f"{value:.2f}")
            value_label.setAlignment(Qt.AlignCenter)
            grid_layout.addWidget(value_label, row, 2)

        chart_layout.addLayout(grid_layout)
        chart_layout.addSpacing(10)

        # Add performance text
        performance_text = ""
        if semester_gpa > current_cgpa:
            performance_text = "✅ This semester improved your CGPA"
        elif semester_gpa < current_cgpa:
            performance_text = "⚠️ This semester lowered your CGPA"
        else:
            performance_text = "➡️ This semester maintained your CGPA"

        performance_label = QLabel(performance_text)
        performance_label.setAlignment(Qt.AlignCenter)
        chart_layout.addWidget(performance_label)

        container_layout.addWidget(chart_group)

        # Add stretch at the end
        container_layout.addStretch()

        # Add scroll area to the main layout (this is the only widget in main_layout)
        main_layout.addWidget(scroll_area)