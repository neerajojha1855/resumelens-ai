# ResumeLens — AI-Powered Resume Screening Platform

![ResumeLens](https://img.shields.io/badge/Status-Active-brightgreen) ![Python 3.12](https://img.shields.io/badge/Python-3.12-blue) ![Django 6.0](https://img.shields.io/badge/Django-6.0-092E20?logo=django) ![Tailwind CSS v4](https://img.shields.io/badge/Tailwind_CSS-v4-38B2AC?logo=tailwind-css)

**ResumeLens** is an intelligent resume screening tool designed to help applicants optimize their resumes for Applicant Tracking Systems (ATS) and discover their best-fit careers. By analyzing resumes using natural language processing (NLP), it provides actionable feedback, career path alignment, and upskilling recommendations.

## ✨ Features

- 🎯 **ATS Compatibility Scoring:** Get a detailed breakdown of how well your resume is formatted, along with actionable improvements for impact verbs and quantifiable metrics.
- 🧠 **Smart Skill Extraction:** Automatically detects and categorizes your technical, soft, and industry-specific skills.
- 💼 **Career Fit Analysis:** Matches your extracted skill profile against real-world job requirements to suggest the roles you are most qualified for.
- 🎓 **Targeted Upskilling:** Identifies gaps in your skill set for your target roles and recommends the exact courses/certifications needed to bridge them.
- 🎨 **Premium UI/UX:** A stunning, fully responsive dark-mode interface built with Tailwind CSS v4, featuring glassmorphism elements and micro-animations.

## 🛠️ Tech Stack

- **Backend:** Python, Django 6
- **Frontend:** HTML, Django Templates, Vanilla JavaScript
- **Styling:** Tailwind CSS v4 (via `django-tailwind`)
- **NLP & Parsing:** `spaCy`, `NLTK`, `PyMuPDF`, `python-docx`
- **Database:** SQLite (Local) / PostgreSQL (Production)
- **Deployment:** Render (via Infrastructure as Code Blueprint)

---

## 🚀 Local Development Setup

To run ResumeLens locally, follow these steps:

### 1. Clone the repository
```bash
git clone https://github.com/neerajojha1855/resumelens-ai.git
cd resumelens-ai
```

### 2. Set up the Python virtual environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Node.js dependencies for Tailwind
*Note: Make sure you have Node.js installed.*
```bash
cd theme/static_src
npm install
cd ../..
```

### 5. Run Database Migrations
```bash
python manage.py migrate
```

### 6. Start the Development Servers
You will need two terminal windows running simultaneously.

**Terminal 1 (Django Server):**
```bash
python manage.py runserver
```

**Terminal 2 (Tailwind Watcher):**
```bash
python manage.py tailwind start
```

Visit `http://localhost:8000` in your browser!

---

## ☁️ Deployment (Render)

ResumeLens is pre-configured for automated deployment on [Render](https://render.com/) using Infrastructure as Code (Blueprint).

1. Go to your Render Dashboard.
2. Click **New** -> **Blueprint**.
3. Connect this GitHub repository.
4. Render will automatically detect the `render.yaml` file and provision:
   - A PostgreSQL Database.
   - A Web Service that automatically runs `build.sh` (installs dependencies, builds Tailwind CSS, and applies migrations).
   - Secure environment variables (auto-generating `SECRET_KEY` and linking `DATABASE_URL`).

---

## 👨‍💻 Developer

**Neeraj Ojha**
- **Portfolio:** [https://portfolio-neeraj-puce.vercel.app/](https://portfolio-neeraj-puce.vercel.app/)
- **GitHub:** [@neerajojha1855](https://github.com/neerajojha1855)