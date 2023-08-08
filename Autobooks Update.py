import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import sqlite3
import pandas as pd
import os

if os.path.exists("accounting.db"):
    os.remove("accounting.db")
else:
    print("The file does not exist.")

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QTableWidgetItem, QHeaderView
from datetime import date

class AccountingSoftware(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        # UI initialization
        self.setWindowTitle("AutoBooks - Advanced Accounting Software")
        self.setGeometry(200, 200, 1200, 800)
        self.setStyleSheet("background-color: #D7EAF5;")
        self.init_ui()
        self.init_db()
        self.update_table()

    def init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        
        # Entry UI components
        entry_group = QtWidgets.QGroupBox("Data Entry")
        entry_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        entry_layout = QtWidgets.QGridLayout()

        self.date_label = QtWidgets.QLabel("Date:")
        self.date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.revenue_label = QtWidgets.QLabel("Revenue:")
        self.revenue_entry = QtWidgets.QDoubleSpinBox()
        self.revenue_entry.setRange(0, 9999999)
        self.expenses_label = QtWidgets.QLabel("Expenses:")
        self.expenses_entry = QtWidgets.QDoubleSpinBox()
        self.expenses_entry.setRange(0, 9999999)
        self.expense_type_label = QtWidgets.QLabel("Expense Type:")
        self.expense_type_combo = QtWidgets.QComboBox()
        self.expense_type_combo.addItems(["Advertising", "Payroll", "Rent", "Utilities", "Inventory", "Car Purchase"])
        self.save_button = QtWidgets.QPushButton("Save Data")
        self.save_button.clicked.connect(self.save_data)
        self.export_button = QtWidgets.QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        self.delete_button = QtWidgets.QPushButton("Delete Selected Row")
        self.delete_button.clicked.connect(self.delete_row)

        entry_layout.addWidget(self.date_label, 0, 0)
        entry_layout.addWidget(self.date_edit, 0, 1)
        entry_layout.addWidget(self.revenue_label, 1, 0)
        entry_layout.addWidget(self.revenue_entry, 1, 1)
        entry_layout.addWidget(self.expenses_label, 2, 0)
        entry_layout.addWidget(self.expenses_entry, 2, 1)
        entry_layout.addWidget(self.expense_type_label, 3, 0)
        entry_layout.addWidget(self.expense_type_combo, 3, 1)
        entry_layout.addWidget(self.save_button, 4, 0, 1, 2)
        entry_layout.addWidget(self.export_button, 5, 0, 1, 2)
        entry_layout.addWidget(self.delete_button, 6, 0, 1, 2)
        
        entry_group.setLayout(entry_layout)

        # Data display table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Revenue", "Expenses", "Expense Type", "Profit"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Add components to the main layout
        layout.addWidget(entry_group)
        layout.addWidget(self.table)

        main_widget = QtWidgets.QWidget()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def init_db(self):
        # Create the "accounting" database and the "financial_data" table.
        self.connection = sqlite3.connect("accounting.db")
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_data (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                revenue REAL NOT NULL,
                expenses REAL NOT NULL,
                expense_type TEXT NOT NULL,
                profit REAL NOT NULL
            )
        """)
        self.connection.commit()

    def save_data(self):
        # Check if revenue and expenses fields are filled
        if not self.revenue_entry.value() and not self.expenses_entry.value():
            self.show_message("Error", "Please enter at least revenue or expenses data.")
            return

        profit = self.revenue_entry.value() - self.expenses_entry.value()
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO financial_data (date, revenue, expenses, expense_type, profit) VALUES (?, ?, ?, ?, ?)", 
                       (self.date_edit.date().toString(QtCore.Qt.ISODate), self.revenue_entry.value(), self.expenses_entry.value(),
                        self.expense_type_combo.currentText(), profit))
        self.connection.commit()
        self.update_table()

    def update_table(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT date, revenue, expenses, expense_type, profit FROM financial_data")
        data = cursor.fetchall()
        
        self.table.setRowCount(0)
        for row_number, row_data in enumerate(data):
            self.table.insertRow(row_number)
            for column_number, column_data in enumerate(row_data):
                self.table.setItem(row_number, column_number, QTableWidgetItem(str(column_data)))

    def export_data(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM financial_data")
        data = cursor.fetchall()
        df = pd.DataFrame(data, columns=["ID", "Date", "Revenue", "Expenses", "Expense Type", "Profit"])
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv);;All Files (*)")
        if path:
            df.to_csv(path, index=False)

    def delete_row(self):
        row = self.table.currentRow()
        if row != -1:
            cell_value = self.table.item(row, 0).text()
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM financial_data WHERE date=?", (cell_value,))
            self.connection.commit()
            self.update_table()
        else:
            self.show_message("Error", "Please select a row to delete.")

    def show_message(self, title, message):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(title)
        dlg.setText(message)
        dlg.setIcon(QMessageBox.Information)
        dlg.show()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = AccountingSoftware()
    window.show()
    sys.exit(app.exec_())

