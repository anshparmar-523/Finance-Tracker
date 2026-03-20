# Personal Finance Tracker

A full-stack web application built with **Flask + SQLite** for tracking income and expenses, setting monthly budgets, and visualising spending trends through interactive charts.

## Features

- **User accounts** — register, log in, log out; each user sees only their own data
- Add income and expense transactions with category, amount, date, and note
- **Filter transactions** by category and type via dropdown
- Monthly **income vs expenses** bar chart (last 6 months)
- **Expense breakdown** doughnut chart by category
- **Budget tracker** with progress bars showing % of monthly limit used
- Full transaction history with delete support
- Seed data + demo account included — works out of the box

## Tech Stack

`Python` · `Flask` · `SQLite` · `HTML5` · `CSS3` · `JavaScript` · `Chart.js`

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The SQLite database (`finance.db`) is auto-created on first run with sample data.

**Demo account:** username `demo` / password `demo123`

## Project Structure

```
finance_tracker/
├── app.py              # Flask routes, auth, API endpoints
├── database.py         # DB init, schema (users/transactions/budgets), seed data
├── requirements.txt
└── templates/
    ├── base.html           # Layout, nav, styles
    ├── login.html          # Login page
    ├── register.html       # Registration page
    ├── index.html          # Dashboard — charts, quick-add, budget progress
    ├── transactions.html   # Full history with category/type filter
    └── budgets.html        # Set and manage monthly budgets
```
