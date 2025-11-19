from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit,
    QComboBox, QPushButton, QSpinBox, QMessageBox, QFrame, QSizePolicy, 
    QScrollArea, QGridLayout, QGroupBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QDialog, QStackedWidget
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QDoubleValidator, QIntValidator
import sys
from styles.gpa_styles import gpa_styles
from database.db_manager import save_gpa_calculation, get_gpa_history  # Import database functions
from .gpaHistory import GPAHistory

qualityPoint = {
    "A+": 4.00, "A": 4.00, "A-": 3.67,
    "B+": 3.33, "B": 3.00, "B-": 2.67,
    "C+": 2.33, "C": 2.00, "F": 0.00
}

class GPACalculatorPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_user_id = main_window.current_user_id
        self.course_rows = []
        
        self.setStyleSheet(gpa_styles())
        self.init_ui()
        self.update_results()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        self.semester_credits_label = QLabel("0")
        self.gpa_label = QLabel("0.00")
        self.total_credits_label = QLabel("0")
        self.cgpa_label = QLabel("0.00")
        
        # Set larger fonts for result values
        value_font = QFont()
        value_font.setPointSize(16)
        value_font.setBold(True)
        self.semester_credits_label.setFont(value_font)
        self.gpa_label.setFont(value_font)
        self.total_credits_label.setFont(value_font)
        self.cgpa_label.setFont(value_font)

        title_bar = QHBoxLayout()

        # Header and subheader spanning full width
        title = QLabel("GPA and CGPA Calculator")
        title.setObjectName("gpaHeader")
        title_bar.addWidget(title)
        
        title_bar.addStretch()

        # Reset button
        reset_btn = QPushButton("Reset")
        reset_btn.setIcon(QIcon("Photo/reset.png"))
        reset_btn.setObjectName("resetButton")
        reset_btn.setCursor(Qt.PointingHandCursor) 
        reset_btn.setFixedSize(110, 45)
        reset_btn.clicked.connect(self.reset_all)
        title_bar.addWidget(reset_btn)
    
        # History button on the right
        history_btn = QPushButton("View History")
        history_btn.setIcon(QIcon("Photo/history_gpa.png"))
        history_btn.setObjectName("historyButton")
        history_btn.setCursor(Qt.PointingHandCursor) 
        history_btn.setFixedSize(180, 45)
        history_btn.clicked.connect(self.show_history)
        title_bar.addWidget(history_btn)

        # Add title bar to main layout
        layout.addLayout(title_bar)

        subtitle = QLabel(
            "To calculate GPA, enter the Credit and select the Grade for each course/ subject.\n"
            "To calculate CGPA, enter current CGPA and Credits Completed prior to this semester.")
        subtitle.setObjectName("gpaSubheader")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Create layout for content (inputs + results)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        layout.addLayout(content_layout)

        # Left side - scrollable inputs
        left_widget = QWidget()
        left_widget.setContentsMargins(0, 0, 0, 0)
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Create a scroll area for the inputs only
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create a container widget for the scroll area
        container_widget = QWidget()
        scroll_area.setWidget(container_widget)
        
        # Container layout for scrollable content
        container_layout = QVBoxLayout(container_widget)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Create group box for current academic status
        status_group = QGroupBox("Current Academic Status")
        status_group.setObjectName("statusGroup")
        status_group.setMinimumHeight(200)
        status_layout = QGridLayout(status_group)
        status_layout.setVerticalSpacing(10)
        status_layout.setHorizontalSpacing(15)

        # Add input validators
        cgpa_validator = QDoubleValidator(0.0, 4.0, 2)
        cgpa_validator.setNotation(QDoubleValidator.StandardNotation)
        
        credits_validator = QIntValidator(0, 10)
        
        self.cgpa_input = QLineEdit()
        self.cgpa_input.setPlaceholderText("E.g. 3.75")
        self.cgpa_input.setValidator(cgpa_validator)
        self.cgpa_input.textChanged.connect(self.update_results)

        self.credits_input = QLineEdit()
        self.credits_input.setPlaceholderText("E.g. 45")
        self.credits_input.setValidator(credits_validator)
        self.credits_input.textChanged.connect(self.update_results)

        status_layout.addWidget(QLabel("Current CGPA:"), 0, 0)
        status_layout.addWidget(self.cgpa_input, 0, 1)
        status_layout.addWidget(QLabel("Credits Completed:"), 1, 0)
        status_layout.addWidget(self.credits_input, 1, 1)

        container_layout.addWidget(status_group)

        # Course section
        course_group = QGroupBox("Courses")
        course_group.setObjectName("courseGroup")
        course_layout = QVBoxLayout(course_group)
        course_layout.setSpacing(12)
        
        # Course section header
        course_header = QHBoxLayout()
        course_header.setContentsMargins(0, 0, 0, 0)

        # Courses label on the left
        course_label = QLabel("Course")
        course_label.setObjectName("course_header")
        course_header.addWidget(course_label)

        # Add stretch to push the other headers to the right
        course_header.addStretch()

        # Credits header
        credits_label = QLabel("Credits")
        credits_label.setObjectName("course_header")
        credits_label.setAlignment(Qt.AlignCenter)
        credits_label.setFixedWidth(80)
        course_header.addWidget(credits_label)

        # Add some spacing between Credits and Grade
        course_header.addSpacing(10)

        # Grade header
        grade_label = QLabel("Grade")
        grade_label.setObjectName("course_header")
        grade_label.setAlignment(Qt.AlignCenter)
        grade_label.setFixedWidth(80)
        course_header.addWidget(grade_label)

        # Add space for the remove button
        course_header.addSpacing(40)

        course_layout.addLayout(course_header)

        # Create widget for courses
        course_content = QWidget()
        self.course_content_layout = QVBoxLayout(course_content)
        self.course_content_layout.setAlignment(Qt.AlignTop)
        self.course_content_layout.setSpacing(12)
        self.course_content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add initial course rows
        for _ in range(3):
            self.add_course_row()

        course_layout.addWidget(course_content)

        # Add Course button at the bottom of the groupbox
        add_btn_inside = QPushButton("Add Course")
        add_btn_inside.setIcon(QIcon("Photo/plus.png"))
        add_btn_inside.setObjectName("addCourseButton")
        add_btn_inside.setCursor(Qt.PointingHandCursor)
        add_btn_inside.setFixedSize(300, 35)
        add_btn_inside.clicked.connect(self.add_course_row)
        course_layout.addWidget(add_btn_inside, alignment=Qt.AlignLeft)  # ← Centered

        container_layout.addWidget(course_group)

        # Add scroll area to left layout (only the input fields will scroll)
        left_layout.addWidget(scroll_area)
        content_layout.addWidget(left_widget, 75)  # 75% width for left side
        
        # Right side - fixed result card (outside the scroll area)
        result_card = QFrame()
        result_card.setObjectName("resultCard")
        result_card.setMaximumWidth(200)
        result_card.setMaximumHeight(540)
        result_card.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        
        result_layout = QVBoxLayout(result_card)
        result_layout.setAlignment(Qt.AlignCenter)
        result_layout.setSpacing(12)
        result_layout.setContentsMargins(5, 8, 5, 8)
        
        # Add title to result card
        result_title = QLabel("Results")
        result_title.setObjectName("resultTitle")
        result_title.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(result_title)
        
        # Add result items with centered values
        result_items = [
            ("Semester Credits", self.semester_credits_label),
            ("GPA", self.gpa_label),
            ("Total Credits", self.total_credits_label),
            ("CGPA", self.cgpa_label)
        ]
        
        for label_text, value_label in result_items:
            # Create a container for each result item
            item_container = QVBoxLayout()
            item_container.setSpacing(12)
            item_container.setAlignment(Qt.AlignCenter)
            
            # Label for the item
            label = QLabel(label_text)
            label.setObjectName("resultItemLabel")
            label.setAlignment(Qt.AlignCenter)
            
            # Value for the item (centered)
            value_label.setObjectName("resultValue")
            value_label.setAlignment(Qt.AlignCenter)
            
            item_container.addWidget(label)
            item_container.addWidget(value_label)
            result_layout.addLayout(item_container)
            
            # Add small separator between items (except after the last one)
            if label_text != "CGPA":
                small_separator = QFrame()
                small_separator.setFrameShape(QFrame.HLine)
                small_separator.setFrameShadow(QFrame.Plain)
                small_separator.setStyleSheet("background-color: #eee;")
                small_separator.setFixedHeight(1)
                result_layout.addWidget(small_separator)
        
        content_layout.addWidget(result_card, 25)  # 25% width for right side
        
        # Add course and reset buttons container
        button_container = QHBoxLayout()
        button_container.setSpacing(8)
        
        # Save button
        save_btn = QPushButton(" Save My Calculation")
        save_btn.setIcon(QIcon("Photo/save.png"))
        save_btn.setObjectName("saveButton")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedSize(770, 43)
        save_btn.clicked.connect(self.save_current_calculation)
        button_container.addWidget(save_btn)
        
        button_container.addStretch()
        layout.addLayout(button_container)

    def add_course_row(self):
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_widget.setLayout(row_layout)
        row_layout.setContentsMargins(0, 5, 0, 5)
        row_layout.setSpacing(8)

        name = QLineEdit()
        name.setPlaceholderText("Course name")
        name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        credits = QSpinBox()
        credits.setRange(0, 10)
        credits.setValue(0)
        credits.setFixedWidth(75)
        credits.setFixedHeight(35)
        credits.valueChanged.connect(self.update_results)

        grade = QComboBox()
        grade.addItems(list(qualityPoint.keys()))
        grade.setCurrentIndex(0)
        grade.setFixedWidth(70)
        grade.currentIndexChanged.connect(self.update_results)
        grade.view().setStyleSheet("background-color: white; color: black;")

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(35, 35)
        remove_btn.setObjectName("removeCourseButton")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda: self.remove_course_row(row_widget))

        row_layout.addWidget(name, 1)
        row_layout.addWidget(credits, 0)
        row_layout.addWidget(grade, 0)
        row_layout.addWidget(remove_btn, 0)

        self.course_rows.append((name, credits, grade, row_widget))
        self.course_content_layout.addWidget(row_widget)
        self.update_results()

    def remove_course_row(self, row_widget):
        if len(self.course_rows) <= 1:
            QMessageBox.warning(self, "Cannot Remove", 
                               "You must have at least one course row.")
            return

        # Find and remove the row from course_rows
        for i, (name, credits, grade, widget) in enumerate(self.course_rows):
            if widget == row_widget:
                # Disconnect signals first
                try:
                    credits.valueChanged.disconnect(self.update_results)
                    grade.currentIndexChanged.disconnect(self.update_results)
                except:
                    pass
                
                # Remove from list and delete widget
                self.course_rows.pop(i)
                widget.deleteLater()
                break
        
        self.update_results()

    def reset_all(self):
            """Reset all inputs and course rows"""
            reply = QMessageBox.question(self, 'Reset Confirmation', 
                                    'Are you sure you want to reset all inputs?',
                                    QMessageBox.Yes | QMessageBox.No, 
                                    QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Clear CGPA and credits inputs
                self.cgpa_input.clear()
                self.credits_input.clear()
                
                # Create a copy of the list to avoid modification during iteration
                rows_to_remove = self.course_rows[3:]  # Get rows beyond the first 3
                for row_data in rows_to_remove:
                    self.remove_course_row(row_data[3])  # row_data[3] is the widget
                
                # Reset the remaining 3 course rows
                for name, credits, grade, widget in self.course_rows:
                    name.clear()
                    credits.setValue(0)
                    grade.setCurrentIndex(0)
                
                self.update_results()

    def validate_numeric_input(self, text, field_name, is_float=False):
        """Validate numeric input and return valid status and value"""
        try:
            if not text:  # Empty is valid (optional field)
                return True, 0
                
            if is_float:
                value = float(text)
                if value <= 0 or value > 4.0:  # CGPA should be between 0 and 4.0
                    QMessageBox.warning(self, "Invalid Input", 
                                    f"{field_name} must be between 0.0 and 4.0")
                    return False, 0  # Return 0 instead of None
            else:
                value = int(text)
                if value < 0:
                    QMessageBox.warning(self, "Invalid Input", 
                                    f"{field_name} cannot be negative")
                    return False, 0  # Return 0 instead of None
            return True, value
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", 
                            f"Please enter a valid number for {field_name}")
            return False, 0  # Return 0 instead of None

    def update_results(self):
        total_quality_points = 0
        total_credits = 0
        valid_courses = 0

        for name, credits, grade, widget in self.course_rows:
            selected_grade = grade.currentText()
            credit_val = credits.value()

            if selected_grade in qualityPoint and credit_val > 0:
                gp = qualityPoint[selected_grade]
                total_quality_points += gp * credit_val
                total_credits += credit_val
                valid_courses += 1

        self.semester_credits_label.setText(str(total_credits))
        
        # Calculate GPA
        if total_credits > 0:
            gpa = total_quality_points / total_credits
            self.gpa_label.setText(f"{gpa:.2f}")
        else:
            self.gpa_label.setText("0.00")
            gpa = 0

        # Validate inputs before CGPA calculation
        cgpa_valid, current_cgpa = self.validate_numeric_input(
            self.cgpa_input.text(), "CGPA", is_float=True
        )
        
        credits_valid, completed_credits = self.validate_numeric_input(
            self.credits_input.text(), "Completed Credits"
        )

        # Only calculate CGPA if we have valid inputs
        if cgpa_valid and credits_valid:
            try:
                total_completed = completed_credits + total_credits
                if total_completed > 0:
                    overall_points = current_cgpa * completed_credits + gpa * total_credits
                    new_cgpa = overall_points / total_completed
                    self.total_credits_label.setText(str(total_completed))
                    self.cgpa_label.setText(f"{new_cgpa:.2f}")
                else:
                    self.total_credits_label.setText("0")
                    self.cgpa_label.setText("0.00")
            except ZeroDivisionError:
                self.total_credits_label.setText(str(total_credits))
                self.cgpa_label.setText(f"{gpa:.2f}")
        else:
            # Show only semester results if CGPA inputs are invalid
            self.total_credits_label.setText(str(total_credits))
            self.cgpa_label.setText(f"{gpa:.2f}")
    
    def reset_after_save(self):
        """Reset input fields after successful save"""
        # Clear CGPA and credits inputs
        self.cgpa_input.clear()
        self.credits_input.clear()
        
        # Clear all course rows by disconnecting signals and removing manually
        # Disconnect signals first to avoid update_results calls
        for name, credits, grade, widget in self.course_rows:
            try:
                credits.valueChanged.disconnect(self.update_results)
                grade.currentIndexChanged.disconnect(self.update_results)
            except:
                pass
            widget.deleteLater()
        
        # Clear the list
        self.course_rows = []
        
        # Add 3 fresh course rows
        for _ in range(3):
            self.add_course_row()
        
        # Update results to show zeros
        self.update_results()

    def save_current_calculation(self):
        """Save the current calculation to the database"""
        # Prepare courses data - ONLY include courses with names and credits > 0
        courses_data = []
        for name, credits, grade, widget in self.course_rows:
            course_name = name.text().strip()
            credit_val = credits.value()
            
            # Only include courses that have a name AND credits > 0
            if course_name and credit_val > 0:
                courses_data.append({
                    'name': course_name,
                    'credits': credit_val,
                    'grade': grade.currentText()
                })
        
        # Show warning if no valid courses
        if not courses_data:
            QMessageBox.warning(self, "No Courses", 
                            "Please add at least one course with a name and credits.")
            return
        
        # Get current values
        semester_credits = int(self.semester_credits_label.text())
        gpa = float(self.gpa_label.text())
        total_credits = int(self.total_credits_label.text())
        cgpa = float(self.cgpa_label.text())
        
        # Get current CGPA and completed credits inputs
        current_cgpa = 0.0
        completed_credits = 0
        try:
            if self.cgpa_input.text():
                current_cgpa = float(self.cgpa_input.text())
            if self.credits_input.text():
                completed_credits = int(self.credits_input.text())
        except ValueError:
            pass
        
        # Save to database using db_manager function
        success = save_gpa_calculation(
            self.current_user_id, semester_credits, gpa, 
            total_credits, cgpa, courses_data, current_cgpa, completed_credits
        )
        
        if success:
            QMessageBox.information(self, "Success", "Calculation saved to history!")
            self.reset_after_save()
        else:
            QMessageBox.warning(self, "Error", "Failed to save calculation.")

    def show_history(self):
        """Show history from GPA calculator page - should return to calculator"""
        history_data = get_gpa_history(self.current_user_id)
        
        # Create history page with proper parent reference
        history_page = GPAHistory(self.main_window, history_data, self, from_calculator=True)
        
        # Add to main window's pages stack
        self.main_window.pages.addWidget(history_page)
        self.main_window.pages.setCurrentWidget(history_page)
        
        # Update back button text
        if hasattr(self.main_window, 'back_btn'):
            self.main_window.back_btn.setText(" Back")
            
        # Store the current state for proper back navigation
        if hasattr(self.main_window, 'store_back_button_state'):
            self.main_window.store_back_button_state()