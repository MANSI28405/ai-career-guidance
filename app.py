from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import io

app = Flask(__name__)
app.secret_key = "secret123"

# =========================
# DUMMY JOB DATA (SIMPLE)
# =========================
jobs_data = [
    {
        "role": "Software Engineer",
        "skills": ["python", "sql"]
    },
    {
        "role": "Machine Learning Engineer",
        "skills": ["python", "ml", "deep learning"]
    },
    {
        "role": "Backend Developer",
        "skills": ["python", "django", "flask", "sql"]
    },
    {
        "role": "Data Scientist",
        "skills": ["python", "pandas", "machine learning"]
    }
]

# =========================
# HELPER FUNCTION
# =========================
def suggest_jobs(user_input):
    user_words = user_input.lower().split()
    results = []

    for job in jobs_data:
        required = job["skills"]

        matched = [skill for skill in required if skill in user_words]
        missing = [skill for skill in required if skill not in user_words]

        match_percent = int((len(matched) / len(required)) * 100)

        roadmap = "Learn " + ", ".join(missing) + " → Build projects → Apply"

        results.append({
            "role": job["role"],
            "match": match_percent,
            "required": ", ".join(required),
            "missing": ", ".join(missing) if missing else "None",
            "roadmap": roadmap
        })

    # Sort by match %
    results.sort(key=lambda x: x["match"], reverse=True)

    return results


# =========================
# HOME → LOGIN
# =========================
@app.route("/")
def home():
    return redirect("/login")


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password),
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect("/dashboard")
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
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password),
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


# =========================
# DASHBOARD
# =========================
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    # keep previous results
    results = session.get("report", [])

    if request.method == "POST":
        skills = request.form.get("skills", "")
        interests = request.form.get("interests", "")

        user_input = skills + " " + interests

        results = suggest_jobs(user_input)

        # save for download
        session["report"] = results

    return render_template("dashboard.html", results=results)


# =========================
# DOWNLOAD REPORT
# =========================
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

    return send_file(
        buffer,
        as_attachment=True,
        download_name="report.txt",
        mimetype="text/plain"
    )


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# RUN
# =========================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)