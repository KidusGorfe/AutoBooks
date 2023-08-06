import sys
from PyQt5 import QtWidgets, QtGui, QtCore
import sqlite3
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import site
import shutil
import subprocess
import pyqtgraph as pg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter
from datetime import datetime

class AccountingSoftware(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AutoBooks - Accounting Software")
        self.setGeometry(200, 200, 1000, 600)

        # Create the "accounting" database and the "financial_data" table.
        connection = sqlite3.connect("accounting.db")
        cursor = connection.cursor()
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

        # Check if the "expense_type" column exists. If not, add it to the table.
        cursor.execute("PRAGMA table_info(financial_data)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        if "expense_type" not in column_names:
            cursor.execute("ALTER TABLE financial_data ADD COLUMN expense_type TEXT NOT NULL")

        # Remove the "data_collection" column from the table.
        if "data_collection" in column_names:
            cursor.execute("CREATE TEMPORARY TABLE financial_data_backup(id, date, revenue, expenses, expense_type, profit)")
            cursor.execute("INSERT INTO financial_data_backup SELECT id, date, revenue, expenses, expense_type, profit FROM financial_data")
            cursor.execute("DROP TABLE financial_data")
            cursor.execute("ALTER TABLE financial_data_backup RENAME TO financial_data")

        connection.commit()
        connection.close()

        self.init_ui()

        # Load existing data when the application starts
        self.update_table()

    def init_ui(self):
        # Create UI elements for data input, data table, and date range selection
        self.central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.central_widget)

        layout = QtWidgets.QVBoxLayout()
        self.central_widget.setLayout(layout)

        self.date_label = QtWidgets.QLabel("Date:")
        self.date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.revenue_label = QtWidgets.QLabel("Revenue:")
        self.revenue_entry = QtWidgets.QLineEdit()
        self.expenses_label = QtWidgets.QLabel("Expenses:")
        self.expenses_entry = QtWidgets.QLineEdit()
        self.expense_type_label = QtWidgets.QLabel("Expense Type:")
        self.expense_type_combo = QtWidgets.QComboBox()
        self.expense_type_combo.addItems(["Advertising", "Payroll", "Marketing", "Utilities", "Office Supplies", "Sales", "Inventory", "Customer Data"])
        self.save_button = QtWidgets.QPushButton("Save Data")
        self.save_button.clicked.connect(self.save_data)

        layout_input = QtWidgets.QGridLayout()
        layout_input.addWidget(self.date_label, 0, 0)
        layout_input.addWidget(self.date_edit, 0, 1)
        layout_input.addWidget(self.revenue_label, 1, 0)
        layout_input.addWidget(self.revenue_entry, 1, 1)
        layout_input.addWidget(self.expenses_label, 2, 0)
        layout_input.addWidget(self.expenses_entry, 2, 1)
        layout_input.addWidget(self.expense_type_label, 3, 0)
        layout_input.addWidget(self.expense_type_combo, 3, 1)
        layout_input.addWidget(self.save_button, 4, 0, 1, 2)

        layout.addLayout(layout_input)

        self.table_view = QtWidgets.QTableView(self)
        self.table_model = QtGui.QStandardItemModel(self)
        self.table_view.setModel(self.table_model)
        layout.addWidget(self.table_view)

        self.delete_button = QtWidgets.QPushButton("Delete Selected Row")
        self.delete_button.clicked.connect(self.delete_selected_row)
        layout.addWidget(self.delete_button)

        self.export_button = QtWidgets.QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_data_as_csv)
        layout.addWidget(self.export_button)

        # Add charts to display financial data trends over time
        self.chart_layout = QtWidgets.QVBoxLayout()
        layout.addLayout(self.chart_layout)

        self.revenue_plot = pg.PlotWidget(title="Revenue Trend")
        self.chart_layout.addWidget(self.revenue_plot)

        self.expenses_plot = pg.PlotWidget(title="Expenses Trend")
        self.chart_layout.addWidget(self.expenses_plot)

        self.profit_plot = pg.PlotWidget(title="Profit Trend")
        self.chart_layout.addWidget(self.profit_plot)

        self.show()

        # Apply custom stylesheet for visual appeal
        self.set_custom_stylesheet()

        # Set input masks for date and monetary values
        date_format = "yyyy-MM-dd"
        self.date_edit.setDisplayFormat(date_format)

        revenue_validator = QtGui.QDoubleValidator(self)
        revenue_validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        self.revenue_entry.setValidator(revenue_validator)

        expenses_validator = QtGui.QDoubleValidator(self)
        expenses_validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        self.expenses_entry.setValidator(expenses_validator)

    def set_custom_stylesheet(self):
        # (Custom stylesheet goes here...)
        pass

    def save_data(self):
        # Get the input data.
        date = self.date_edit.date().toString("yyyy-MM-dd")
        revenue_text = self.revenue_entry.text()
        expenses_text = self.expenses_entry.text()

        # Validate input fields for revenue and expenses
        if not revenue_text or not expenses_text:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please enter valid revenue and expenses values.")
            return

        try:
            revenue = float(revenue_text)
            expenses = float(expenses_text)
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please enter valid revenue and expenses values.")
            return

        expense_type = self.expense_type_combo.currentText()
        profit = revenue - expenses

        # Connect to the database and insert the data as a new entry.
        connection = sqlite3.connect("accounting.db")
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO financial_data (date, revenue, expenses, expense_type, profit)
            VALUES (?, ?, ?, ?, ?)
        """, (date, revenue, expenses, expense_type, profit))
        
        connection.commit()
        connection.close()

        # Update the table view and charts to show the updated data
        self.update_table()
        self.update_charts()

    def update_table(self):
        # Fetch data from the database and update the table view
        connection = sqlite3.connect("accounting.db")
        query = "SELECT * FROM financial_data"
        df = pd.read_sql_query(query, connection)

        # Display the data in the table view
        self.table_model.clear()
        self.table_model.setColumnCount(len(df.columns))
        self.table_model.setRowCount(len(df.index))
        self.table_model.setHorizontalHeaderLabels(df.columns)

        for row in range(len(df.index)):
            for col in range(len(df.columns)):
                item = QtGui.QStandardItem(str(df.iat[row, col]))
                self.table_model.setItem(row, col, item)

        connection.close()

    def update_charts(self):
        # Fetch data from the database and update the charts
        connection = sqlite3.connect("accounting.db")
        query = "SELECT date, revenue, expenses, profit FROM financial_data"
        df = pd.read_sql_query(query, connection)

        # Convert date strings to datetime objects for plotting
        df["date"] = pd.to_datetime(df["date"])

        # Revenue Trend
        self.revenue_plot.clear()
        self.revenue_plot.plot(df["date"], df["revenue"], pen=pg.mkPen(color="b", width=2))
        self.revenue_plot.setTitle("Revenue Trend")
        self.revenue_plot.setLabel("bottom", text="Date")
        self.revenue_plot.setLabel("left", text="Revenue")

        # Expenses Trend
        self.expenses_plot.clear()
        self.expenses_plot.plot(df["date"], df["expenses"], pen=pg.mkPen(color="r", width=2))
        self.expenses_plot.setTitle("Expenses Trend")
        self.expenses_plot.setLabel("bottom", text="Date")
        self.expenses_plot.setLabel("left", text="Expenses")

        # Profit Trend
        self.profit_plot.clear()
        self.profit_plot.plot(df["date"], df["profit"], pen=pg.mkPen(color="g", width=2))
        self.profit_plot.setTitle("Profit Trend")
        self.profit_plot.setLabel("bottom", text="Date")
        self.profit_plot.setLabel("left", text="Profit")

        connection.close()

    def delete_selected_row(self):
        selected_row = self.table_view.currentIndex().row()
        if selected_row >= 0:
            # Get the ID of the selected row from the database
            connection = sqlite3.connect("accounting.db")
            cursor = connection.cursor()
            query = "SELECT id FROM financial_data"
            result = cursor.execute(query).fetchall()
            row_id = result[selected_row][0]

            # Delete the selected row from the database
            cursor.execute("DELETE FROM financial_data WHERE id=?", (row_id,))
            connection.commit()
            connection.close()

            # Update the table view and charts to reflect the changes
            self.update_table()
            self.update_charts()

    def export_data_as_csv(self):
        # Get the date range from the user
        date_dialog = DateRangeDialog(self)
        if date_dialog.exec_():
            start_date = date_dialog.start_date.date().toString("yyyy-MM-dd")
            end_date = date_dialog.end_date.date().toString("yyyy-MM-dd")

            # Connect to the database and fetch data within the given date range.
            connection = sqlite3.connect("accounting.db")
            query = f"SELECT * FROM financial_data WHERE date BETWEEN '{start_date}' AND '{end_date}'"
            df = pd.read_sql_query(query, connection)

            # Export data to a CSV file.
            df.to_csv("financial_data.csv", index=False)

            connection.close()

    def closeEvent(self, event):
        # Show confirmation dialog before closing the application
        reply = QtWidgets.QMessageBox.question(self, 'Confirm Exit', 'Are you sure you want to exit?', QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

# Dialog for selecting date range
class DateRangeDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(DateRangeDialog, self).__init__(parent)

        self.setWindowTitle("Select Date Range")
        self.resize(300, 150)

        layout = QtWidgets.QVBoxLayout()

        self.start_date_label = QtWidgets.QLabel("Start Date:")
        self.start_date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.end_date_label = QtWidgets.QLabel("End Date:")
        self.end_date_edit = QtWidgets.QDateEdit(QtCore.QDate.currentDate())

        layout.addWidget(self.start_date_label)
        layout.addWidget(self.start_date_edit)
        layout.addWidget(self.end_date_label)
        layout.addWidget(self.end_date_edit)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        self.setLayout(layout)

    @property
    def start_date(self):
        return self.start_date_edit.date()

    @property
    def end_date(self):
        return self.end_date_edit.date()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = AccountingSoftware()
    sys.exit(app.exec_())
