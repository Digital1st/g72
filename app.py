from flask import Flask, request, redirect, url_for, flash, render_template_string
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")


def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id SERIAL PRIMARY KEY,
            goal TEXT NOT NULL,
            goal_date DATE NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Goals App</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
        }
        h1, h2 { margin-bottom: 15px; }
        form { margin-bottom: 20px; }
        input, button {
            padding: 10px;
            margin: 5px 0;
        }
        input[type="text"], input[type="date"] {
            width: 280px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        table, th, td {
            border: 1px solid #ccc;
        }
        th, td {
            padding: 12px;
            text-align: left;
        }
        .actions {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .flash {
            color: green;
            margin-bottom: 15px;
        }
        .delete-form {
            display: inline;
            margin: 0;
        }
        a {
            text-decoration: none;
            color: blue;
        }
    </style>
</head>
<body>
    <h1>Goals Tracker</h1>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="flash">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <h2>Add Goal</h2>
    <form action="{{ url_for('add_goal') }}" method="POST">
        <div>
            <label>Goal</label><br>
            <input type="text" name="goal" required>
        </div>
        <div>
            <label>Date</label><br>
            <input type="date" name="goal_date" required>
        </div>
        <div>
            <button type="submit">Insert</button>
        </div>
    </form>

    <h2>All Goals</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Goal</th>
                <th>Date</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
        {% for row in goals %}
            <tr>
                <td>{{ row.id }}</td>
                <td>{{ row.goal }}</td>
                <td>{{ row.goal_date }}</td>
                <td>
                    <div class="actions">
                        <a href="{{ url_for('edit_goal', goal_id=row.id) }}">Edit</a>
                        <form class="delete-form" action="{{ url_for('delete_goal', goal_id=row.id) }}" method="POST">
                            <button type="submit" onclick="return confirm('Delete this record?')">Delete</button>
                        </form>
                    </div>
                </td>
            </tr>
        {% else %}
            <tr>
                <td colspan="4">No goals found.</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

EDIT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Edit Goal</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 700px;
            margin: 40px auto;
            padding: 20px;
        }
        input, button {
            padding: 10px;
            margin: 5px 0;
        }
        input[type="text"], input[type="date"] {
            width: 280px;
        }
        .flash {
            color: green;
            margin-bottom: 15px;
        }
        a {
            text-decoration: none;
            color: blue;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <h1>Edit Goal</h1>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}
          <div class="flash">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form method="POST">
        <div>
            <label>Goal</label><br>
            <input type="text" name="goal" value="{{ goal_item.goal }}" required>
        </div>
        <div>
            <label>Date</label><br>
            <input type="date" name="goal_date" value="{{ goal_item.goal_date }}" required>
        </div>
        <div>
            <button type="submit">Update</button>
            <a href="{{ url_for('index') }}">Back</a>
        </div>
    </form>
</body>
</html>
"""


@app.route("/")
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, goal, goal_date FROM goals ORDER BY id ASC;")
    goals = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(INDEX_HTML, goals=goals)


@app.route("/add", methods=["POST"])
def add_goal():
    goal = request.form.get("goal", "").strip()
    goal_date = request.form.get("goal_date", "").strip()

    if not goal or not goal_date:
        flash("Goal and date are required.")
        return redirect(url_for("index"))

    try:
        datetime.strptime(goal_date, "%Y-%m-%d")
    except ValueError:
        flash("Invalid date.")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO goals (goal, goal_date) VALUES (%s, %s);",
        (goal, goal_date)
    )
    conn.commit()
    cur.close()
    conn.close()

    flash("Goal added successfully.")
    return redirect(url_for("index"))


@app.route("/edit/<int:goal_id>", methods=["GET", "POST"])
def edit_goal(goal_id):
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == "POST":
        goal = request.form.get("goal", "").strip()
        goal_date = request.form.get("goal_date", "").strip()

        if not goal or not goal_date:
            flash("Goal and date are required.")
            cur.close()
            conn.close()
            return redirect(url_for("edit_goal", goal_id=goal_id))

        try:
            datetime.strptime(goal_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid date.")
            cur.close()
            conn.close()
            return redirect(url_for("edit_goal", goal_id=goal_id))

        cur.execute(
            "UPDATE goals SET goal = %s, goal_date = %s WHERE id = %s;",
            (goal, goal_date, goal_id)
        )
        conn.commit()
        cur.close()
        conn.close()

        flash("Goal updated successfully.")
        return redirect(url_for("index"))

    cur.execute("SELECT id, goal, goal_date FROM goals WHERE id = %s;", (goal_id,))
    goal_item = cur.fetchone()
    cur.close()
    conn.close()

    if not goal_item:
        flash("Goal not found.")
        return redirect(url_for("index"))

    return render_template_string(EDIT_HTML, goal_item=goal_item)


@app.route("/delete/<int:goal_id>", methods=["POST"])
def delete_goal(goal_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM goals WHERE id = %s;", (goal_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Goal deleted successfully.")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
