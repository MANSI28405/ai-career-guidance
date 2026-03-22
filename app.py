from flask import Flask, render_template, request, redirect, session, send_file
import pandas as pd
import os
import io
import re
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = "secret123"

# =========================
# DATABASE SETUP
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
# LOAD DATASET (SAFE)
# =========================
DATA_FILE = "naukri_com-job_sample.csv"

try:
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, encoding="latin1")
        df = df.dropna()
        df = df.head(1200)

        if "jobdescription" in df.columns:
            job_desc_list = df["jobdescription"].astype(str).tolist()
        else:
            job_desc_list = ["python developer", "data science"]
    else:
        job_desc_list = ["python developer", "machine learning"]

except:
    job_desc_list = ["python developer", "backend developer"]

# =========================
# LAZY MODEL LOADING (FIX 502)
# =========================
vectorizer = None
tfidf_matrix = None

def load_model():
    global vectorizer, tfidf_matrix
    if vectorizer is None:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(job_desc_list)

# =========================
# SKILLS
# =========================
SKILLS = [
    "python","java","c++","machine learning","deep learning",
    "data science","nlp","sql","html","css","javascript",
    "react","flask","django","tensorflow","pandas","numpy"
]

def extract_skills(text):
    text = str(text).lower()
    return [s for s in SKILLS if s in text]

def extract_role(text):
    text = text.lower()
    if "data scientist" in text:
        return "Data Scientist"
    elif "machine learning" in text:
        return "ML Engineer"
    elif "backend" in text:
        return "Backend Developer"
    elif "frontend" in text:
        return "Frontend Developer"
    elif "python" in text:
        return "Python Developer"
    else:
        return "Software Engineer"

def roadmap(missing):
    if not missing:
        return "Build → Practice → Apply"
    return f"Learn {', '.join(missing)} → Build → Practice → Apply"

# =========================
# AI LOGIC
# =========================
def suggest_jobs(user_input):
    load_model()

    results = []
    user_vec = vectorizer.transform([user_input])
    sim = cosine_similarity(user_vec, tfidf_matrix)

    indices = sim[0].argsort()[-10:][::-1]
    user_skills = extract_skills(user_input)

    seen = set()

    for i in indices:
        desc = job_desc_list[i]
        role = extract_role(desc)

        if role in seen:
            continue
        seen.add(role)

        job_skills = extract_skills(desc)

        match = len(set(user_skills) & set(job_skills))
        total = len(job_skills) if job_skills else 1
        percent = int((match / total) * 100)

        missing = list(set(job_skills) - set(user_skills))

        results.append({
            "role": role,
            "match": percent,
            "required": ", ".join(job_skills) or "basic",
            "missing": ", ".join(missing) or "None",
            "roadmap": roadmap(missing)
        })

    return results[:5]

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
        data = c.fetchone()
        conn.close()

        if data:
            session["user"] = user
            return redirect("/dashboard")

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
# RUN
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)