from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QPushButton,
                            QStackedWidget, QLabel)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from .gpaCalculator import GPACalculatorPage
from .goalCalculator import GoalCalculatorPage
from .gpaHistory import GPAHistory
from .gradingScheme import GradingSchemePage
from .feature_button import FeatureButton
from styles.gpa_styles import gpa_styles
from database.db_manager import get_gpa_history

class GPACalculatorWidget(QWidget):
    def __init__(self, main_window, user_id):
        super().__init__()
        self.main_window = main_window
        self.current_user_id = user_id

        # Initialize back button state attributes
        self.original_back_text = ""
        self.original_current_widget = None
        
        # Apply styles
        self.setStyleSheet(gpa_styles())

        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # Stacked widget FIRST
        self.pages = QStackedWidget()
        self.main_layout.addWidget(self.pages)
        
        # Create all pages
        self.create_feature_grid_page()
        self.create_gpa_pages()
        
        # Show feature grid by default
        self.pages.setCurrentWidget(self.feature_grid_page)
        
        # Back button LAST (without position specification)
        self.setup_back_button()

    def setup_back_button(self):
        """Back button shown on all pages - add to layout LAST"""
        self.back_btn = QPushButton()
        self.back_btn.setIcon(QIcon("Photo/back.png"))
        self.back_btn.setText(" Back to Home")
        self.back_btn.setFixedSize(750, 40)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setObjectName("iconBackButton")
        self.back_btn.setIconSize(QSize(16, 16))
        self.back_btn.clicked.connect(self.handle_back)
        # ✅ Changed: No position specified, just alignment
        self.main_layout.addWidget(self.back_btn, alignment=Qt.AlignCenter)

    # ... rest of the methods remain the same ...
    def create_feature_grid_page(self):
        """Create the main GPA feature selection grid"""
        self.feature_grid_page = QWidget()
        layout = QVBoxLayout(self.feature_grid_page)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        title = QLabel("Academic Tools")
        title.setContentsMargins(0, 0, 0, 0)
        title.setObjectName("gpaHeader")
        layout.addWidget(title)

        # Feature grid
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(15)
        grid_layout.setVerticalSpacing(35)

        features = [
            ("Photo/gpa_icon.png", "GPA Calculator", self.show_gpa_calculator),
            ("Photo/goal-calculator.png", "Goal Calculator", self.show_goal_calculator),
            ("Photo/historycalculation.png", "View History", self.show_history),
            ("Photo/gradingscheme.png", "Grading Scheme", self.show_grading_scheme),
        ]

        for i, (icon, text, handler) in enumerate(features):
            # Use "gpa" size type for gpa page
            btn = FeatureButton(icon, text, size_type="gpa")
            btn.clicked.connect(handler)
            grid_layout.addWidget(btn, i // 2, i % 2)

        layout.addLayout(grid_layout)
        layout.addStretch()
        self.pages.addWidget(self.feature_grid_page)

    def create_gpa_pages(self):
        """Create all GPA feature pages"""
        self.gpa_calculator_page = GPACalculatorPage(self)
        self.goal_calculator_page = GoalCalculatorPage(self)

        history_data = get_gpa_history(self.current_user_id) # Fetch data from database first
        self.history_page = GPAHistory(self, history_data, self.gpa_calculator_page)
        self.grading_scheme_page = GradingSchemePage(self)
        
        self.pages.addWidget(self.gpa_calculator_page)
        self.pages.addWidget(self.goal_calculator_page)
        self.pages.addWidget(self.history_page)
        self.pages.addWidget(self.grading_scheme_page)

    def store_back_button_state(self):
        """Store the current back button state"""
        self.original_back_text = self.back_btn.text()
        self.original_current_widget = self.pages.currentWidget()

    def restore_back_button_state(self):
        """Restore the back button to its original state"""
        try:
            # Always reconnect to handle_back
            self.back_btn.clicked.disconnect()
            self.back_btn.clicked.connect(self.handle_back)
            
            # Restore the original text based on which page we were on
            if self.original_current_widget == self.feature_grid_page:
                self.back_btn.setText(" Back to Home")
            else:
                self.back_btn.setText(" Back")
                
        except Exception as e:
            print(f"Error restoring back button: {e}")
            # Fallback
            self.back_btn.clicked.connect(self.handle_back)
            self.back_btn.setText(" Back")

    def handle_back(self):
        """Handle back button navigation"""
        if self.pages.currentWidget() != self.feature_grid_page:
            self.pages.setCurrentWidget(self.feature_grid_page)
            self.back_btn.setText(" Back to Home")
        else:
            # Go back to main application home
            self.main_window.pages.setCurrentWidget(self.main_window.feature_grid_page)

    # Navigation methods
    def show_gpa_calculator(self):
        self.pages.setCurrentWidget(self.gpa_calculator_page)
        self.back_btn.setText(" Back")

    def show_goal_calculator(self):
        self.pages.setCurrentWidget(self.goal_calculator_page)
        self.back_btn.setText(" Back")

    def show_history(self):
        """Show history from feature grid - should return to feature grid"""
        fresh_history_data = get_gpa_history(self.current_user_id)
        
        # Store the current back button state before navigating
        self.store_back_button_state()
        
        # Update history page with flag indicating we came from feature grid
        self.history_page.refresh_data(fresh_history_data, from_calculator=False)
        self.pages.setCurrentWidget(self.history_page)
        self.back_btn.setText(" Back")

    def show_grading_scheme(self):
        self.pages.setCurrentWidget(self.grading_scheme_page)
        self.back_btn.setText(" Back")