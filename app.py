from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"

# =========================
# DATABASE
# =========================
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# =========================
# CLEAN INPUT
# =========================
def clean_input(text):
    return text.lower().replace(",", " ").split()

# =========================
# ROADMAP GENERATOR
# =========================
def generate_roadmap(role, missing):
    if not missing:
        return "Build advanced projects → Practice → Apply"
    return f"Learn {', '.join(missing)} → Build projects → Practice → Apply"

# =========================
# JOB SUGGESTION LOGIC (FINAL)
# =========================
def suggest_jobs(user_input):
    user_skills = clean_input(user_input)

    roles = {
        "Data Scientist": ["python", "machine", "learning", "data", "pandas"],
        "Machine Learning Engineer": ["python", "ml", "deep", "learning"],
        "Backend Developer": ["python", "django", "flask", "sql"],
        "Frontend Developer": ["html", "css", "javascript", "react"],
        "Software Engineer": ["java", "c++", "coding", "problem"],
    }

    results = []

    for role, skills in roles.items():
        matched = [s for s in user_skills if s in skills]
        score = int((len(matched) / len(skills)) * 100)

        missing = [s for s in skills if s not in user_skills]

        if score > 0:
            results.append({
                "role": role,
                "score": score,
                "required": ", ".join(skills),
                "missing": ", ".join(missing),
                "roadmap": generate_roadmap(role, missing)
            })

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return results[:4]

# =========================
# ROUTES
# =========================

@app.route("/", methods=["GET", "POST"])
def home():
    if 'user' not in session:
        return redirect("/login")

    results = None

    if request.method == "POST":
        try:
            skills = request.form.get("skills", "")
            interests = request.form.get("interests", "")

            user_input = skills + " " + interests

            results = suggest_jobs(user_input)
        except Exception as e:
            print("ERROR:", e)
            results = []

    return render_template("index.html", results=results)

# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect("/")
        else:
            return "Invalid Credentials"

    return render_template("login.html")

# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")

# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect("/login")

# =========================
# RUN (IMPORTANT FOR RAILWAY)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)