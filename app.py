from flask import Flask, render_template, request, redirect, session, send_file
import pandas as pd
import os
import io
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = "secret123"

# =========================
# LOAD DATASET SAFELY
# =========================
DATA_FILE = "naukri_com-job_sample.csv"

if os.path.exists(DATA_FILE):
    df = pd.read_csv(DATA_FILE, encoding="latin1")
    df = df.dropna()
    df = df.head(2000)
    job_desc_list = df["jobdescription"].astype(str).tolist()
else:
    print("⚠️ CSV FILE NOT FOUND")
    job_desc_list = ["python developer job", "machine learning engineer job"]

# =========================
# TF-IDF MODEL
# =========================
vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = vectorizer.fit_transform(job_desc_list)

# =========================
# SKILLS LIST
# =========================
SKILLS = [
    "python","java","c++","machine learning","deep learning",
    "data science","nlp","sql","html","css","javascript",
    "react","flask","django","tensorflow","pandas","numpy"
]

# =========================
# CLEAN INPUT
# =========================
def clean_input(text):
    return re.sub(r"[^\w\s]", "", text.lower()).split()

# =========================
# EXTRACT SKILLS
# =========================
def extract_skills(text):
    text = str(text).lower()
    found = [s for s in SKILLS if s in text]
    return list(set(found)) if found else []

# =========================
# DETECT ROLE
# =========================
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

# =========================
# ROADMAP GENERATOR
# =========================
def generate_roadmap(missing):
    if not missing:
        return "Build projects → Practice → Apply"
    return f"Learn {', '.join(missing)} → Build projects → Practice → Apply"

# =========================
# MAIN LOGIC
# =========================
def suggest_jobs(user_input):
    results = []

    try:
        user_vec = vectorizer.transform([user_input])
        similarity = cosine_similarity(user_vec, tfidf_matrix)

        indices = similarity[0].argsort()[-10:][::-1]
        user_skills = extract_skills(user_input)

        seen = set()

        for i in indices:
            if i >= len(job_desc_list):
                continue

            desc = job_desc_list[i]
            role = extract_job_role(desc)

            if role in seen:
                continue
            seen.add(role)

            job_skills = extract_skills(desc)

            matched = len(set(user_skills) & set(job_skills))
            total = len(job_skills) if job_skills else 1
            match_percent = int((matched / total) * 100)

            missing = list(set(job_skills) - set(user_skills))

            results.append({
                "role": role,
                "match": match_percent,
                "required": ", ".join(job_skills) if job_skills else "basic skills",
                "missing": ", ".join(missing) if missing else "None",
                "roadmap": generate_roadmap(missing)
            })

        return results[:5]

    except Exception as e:
        print("ERROR:", e)
        return []

# =========================
# ROUTES
# =========================

@app.route("/", methods=["GET", "POST"])
def index():
    results = []

    if request.method == "POST":
        skills = request.form.get("skills", "")
        interests = request.form.get("interests", "")

        user_input = skills + " " + interests

        results = suggest_jobs(user_input)

        session["report"] = results  # save for download

    return render_template("index.html", results=results)

# =========================
# DOWNLOAD REPORT (FIXED)
# =========================
@app.route("/download")
def download_report():
    try:
        results = session.get("report", [])

        if not results:
            return "No data available to download"

        content = "AI Career Guidance Report\n\n"

        for job in results:
            content += f"Role: {job['role']}\n"
            content += f"Match: {job['match']}%\n"
            content += f"Required Skills: {job['required']}\n"
            content += f"Missing Skills: {job['missing']}\n"
            content += f"Roadmap: {job['roadmap']}\n"
            content += "-"*40 + "\n"

        buffer = io.BytesIO()
        buffer.write(content.encode())
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="career_report.txt",
            mimetype="text/plain"
        )

    except Exception as e:
        return str(e)

# =========================
# RUN (RAILWAY SAFE)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)