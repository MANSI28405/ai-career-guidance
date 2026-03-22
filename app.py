from flask import Flask, render_template, request, redirect, session
import sqlite3
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os

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
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# LOAD DATASET
# =========================

df = pd.read_csv("naukri_com-job_sample.csv", encoding="latin1")

# Clean + reset index (IMPORTANT FIX)
df = df.dropna().reset_index(drop=True)
df = df.head(2000).reset_index(drop=True)

# Extract job descriptions safely
job_desc_column = df.iloc[:, 4].astype(str)

# Remove empty rows
job_desc_column = job_desc_column[job_desc_column.str.strip() != ""]

# Fallback if empty
if job_desc_column.empty:
    job_desc_column = pd.Series(["python data science machine learning"])

vectorizer = TfidfVectorizer(stop_words='english')
tfidf_matrix = vectorizer.fit_transform(job_desc_column)

# =========================
# SKILLS LIST
# =========================

SKILLS = [
    "python","java","c++","machine learning","deep learning",
    "data science","nlp","sql","html","css","javascript",
    "react","flask","django","tensorflow","pandas","numpy"
]

def clean_input(text):
    return re.sub(r'[,]+', ' ', text.lower()).split()

def extract_skills(text):
    text = str(text).lower()
    found = [s for s in SKILLS if s in text]
    return list(set(found)) if found else ["Not specified"]

def extract_job_role(text):
    text = str(text).lower()

    if "data scientist" in text:
        return "Data Scientist"
    elif "machine learning" in text:
        return "Machine Learning Engineer"
    elif "backend" in text:
        return "Backend Developer"
    elif "frontend" in text:
        return "Frontend Developer"
    elif "python developer" in text:
        return "Python Developer"
    else:
        return "Software Engineer"

def generate_roadmap(role, missing):
    if missing == ["None"]:
        return "Build advanced projects → Practice → Apply"
    return f"Learn {', '.join(missing)} → Build projects → Practice → Apply"

# =========================
# JOB SUGGESTION
# =========================

def suggest_jobs(user_input):
    results = []

    user_vec = vectorizer.transform([user_input])
    similarity = cosine_similarity(user_vec, tfidf_matrix)

    indices = similarity[0].argsort()[-30:][::-1]
    user_skills = clean_input(user_input)

    seen = set()

    for i in indices:
        try:
            desc = str(df.iloc[i, 4])  # SAFE ACCESS
        except:
            continue

        role = extract_job_role(desc)

        if role in seen:
            continue
        seen.add(role)

        required = extract_skills(desc)

        matched = len([s for s in required if s in user_skills])
        total = len(required) if required else 1

        score = int(min(95, (matched/total)*100 + 40))

        missing = [s for s in required if s not in user_skills]

        results.append({
            "role": role,
            "match": score,
            "skills": required,
            "missing": missing if missing else ["None"],
            "roadmap": generate_roadmap(role, missing if missing else ["None"])
        })

        if len(results) == 5:
            break

    return results

# =========================
# AUTH ROUTES
# =========================

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if len(password) < 5:
            return "Password must be at least 5 characters"

        try:
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("INSERT INTO users (username,password) VALUES (?,?)",(username,password))
            conn.commit()
            conn.close()
            return redirect('/login')
        except:
            return "User already exists"

    return render_template('register.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?",(username,password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            return "Invalid credentials"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# =========================
# MAIN PAGE
# =========================

@app.route('/', methods=['GET','POST'])
def home():

    if 'user' not in session:
        return redirect('/login')

    results = None

    if request.method == 'POST':
        skills = request.form['skills']
        interests = request.form['interests']

        user_input = skills + " " + interests
        results = suggest_jobs(user_input)

    return render_template('index.html', results=results)

# =========================
# RUN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)