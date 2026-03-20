
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from database import init_db, get_db, close_db
from datetime import date
import calendar
import hashlib

app = Flask(__name__)
app.secret_key = "finance_tracker_secret_2024"

# Register DB teardown so connections are closed after every request
app.teardown_appcontext(close_db)


# Auth helpers 
def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# Auth Routes 
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("register"))
        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            flash("Username already taken. Please choose another.", "error")
            return redirect(url_for("register"))
        db.execute("INSERT INTO users (username, password) VALUES (?,?)",
                   (username, hash_pw(password)))
        db.commit()
        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, hash_pw(password))
        ).fetchone()
        if user:
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# Home / Dashboard
@app.route("/")
@login_required
def index():
    db  = get_db()
    uid = session["user_id"]
    today       = date.today()
    month_start = today.replace(day=1).isoformat()

    income = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions "
        "WHERE user_id=? AND type='income' AND date >= ?",
        (uid, month_start)
    ).fetchone()[0]

    expenses = db.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions "
        "WHERE user_id=? AND type='expense' AND date >= ?",
        (uid, month_start)
    ).fetchone()[0]

    balance = income - expenses

    budgets = db.execute("SELECT * FROM budgets WHERE user_id=?", (uid,)).fetchall()
    budget_usage = []
    for b in budgets:
        spent = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE user_id=? AND category=? AND type='expense' AND date >= ?",
            (uid, b["category"], month_start)
        ).fetchone()[0]
        budget_usage.append({
            "category": b["category"],
            "limit":    b["monthly_limit"],
            "spent":    spent,
            "percent":  min(round((spent / b["monthly_limit"]) * 100, 1), 100)
                        if b["monthly_limit"] > 0 else 0
        })

    recent = db.execute(
        "SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC, id DESC LIMIT 10",
        (uid,)
    ).fetchall()

    return render_template("index.html",
                           income=income, expenses=expenses, balance=balance,
                           budget_usage=budget_usage, recent=recent,
                           today=today.isoformat())


# Transactions 
@app.route("/transactions")
@login_required
def transactions():
    db  = get_db()
    uid = session["user_id"]

    filter_cat  = request.args.get("category", "")
    filter_type = request.args.get("type", "")

    query  = "SELECT * FROM transactions WHERE user_id=?"
    params = [uid]
    if filter_cat:
        query  += " AND category=?"
        params.append(filter_cat)
    if filter_type:
        query  += " AND type=?"
        params.append(filter_type)
    query += " ORDER BY date DESC, id DESC"

    txns = db.execute(query, params).fetchall()
    categories = db.execute(
        "SELECT DISTINCT category FROM transactions WHERE user_id=? ORDER BY category",
        (uid,)
    ).fetchall()
    return render_template("transactions.html",
                           transactions=txns, categories=categories,
                           filter_cat=filter_cat, filter_type=filter_type)


@app.route("/add", methods=["POST"])
@login_required
def add_transaction():
    db       = get_db()
    uid      = session["user_id"]
    txn_type = request.form["type"]
    category = request.form["category"].strip()
    amount   = float(request.form["amount"])
    note     = request.form.get("note", "").strip()
    txn_date = request.form.get("date") or date.today().isoformat()

    if amount <= 0:
        flash("Amount must be greater than zero.", "error")
        return redirect(url_for("index"))

    db.execute(
        "INSERT INTO transactions (user_id, type, category, amount, note, date) VALUES (?,?,?,?,?,?)",
        (uid, txn_type, category, amount, note, txn_date)
    )
    db.commit()
    flash(f"{txn_type.capitalize()} of ₹{amount:.2f} added.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:txn_id>", methods=["POST"])
@login_required
def delete_transaction(txn_id):
    db  = get_db()
    uid = session["user_id"]
    db.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (txn_id, uid))
    db.commit()
    flash("Transaction deleted.", "info")
    return redirect(url_for("transactions"))


# Budgets 
@app.route("/budgets")
@login_required
def budgets():
    db  = get_db()
    uid = session["user_id"]
    all_budgets = db.execute(
        "SELECT * FROM budgets WHERE user_id=? ORDER BY category", (uid,)
    ).fetchall()
    return render_template("budgets.html", budgets=all_budgets)


@app.route("/budgets/set", methods=["POST"])
@login_required
def set_budget():
    db       = get_db()
    uid      = session["user_id"]
    category = request.form["category"].strip()
    limit    = float(request.form["limit"])
    existing = db.execute(
        "SELECT id FROM budgets WHERE user_id=? AND category=?", (uid, category)
    ).fetchone()
    if existing:
        db.execute("UPDATE budgets SET monthly_limit=? WHERE user_id=? AND category=?",
                   (limit, uid, category))
    else:
        db.execute("INSERT INTO budgets (user_id, category, monthly_limit) VALUES (?,?,?)",
                   (uid, category, limit))
    db.commit()
    flash(f"Budget for '{category}' set to ₹{limit:.2f}.", "success")
    return redirect(url_for("budgets"))


@app.route("/budgets/delete/<int:budget_id>", methods=["POST"])
@login_required
def delete_budget(budget_id):
    db  = get_db()
    uid = session["user_id"]
    db.execute("DELETE FROM budgets WHERE id=? AND user_id=?", (budget_id, uid))
    db.commit()
    flash("Budget removed.", "info")
    return redirect(url_for("budgets"))


# Charts API 
@app.route("/api/monthly-chart")
@login_required
def monthly_chart():
    db    = get_db()
    uid   = session["user_id"]
    today = date.today()
    labels, income_data, expense_data = [], [], []

    for i in range(5, -1, -1):
        year  = today.year if today.month - i > 0 else today.year - 1
        month = (today.month - i - 1) % 12 + 1
        label = f"{calendar.month_abbr[month]} {year}"
        start = f"{year}-{month:02d}-01"
        _, last_day = calendar.monthrange(year, month)
        end   = f"{year}-{month:02d}-{last_day}"

        inc = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE user_id=? AND type='income' AND date BETWEEN ? AND ?",
            (uid, start, end)
        ).fetchone()[0]
        exp = db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions "
            "WHERE user_id=? AND type='expense' AND date BETWEEN ? AND ?",
            (uid, start, end)
        ).fetchone()[0]

        labels.append(label)
        income_data.append(float(inc))
        expense_data.append(float(exp))

    return jsonify({"labels": labels, "income": income_data, "expenses": expense_data})


@app.route("/api/category-pie")
@login_required
def category_pie():
    db    = get_db()
    uid   = session["user_id"]
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    rows = db.execute(
        "SELECT category, SUM(amount) as total FROM transactions "
        "WHERE user_id=? AND type='expense' AND date >= ? "
        "GROUP BY category ORDER BY total DESC",
        (uid, month_start)
    ).fetchall()
    return jsonify({
        "labels": [r["category"] for r in rows],
        "values": [float(r["total"])  for r in rows]
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
