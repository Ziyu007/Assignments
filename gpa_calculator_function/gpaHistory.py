from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton, QStackedWidget)
from PyQt5.QtCore import Qt
from datetime import datetime
from styles.gpa_styles import gpa_styles
from gpa_calculator_function.historyDetails import GPAHistoryDetails

class GPAHistory(QWidget):
    def __init__(self, parent, history_data, previous_page, from_calculator=False):
        super().__init__()
        self.parent = parent  # This is GPACalculatorWidget
        self.history_data = history_data
        self.previous_page = previous_page  # This should be the calculator's feature grid page
        self.from_calculator = from_calculator  # Flag to track where we came from
        
        self.setStyleSheet(gpa_styles())
        
        # Create a local stacked widget for history navigation
        self.history_stack = QStackedWidget()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add the history stack to layout
        layout.addWidget(self.history_stack)
        
        # Show the table view initially
        self.show_table_view()

    def show_table_view(self):
        """Show the main history table"""
        # Clear existing table widget if it exists
        if hasattr(self, 'table_widget'):
            self.history_stack.removeWidget(self.table_widget)
            self.table_widget.deleteLater()
        
        self.table_widget = QWidget()
        table_layout = QVBoxLayout(self.table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("GPA Calculation History")
        title.setObjectName("gpaHeader")
        table_layout.addWidget(title)
        
        if not self.history_data:
            no_data_label = QLabel("No history found.")
            no_data_label.setAlignment(Qt.AlignCenter)
            table_layout.addWidget(no_data_label)
        else:
            # Table setup
            self.table = QTableWidget()
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels([
                "Date", "Semester\nCredits", "Semester\nGPA", "Total\nCredits", "Current\nCGPA", "Previous\nCGPA", "Actions"
            ])
            
            # Enable word wrap for headers and content
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table.verticalHeader().setVisible(False)
            
            # Set word wrap for all items
            self.table.setWordWrap(True)
            
            # Populate table
            for i, record in enumerate(self.history_data):
                self.table.insertRow(i)
                date_obj = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                
                # Create items with word wrap enabled
                date_item = QTableWidgetItem(date_str)
                date_item.setTextAlignment(Qt.AlignLeft)
                
                credits_item = QTableWidgetItem(str(record['semester_credits']))
                credits_item.setTextAlignment(Qt.AlignCenter)
                
                gpa_item = QTableWidgetItem(f"{record['gpa']:.2f}")
                gpa_item.setTextAlignment(Qt.AlignCenter)
                
                total_credits_item = QTableWidgetItem(str(record['total_credits']))
                total_credits_item.setTextAlignment(Qt.AlignCenter)
                
                cgpa_item = QTableWidgetItem(f"{record['cgpa']:.2f}")
                cgpa_item.setTextAlignment(Qt.AlignCenter)
                
                prev_cgpa_text = f"{record['current_cgpa']:.2f} ({record['completed_credits']} credits)"
                prev_cgpa_item = QTableWidgetItem(prev_cgpa_text)
                prev_cgpa_item.setTextAlignment(Qt.AlignLeft)
                
                # Set items to the table
                self.table.setItem(i, 0, date_item)
                self.table.setItem(i, 1, credits_item)
                self.table.setItem(i, 2, gpa_item)
                self.table.setItem(i, 3, total_credits_item)
                self.table.setItem(i, 4, cgpa_item)
                self.table.setItem(i, 5, prev_cgpa_item)
                
                view_btn = QPushButton("Details")
                view_btn.setObjectName("detailsButton")
                view_btn.setCursor(Qt.PointingHandCursor) 
                view_btn.clicked.connect(lambda checked, r=record: self.view_details(r))
                self.table.setCellWidget(i, 6, view_btn)

            # Enable word wrapping and resize rows to fit content
            self.table.setWordWrap(True)
            self.table.resizeRowsToContents()
            
            # Set row height policy to ensure all content is visible
            self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

            self.table.setEditTriggers(QTableWidget.NoEditTriggers)
            self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table_layout.addWidget(self.table)
        
        # Add table widget to stack if not already added
        for i in range(self.history_stack.count()):
            if self.history_stack.widget(i) == self.table_widget:
                break
        else:
            self.history_stack.addWidget(self.table_widget)
        
        self.history_stack.setCurrentWidget(self.table_widget)
        
        # When on table view, back button should go to calculator's feature grid
        self.setup_table_view_back_button()

    def setup_table_view_back_button(self):
        """Setup back button to go to calculator's feature grid when on table view"""
        back_button = self.find_back_button()
        if back_button:
            # Disconnect any existing connections
            try:
                back_button.clicked.disconnect()
            except:
                pass
            
            # Connect to go back to calculator's feature grid
            back_button.clicked.connect(self.go_to_calculator_grid)

    def go_to_calculator_grid(self):
        """Go back to either calculator page or feature grid based on origin"""
        if self.from_calculator:
            # Came from calculator page - go back to calculator page
            self.parent.pages.setCurrentWidget(self.previous_page)
            # Restore back button state for calculator page
            if hasattr(self.parent, 'restore_back_button_state'):
                self.parent.restore_back_button_state()
        else:
            # Came from feature grid - go back to feature grid
            # Restore the back button state first
            if hasattr(self.parent, 'restore_back_button_state'):
                self.parent.restore_back_button_state()
            self.parent.pages.setCurrentWidget(self.parent.feature_grid_page)

    def view_details(self, record):
        """Show details for a specific record"""
        # Create details page
        details_page = GPAHistoryDetails(self, record)
        
        # Add to history stack
        self.history_stack.addWidget(details_page)
        self.history_stack.setCurrentWidget(details_page)
        
        # Update back button to handle history navigation
        self.setup_details_back_button()

    def setup_details_back_button(self):
        """Configure back button for history details navigation"""
        back_button = self.find_back_button()
        if back_button:
            # Disconnect any existing connections
            try:
                back_button.clicked.disconnect()
            except:
                pass
            
            # Connect to history back handler
            back_button.clicked.connect(self.handle_details_back)

    def handle_details_back(self):
        """Handle back navigation from details to table view"""
        # Go back to table view from details
        self.history_stack.setCurrentWidget(self.table_widget)
        
        # Remove the details page from stack
        current_widget = self.history_stack.currentWidget()
        if current_widget != self.table_widget:
            self.history_stack.removeWidget(current_widget)
            current_widget.deleteLater()
        
        # Setup back button to go to calculator grid again
        self.setup_table_view_back_button()

    def find_back_button(self):
        """Find the back button in the parent widget"""
        # Check common back button attribute names
        if hasattr(self.parent, 'back_btn'):
            return self.parent.back_btn
        elif hasattr(self.parent, 'back_button'):
            return self.parent.back_button
        elif hasattr(self.parent, 'btn_back'):
            return self.parent.btn_back
        else:
            # If no back button found, search in children
            for child in self.parent.findChildren(QPushButton):
                if 'back' in child.text().lower() or 'back' in child.objectName().lower():
                    return child
            return None

    def refresh_data(self, new_history_data, from_calculator=False):
        """Refresh with new data and update origin flag"""
        self.history_data = new_history_data
        self.from_calculator = from_calculator
        self.show_table_view() # Rebuild the table view
