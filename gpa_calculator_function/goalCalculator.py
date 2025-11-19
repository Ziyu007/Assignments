from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QGroupBox, QGridLayout, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QDoubleValidator, QIntValidator
from styles.gpa_styles import gpa_styles

class GoalCalculatorPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.current_cgpa = 0.0
        self.completed_credits = 0
        
        self.setStyleSheet(gpa_styles())
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        title_bar = QHBoxLayout()

        # Title
        title = QLabel("CGPA Goal Calculator")
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

        # Add title bar to main layout
        layout.addLayout(title_bar)
        
        # Description
        desc = QLabel("Calculate the GPA you need next semester to reach your target CGPA")
        desc.setObjectName("gpaSubheader")
        layout.addWidget(desc)
        
        # Input Group
        input_group = QGroupBox("Input Parameters")
        input_group.setObjectName("inputGroup")
        input_layout = QGridLayout(input_group)
        input_layout.setSpacing(10)
        
        # Add input validators
        cgpa_validator = QDoubleValidator(0.0, 4.0, 2)
        cgpa_validator.setNotation(QDoubleValidator.StandardNotation)
        
        credits_validator = QIntValidator(0, 999)
        
        # Current CGPA
        input_layout.addWidget(QLabel("Current CGPA:"), 0, 0)
        self.current_cgpa_input = QLineEdit()
        self.current_cgpa_input.setPlaceholderText("E.g. 3.25")
        self.current_cgpa_input.setValidator(cgpa_validator)
        input_layout.addWidget(self.current_cgpa_input, 0, 1)
        
        # Completed Credits
        input_layout.addWidget(QLabel("Completed Credits:"), 1, 0)
        self.completed_credits_input = QLineEdit()
        self.completed_credits_input.setPlaceholderText("E.g. 45")
        self.completed_credits_input.setValidator(credits_validator)
        input_layout.addWidget(self.completed_credits_input, 1, 1)
        
        # Target CGPA
        input_layout.addWidget(QLabel("Target CGPA:"), 2, 0)
        self.target_cgpa_input = QLineEdit()
        self.target_cgpa_input.setPlaceholderText("E.g. 3.5")
        self.target_cgpa_input.setValidator(cgpa_validator)
        input_layout.addWidget(self.target_cgpa_input, 2, 1)
        
        # Future Credits (next semester)
        input_layout.addWidget(QLabel("Next Semester Credits:"), 3, 0)
        self.future_credits_input = QLineEdit()
        self.future_credits_input.setPlaceholderText("E.g. 15")
        self.future_credits_input.setValidator(credits_validator)
        input_layout.addWidget(self.future_credits_input, 3, 1)
        
        layout.addWidget(input_group)
        
        # Calculate Button
        calculate_btn = QPushButton("Calculate Required GPA")
        calculate_btn.setObjectName("calculateButton")
        calculate_btn.setCursor(Qt.PointingHandCursor) 
        calculate_btn.clicked.connect(self.calculate_required_gpa)
        layout.addWidget(calculate_btn)
        
        # Results Group (initially hidden)
        self.results_group = QGroupBox("Results")
        self.results_group.setObjectName("resultGroup")
        self.results_group.setVisible(False)
        results_layout = QVBoxLayout(self.results_group)
        
        self.required_gpa_label = QLabel()
        self.required_gpa_label.setAlignment(Qt.AlignCenter)
        self.required_gpa_label.setObjectName("resultValue")

        self.explanation_label = QLabel()
        self.explanation_label.setAlignment(Qt.AlignCenter)
        self.explanation_label.setWordWrap(True)
        
        self.scenario_label = QLabel()
        self.scenario_label.setAlignment(Qt.AlignCenter)
        self.scenario_label.setWordWrap(True)
        
        results_layout.addWidget(self.required_gpa_label)
        results_layout.addWidget(self.explanation_label)
        results_layout.addWidget(self.scenario_label)
        
        layout.addWidget(self.results_group)
        layout.addStretch()
    
    def validate_numeric_input(self, text, field_name, is_float=False, allow_zero=False):
        """Validate numeric input and return valid status and value"""
        try:
            if not text.strip():  # Check for empty input first
                return False, 0  # Return False but don't show error here
                
            if is_float:
                value = float(text)
                if value < 0 or value > 4.0:  # CGPA should be between 0 and 4.0
                    QMessageBox.warning(self, "Invalid Input", 
                                    f"{field_name} must be between 0.0 and 4.0")
                    return False, 0
            else:
                value = int(text)
                if value < 0:
                    QMessageBox.warning(self, "Invalid Input", 
                                    f"{field_name} cannot be negative")
                    return False, 0
                if not allow_zero and value == 0:
                    QMessageBox.warning(self, "Invalid Input", 
                                    f"{field_name} cannot be zero")
                    return False, 0
                    
            return True, value
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", 
                            f"Please enter a valid number for {field_name}")
            return False, 0

    def calculate_required_gpa(self):
        # Collect all validation results first
        validations = []
        
        validations.append(self.validate_numeric_input(
            self.current_cgpa_input.text(), "Current CGPA", is_float=True
        ))
        
        validations.append(self.validate_numeric_input(
            self.completed_credits_input.text(), "Completed Credits"
        ))
        
        validations.append(self.validate_numeric_input(
            self.target_cgpa_input.text(), "Target CGPA", is_float=True
        ))
        
        validations.append(self.validate_numeric_input(
            self.future_credits_input.text(), "Next Semester Credits", allow_zero=False
        ))
        
        # Check if any fields are empty
        empty_fields = []
        if not self.current_cgpa_input.text().strip():
            empty_fields.append("Current CGPA")
        if not self.completed_credits_input.text().strip():
            empty_fields.append("Completed Credits")
        if not self.target_cgpa_input.text().strip():
            empty_fields.append("Target CGPA")
        if not self.future_credits_input.text().strip():
            empty_fields.append("Next Semester Credits")
        
        # Show single error message for empty fields
        if empty_fields:
            field_list = ", ".join(empty_fields)
            QMessageBox.warning(self, "Missing Inputs", 
                            f"Please fill in the following fields:\n{field_list}")
            return
        
        # Check if all inputs are valid (no range errors)
        if not all([valid for valid, value in validations]):
            return  # Error messages already shown by validate_numeric_input
        
        # Extract the values
        current_cgpa = validations[0][1]
        completed_credits = validations[1][1]
        target_cgpa = validations[2][1]
        future_credits = validations[3][1]
        
        # Additional validation: Target CGPA should be achievable
        if target_cgpa < current_cgpa:
            QMessageBox.warning(self, "Invalid Target", 
                            "Target CGPA cannot be lower than current CGPA")
            return
            
        # Calculate required GPA
        current_total = current_cgpa * completed_credits
        future_total = target_cgpa * (completed_credits + future_credits)
        required_gpa = (future_total - current_total) / future_credits
        
        # Clamp between 0-4.0 and round
        required_gpa = max(0.0, min(4.0, round(required_gpa, 2)))

        # Display results
        self.required_gpa_label.setText(f"Required GPA: {required_gpa:.2f}")
            
        # Set the explanation
        explanation_text = f"""To reach your target CGPA of {target_cgpa:.2f}, you need to get 
    a GPA of {required_gpa:.2f} in your next semester."""
            
        self.explanation_label.setText(explanation_text)

        # Add scenario analysis
        if required_gpa > 4.0:
            scenario = "⚠️  Target exceeds maximum GPA - recommend adjusting timeline or goal"
        elif required_gpa >= 3.7:
            scenario = "🎯 Challenging but possible! Plan for dedicated study time"
        elif required_gpa >= 3.0:
            scenario = "📚 Manageable goal! Regular review sessions will help you succeed"
        else:
            scenario = "💡 On track! Continue your current study habits to reach this target"
            
        self.scenario_label.setText(scenario)
        self.results_group.setVisible(True)

    def reset_all(self):
        """Reset all inputs"""
        reply = QMessageBox.question(self, 'Reset Confirmation', 
                                'Are you sure you want to reset all inputs?',
                                QMessageBox.Yes | QMessageBox.No, 
                                QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Clear all input fields
            self.current_cgpa_input.clear()
            self.completed_credits_input.clear()
            self.target_cgpa_input.clear()
            self.future_credits_input.clear()
            
            # Hide results section
            self.results_group.setVisible(False)
            
            # Optional: Clear result labels
            self.required_gpa_label.clear()
            self.explanation_label.clear()
            self.scenario_label.clear()