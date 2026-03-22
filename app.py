from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import io
import os

app = Flask(__name__)
app.secret_key = "secret123"


# =========================
# DATABASE INIT (AUTO CREATE)
# =========================
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# =========================
# JOB SUGGESTION LOGIC
# =========================
def suggest_jobs(user_input):
    if not user_input.strip():
        return []

    jobs = [
        {
            "role": "Software Engineer",
            "required": "python, sql",
            "missing": "machine learning",
            "roadmap": "Learn ML → Build projects → Apply",
            "match": 80
        },
        {
            "role": "Data Scientist",
            "required": "python, pandas",
            "missing": "deep learning",
            "roadmap": "Learn DL → Practice → Apply",
            "match": 70
        },
        {
            "role": "Backend Developer",
            "required": "django, sql",
            "missing": "flask",
            "roadmap": "Learn Flask → Build APIs → Apply",
            "match": 60
        }
    ]

    jobs.sort(key=lambda x: x["match"], reverse=True)
    return jobs


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return redirect("/login")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
        result = c.fetchone()
        conn.close()

        if result:
            session["user"] = user
            return redirect("/dashboard")
        else:
            return "Invalid credentials"

    return render_template("login.html")


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pwd))
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# DASHBOARD
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    results = []

    if request.method == "POST":
        skills = request.form.get("skills", "")
        interests = request.form.get("interests", "")

        user_input = skills + " " + interests
        results = suggest_jobs(user_input)

        session["report"] = results

    return render_template("dashboard.html", results=results)


# DOWNLOAD REPORT
@app.route("/download")
def download():
    data = session.get("report", [])

    if not data:
        return "No report available"

    content = "AI Career Report\n\n"

    for job in data:
        content += f"{job['role']} ({job['match']}%)\n"
        content += f"Required: {job['required']}\n"
        content += f"Missing: {job['missing']}\n"
        content += f"Roadmap: {job['roadmap']}\n\n"

    buffer = io.BytesIO()
    buffer.write(content.encode())
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name="report.txt",
                     mimetype="text/plain")


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# RUN (RAILWAY COMPATIBLE)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)