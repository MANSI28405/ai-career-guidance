from flask import Flask, render_template, request, session, jsonify
import pandas as pd
import os
import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = "secret123"

# ==============================
# LOAD DATA SAFELY (NO CRASH)
# ==============================

CSV_FILE = "naukri_com-job_sample.csv"
job_desc_list = []

try:
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE, encoding="latin1")
        df = df.dropna()

        if "jobdesc" not in df.columns:
            df["jobdesc"] = df.iloc[:, 0]

        df = df.head(1000)
        job_desc_list = df["jobdesc"].astype(str).tolist()

    else:
        raise Exception("CSV not found")

except Exception as e:
    print("⚠️ Using fallback dataset:", e)

    job_desc_list = [
        "python developer machine learning pandas numpy",
        "frontend developer html css javascript react",
        "backend developer flask django sql api",
        "data scientist python pandas numpy machine learning",
        "machine learning engineer tensorflow deep learning python"
    ]

# ==============================
# ML MODEL (SAFE)
# ==============================

vectorizer = TfidfVectorizer(stop_words="english")

if job_desc_list:
    tfidf_matrix = vectorizer.fit_transform(job_desc_list)
else:
    tfidf_matrix = None

# ==============================
# SKILLS
# ==============================

SKILLS = [
    "python","java","c++","machine learning","deep learning",
    "data science","nlp","sql","html","css","javascript",
    "react","flask","django","tensorflow","pandas","numpy"
]

# ==============================
# HELPERS
# ==============================

def clean_input(text):
    return re.sub(r'[^\w\s]', '', text.lower()).split()

def extract_skills(text):
    text = str(text).lower()
    return list(set([s for s in SKILLS if s in text]))

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
    elif "python" in text:
        return "Python Developer"
    else:
        return "Software Engineer"

def generate_roadmap(missing):
    if not missing:
        return "Build projects → Practice → Apply"
    return f"Learn {', '.join(missing)} → Build projects → Practice → Apply"

def save_results(results):
    with open("results.json", "w") as f:
        json.dump(results, f)

# ==============================
# CORE FUNCTION (SAFE)
# ==============================

def suggest_jobs(user_input):

    # 🔥 fallback safety (prevents crash)
    if not job_desc_list or tfidf_matrix is None:
        return [{
            "role": "Software Engineer",
            "score": 80,
            "required": "python, sql",
            "missing": "machine learning",
            "roadmap": "Learn ML → Build projects → Apply"
        }]

    results = []

    try:
        user_vec = vectorizer.transform([user_input])
        similarity = cosine_similarity(user_vec, tfidf_matrix)

        indices = similarity[0].argsort()[-10:][::-1]

        seen = set()

        for i in indices:

            if i >= len(job_desc_list):
                continue

            desc = job_desc_list[i]
            role = extract_job_role(desc)

            if role in seen:
                continue

            seen.add(role)

            required = extract_skills(desc)
            user_skills = clean_input(user_input)

            missing = [s for s in required if s not in user_skills]

            score = int(similarity[0][i] * 100)

            results.append({
                "role": role,
                "score": score,
                "required": ", ".join(required) if required else "None",
                "missing": ", ".join(missing) if missing else "None",
                "roadmap": generate_roadmap(missing)
            })

            if len(results) >= 5:
                break

    except Exception as e:
        print("ERROR:", e)
        return []

    save_results(results)
    return results

# ==============================
# ROUTES
# ==============================

@app.route("/", methods=["GET", "POST"])
def home():

    if 'user' not in session:
        session['user'] = "guest"

    results = None

    if request.method == "POST":
        skills = request.form.get("skills", "")
        interests = request.form.get("interests", "")

        user_input = skills + " " + interests

        results = suggest_jobs(user_input)

    return render_template("index.html", results=results)


@app.route("/download")
def download():
    if os.path.exists("results.json"):
        with open("results.json") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "No results yet"})

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)