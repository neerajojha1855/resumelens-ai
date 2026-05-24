"""
ResumeLens — NLP Resume Analysis Engine
Parsing, ATS scoring, job matching, and course recommendation utilities.
"""

import re
import os
import tempfile
import json
import logging
from collections import Counter
import requests

logger = logging.getLogger(__name__)

# ─── PDF / DOCX Extraction ────────────────────────────────────────────────────

def extract_text_from_pdf(file_obj):
    """Extract text from an uploaded PDF file using PyMuPDF."""
    import fitz  # PyMuPDF

    # Write the uploaded file to a temp file so fitz can open it
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        for chunk in file_obj.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    finally:
        os.unlink(tmp_path)


def extract_text_from_docx(file_obj):
    """Extract text from an uploaded DOCX file."""
    from docx import Document

    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
        for chunk in file_obj.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        doc = Document(tmp_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    finally:
        os.unlink(tmp_path)


def extract_text(file_obj):
    """Route to the correct extractor based on file extension."""
    name = file_obj.name.lower()
    if name.endswith('.pdf'):
        return extract_text_from_pdf(file_obj)
    elif name.endswith('.docx') or name.endswith('.doc'):
        return extract_text_from_docx(file_obj)
    else:
        raise ValueError("Unsupported file format. Please upload a PDF or DOCX file.")


# ─── Skill Taxonomy ───────────────────────────────────────────────────────────

SKILL_CATEGORIES = {
    "Programming Languages": [
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
        "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
        "dart", "lua", "haskell", "elixir", "clojure", "objective-c",
    ],
    "Web Development": [
        "html", "css", "react", "angular", "vue", "next.js", "nuxt.js",
        "node.js", "express.js", "django", "flask", "fastapi", "spring boot",
        "asp.net", "rails", "laravel", "svelte", "tailwind", "bootstrap",
        "jquery", "webpack", "vite", "graphql", "rest api", "websocket",
    ],
    "Data Science & ML": [
        "machine learning", "deep learning", "tensorflow", "pytorch", "keras",
        "scikit-learn", "pandas", "numpy", "scipy", "matplotlib", "seaborn",
        "nlp", "natural language processing", "computer vision", "opencv",
        "data analysis", "data visualization", "jupyter", "tableau", "power bi",
        "statistics", "regression", "classification", "clustering",
        "neural networks", "transformers", "llm", "generative ai",
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
        "terraform", "ansible", "jenkins", "ci/cd", "github actions",
        "gitlab ci", "linux", "nginx", "apache", "serverless", "lambda",
        "cloudformation", "helm", "prometheus", "grafana", "elk stack",
    ],
    "Databases": [
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "cassandra", "dynamodb", "firebase", "sqlite", "oracle", "neo4j",
        "supabase", "prisma", "sequelize", "sqlalchemy",
    ],
    "Mobile Development": [
        "react native", "flutter", "swift", "swiftui", "kotlin", "android",
        "ios", "xamarin", "ionic", "expo",
    ],
    "Tools & Practices": [
        "git", "github", "gitlab", "bitbucket", "jira", "confluence",
        "agile", "scrum", "kanban", "tdd", "unit testing", "integration testing",
        "code review", "pair programming", "figma", "sketch", "adobe xd",
    ],
    "Soft Skills": [
        "leadership", "communication", "teamwork", "problem solving",
        "critical thinking", "project management", "time management",
        "presentation", "mentoring", "collaboration", "strategic planning",
    ],
}

# Flatten for quick lookup
ALL_SKILLS = {}
for category, skills in SKILL_CATEGORIES.items():
    for skill in skills:
        ALL_SKILLS[skill] = category


# ─── Action Verbs ──────────────────────────────────────────────────────────────

ACTION_VERBS = [
    "achieved", "administered", "analyzed", "architected", "automated",
    "built", "championed", "collaborated", "conducted", "configured",
    "created", "debugged", "delivered", "deployed", "designed", "developed",
    "directed", "drove", "enabled", "engineered", "enhanced", "established",
    "evaluated", "executed", "expanded", "facilitated", "formulated",
    "generated", "grew", "guided", "headed", "identified", "implemented",
    "improved", "increased", "initiated", "innovated", "integrated",
    "introduced", "launched", "led", "leveraged", "maintained", "managed",
    "mentored", "migrated", "modernized", "monitored", "negotiated",
    "optimized", "orchestrated", "organized", "overhauled", "oversaw",
    "performed", "pioneered", "planned", "presented", "produced",
    "programmed", "proposed", "published", "reduced", "refactored",
    "reformed", "resolved", "restructured", "revamped", "scaled",
    "simplified", "spearheaded", "standardized", "streamlined",
    "strengthened", "supervised", "supported", "tested", "trained",
    "transformed", "troubleshot", "unified", "upgraded", "utilized",
]

# ─── Resume Section Detection ─────────────────────────────────────────────────

SECTION_PATTERNS = {
    "education": r"(?i)\b(education|academic|qualification|degree|university|college|school)\b",
    "experience": r"(?i)\b(experience|employment|work\s*history|professional\s*experience|career)\b",
    "skills": r"(?i)\b(skills|technical\s*skills|competencies|proficiencies|technologies|tech\s*stack)\b",
    "projects": r"(?i)\b(projects|portfolio|personal\s*projects|key\s*projects)\b",
    "certifications": r"(?i)\b(certifications?|certificates?|licenses?|accreditations?)\b",
    "summary": r"(?i)\b(summary|objective|profile|about\s*me|professional\s*summary)\b",
}


# ─── Resume Parser ─────────────────────────────────────────────────────────────

def parse_resume(text):
    """
    Parse resume text and extract structured data:
    - contact info (email, phone, linkedin)
    - detected sections
    - skills (matched against taxonomy)
    - action verbs used
    - quantifiable metrics
    """
    text_lower = text.lower()
    lines = text.strip().split('\n')

    # ── Contact Info ──
    email_match = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    phone_match = re.findall(r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\./0-9]{7,15}', text)
    linkedin_match = re.findall(r'(?:linkedin\.com/in/|linkedin:\s*)([a-zA-Z0-9\-_]+)', text, re.I)
    github_match = re.findall(r'(?:github\.com/|github:\s*)([a-zA-Z0-9\-_]+)', text, re.I)

    contact = {
        "email": email_match[0] if email_match else None,
        "phone": phone_match[0].strip() if phone_match else None,
        "linkedin": linkedin_match[0] if linkedin_match else None,
        "github": github_match[0] if github_match else None,
    }

    # ── Sections Detected ──
    sections_found = {}
    for section_name, pattern in SECTION_PATTERNS.items():
        if re.search(pattern, text):
            sections_found[section_name] = True

    # ── Skills Extraction ──
    found_skills = {}
    for skill, category in ALL_SKILLS.items():
        # Use word boundary matching for short skills, substring for longer ones
        if len(skill) <= 2:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, text_lower):
                found_skills[skill] = category
        elif skill in text_lower:
            found_skills[skill] = category

    # Group skills by category
    skills_by_category = {}
    for skill, category in found_skills.items():
        if category not in skills_by_category:
            skills_by_category[category] = []
        skills_by_category[category].append(skill)

    # ── Action Verbs ──
    words = re.findall(r'\b[a-z]+\b', text_lower)
    found_verbs = [v for v in ACTION_VERBS if v in words]

    # ── Quantifiable Metrics ──
    metrics = re.findall(
        r'(?:\d+[%+]|\$[\d,]+\.?\d*|\d+\s*(?:users?|clients?|customers?|projects?|team\s*members?|employees?|applications?|years?|months?|percent|million|billion|thousand|k\b))',
        text_lower
    )

    # ── Word count & line count ──
    word_count = len(words)
    line_count = len([l for l in lines if l.strip()])

    # ── Education details ──
    degree_patterns = [
        r"(?i)\b(bachelor|b\.?s\.?|b\.?a\.?|b\.?e\.?|b\.?tech|b\.?sc)\b",
        r"(?i)\b(master|m\.?s\.?|m\.?a\.?|m\.?e\.?|m\.?tech|m\.?sc|mba)\b",
        r"(?i)\b(ph\.?d|doctorate|doctoral)\b",
        r"(?i)\b(associate|diploma|certificate)\b",
    ]
    education_level = []
    for dp in degree_patterns:
        matches = re.findall(dp, text)
        if matches:
            education_level.extend(matches)

    return {
        "contact": contact,
        "sections_found": sections_found,
        "skills": found_skills,
        "skills_by_category": skills_by_category,
        "skill_count": len(found_skills),
        "action_verbs": found_verbs,
        "action_verb_count": len(found_verbs),
        "metrics": metrics,
        "metric_count": len(metrics),
        "word_count": word_count,
        "line_count": line_count,
        "education_level": education_level,
    }


# ─── ATS Score Calculator ─────────────────────────────────────────────────────

def compute_ats_score(parsed_data):
    """
    Compute ATS compatibility score (0–100) across weighted categories.
    Returns (total_score, breakdown_dict).
    """
    breakdown = {}

    # 1. Contact Info (10%)
    contact = parsed_data.get("contact", {})
    contact_score = 0
    if contact.get("email"):
        contact_score += 40
    if contact.get("phone"):
        contact_score += 30
    if contact.get("linkedin"):
        contact_score += 20
    if contact.get("github"):
        contact_score += 10
    breakdown["Contact Information"] = {
        "score": min(contact_score, 100),
        "weight": 10,
        "details": f"{'Email ✓' if contact.get('email') else 'Email ✗'}, "
                   f"{'Phone ✓' if contact.get('phone') else 'Phone ✗'}, "
                   f"{'LinkedIn ✓' if contact.get('linkedin') else 'LinkedIn ✗'}, "
                   f"{'GitHub ✓' if contact.get('github') else 'GitHub ✗'}",
    }

    # 2. Section Structure (20%)
    sections = parsed_data.get("sections_found", {})
    essential = ["experience", "education", "skills"]
    bonus = ["projects", "certifications", "summary"]
    section_score = 0
    for s in essential:
        if sections.get(s):
            section_score += 25
    for s in bonus:
        if sections.get(s):
            section_score += 8.33
    section_score = min(section_score, 100)
    found_names = [s for s in SECTION_PATTERNS if sections.get(s)]
    breakdown["Section Structure"] = {
        "score": round(section_score),
        "weight": 20,
        "details": f"Found: {', '.join(found_names) if found_names else 'None'}",
    }

    # 3. Skills Keywords (25%)
    skill_count = parsed_data.get("skill_count", 0)
    if skill_count >= 15:
        skill_score = 100
    elif skill_count >= 10:
        skill_score = 85
    elif skill_count >= 7:
        skill_score = 70
    elif skill_count >= 4:
        skill_score = 50
    elif skill_count >= 2:
        skill_score = 30
    else:
        skill_score = 10
    breakdown["Skills & Keywords"] = {
        "score": skill_score,
        "weight": 25,
        "details": f"{skill_count} industry-relevant skills detected",
    }

    # 4. Action Verbs (15%)
    verb_count = parsed_data.get("action_verb_count", 0)
    if verb_count >= 12:
        verb_score = 100
    elif verb_count >= 8:
        verb_score = 85
    elif verb_count >= 5:
        verb_score = 65
    elif verb_count >= 3:
        verb_score = 45
    elif verb_count >= 1:
        verb_score = 25
    else:
        verb_score = 5
    breakdown["Action Verbs"] = {
        "score": verb_score,
        "weight": 15,
        "details": f"{verb_count} strong action verbs used",
    }

    # 5. Quantifiable Results (15%)
    metric_count = parsed_data.get("metric_count", 0)
    if metric_count >= 6:
        metric_score = 100
    elif metric_count >= 4:
        metric_score = 80
    elif metric_count >= 2:
        metric_score = 60
    elif metric_count >= 1:
        metric_score = 35
    else:
        metric_score = 10
    breakdown["Quantifiable Results"] = {
        "score": metric_score,
        "weight": 15,
        "details": f"{metric_count} measurable achievements found",
    }

    # 6. Formatting & Length (15%)
    word_count = parsed_data.get("word_count", 0)
    if 300 <= word_count <= 900:
        format_score = 100
    elif 200 <= word_count < 300 or 900 < word_count <= 1200:
        format_score = 75
    elif 100 <= word_count < 200 or 1200 < word_count <= 1600:
        format_score = 50
    else:
        format_score = 25
    breakdown["Formatting & Length"] = {
        "score": format_score,
        "weight": 15,
        "details": f"{word_count} words ({'optimal range' if 300 <= word_count <= 900 else 'consider adjusting length'})",
    }

    # ── Weighted Total ──
    total = sum(
        cat["score"] * cat["weight"] / 100
        for cat in breakdown.values()
    )
    total_score = round(total)

    return total_score, breakdown


# ─── Job Role Database ─────────────────────────────────────────────────────────

JOB_ROLES = {
    "Software Engineer": {
        "required_skills": ["python", "java", "javascript", "git", "sql", "data structures", "algorithms"],
        "preferred_skills": ["docker", "aws", "ci/cd", "agile", "unit testing", "rest api"],
        "salary_range": "$90K – $160K",
        "icon": "💻",
        "description": "Design, develop, and maintain software applications and systems.",
    },
    "Frontend Developer": {
        "required_skills": ["html", "css", "javascript", "react", "git"],
        "preferred_skills": ["typescript", "next.js", "tailwind", "figma", "webpack", "vue"],
        "salary_range": "$80K – $145K",
        "icon": "🎨",
        "description": "Build responsive, performant user interfaces for web applications.",
    },
    "Backend Developer": {
        "required_skills": ["python", "sql", "rest api", "git"],
        "preferred_skills": ["django", "flask", "docker", "postgresql", "redis", "aws", "node.js"],
        "salary_range": "$85K – $155K",
        "icon": "⚙️",
        "description": "Develop server-side logic, APIs, and database architectures.",
    },
    "Full Stack Developer": {
        "required_skills": ["html", "css", "javascript", "python", "sql", "git"],
        "preferred_skills": ["react", "node.js", "docker", "aws", "mongodb", "rest api"],
        "salary_range": "$90K – $160K",
        "icon": "🔄",
        "description": "Build and maintain both client-side and server-side components.",
    },
    "Data Scientist": {
        "required_skills": ["python", "machine learning", "statistics", "sql", "pandas"],
        "preferred_skills": ["tensorflow", "pytorch", "scikit-learn", "r", "tableau", "deep learning"],
        "salary_range": "$100K – $175K",
        "icon": "📊",
        "description": "Extract insights from complex datasets using statistical and ML methods.",
    },
    "Data Engineer": {
        "required_skills": ["python", "sql", "aws", "docker"],
        "preferred_skills": ["postgresql", "mongodb", "redis", "kafka", "terraform", "linux"],
        "salary_range": "$95K – $165K",
        "icon": "🔧",
        "description": "Design and build scalable data pipelines and infrastructure.",
    },
    "ML Engineer": {
        "required_skills": ["python", "machine learning", "tensorflow", "docker"],
        "preferred_skills": ["pytorch", "kubernetes", "aws", "deep learning", "mlops", "ci/cd"],
        "salary_range": "$110K – $185K",
        "icon": "🤖",
        "description": "Productionize machine learning models at scale.",
    },
    "DevOps Engineer": {
        "required_skills": ["linux", "docker", "kubernetes", "ci/cd", "git"],
        "preferred_skills": ["terraform", "aws", "ansible", "prometheus", "jenkins", "python"],
        "salary_range": "$95K – $165K",
        "icon": "🚀",
        "description": "Automate infrastructure and streamline deployment pipelines.",
    },
    "Cloud Architect": {
        "required_skills": ["aws", "docker", "kubernetes", "terraform", "linux"],
        "preferred_skills": ["azure", "gcp", "serverless", "cloudformation", "python", "networking"],
        "salary_range": "$120K – $200K",
        "icon": "☁️",
        "description": "Design and oversee cloud computing strategies and architectures.",
    },
    "Mobile Developer": {
        "required_skills": ["react native", "javascript", "git"],
        "preferred_skills": ["typescript", "flutter", "swift", "kotlin", "firebase", "rest api"],
        "salary_range": "$85K – $150K",
        "icon": "📱",
        "description": "Build native and cross-platform mobile applications.",
    },
    "UI/UX Designer": {
        "required_skills": ["figma", "html", "css"],
        "preferred_skills": ["sketch", "adobe xd", "javascript", "react", "user research"],
        "salary_range": "$75K – $135K",
        "icon": "✏️",
        "description": "Design intuitive, beautiful user interfaces and experiences.",
    },
    "Product Manager": {
        "required_skills": ["agile", "project management", "communication", "strategic planning"],
        "preferred_skills": ["jira", "confluence", "sql", "data analysis", "scrum", "leadership"],
        "salary_range": "$100K – $170K",
        "icon": "📋",
        "description": "Drive product vision, roadmap, and cross-functional execution.",
    },
    "Cybersecurity Analyst": {
        "required_skills": ["linux", "networking", "python"],
        "preferred_skills": ["aws", "docker", "sql", "git", "monitoring", "encryption"],
        "salary_range": "$85K – $150K",
        "icon": "🔒",
        "description": "Protect systems and data from cyber threats and vulnerabilities.",
    },
    "QA Engineer": {
        "required_skills": ["unit testing", "git", "agile"],
        "preferred_skills": ["python", "javascript", "selenium", "ci/cd", "integration testing", "jira"],
        "salary_range": "$70K – $125K",
        "icon": "🧪",
        "description": "Ensure software quality through testing strategies and automation.",
    },
    "Database Administrator": {
        "required_skills": ["sql", "postgresql", "linux"],
        "preferred_skills": ["mysql", "mongodb", "redis", "oracle", "aws", "python"],
        "salary_range": "$80K – $140K",
        "icon": "🗄️",
        "description": "Manage, optimize, and secure database systems.",
    },
    "AI Research Scientist": {
        "required_skills": ["python", "deep learning", "machine learning", "pytorch"],
        "preferred_skills": ["tensorflow", "nlp", "computer vision", "transformers", "statistics", "r"],
        "salary_range": "$120K – $220K",
        "icon": "🧠",
        "description": "Advance the state of the art in artificial intelligence research.",
    },
    "Site Reliability Engineer": {
        "required_skills": ["linux", "python", "docker", "kubernetes", "monitoring"],
        "preferred_skills": ["terraform", "aws", "prometheus", "grafana", "ci/cd", "go"],
        "salary_range": "$110K – $185K",
        "icon": "🛡️",
        "description": "Ensure reliability, scalability, and performance of production systems.",
    },
    "Blockchain Developer": {
        "required_skills": ["javascript", "python", "git"],
        "preferred_skills": ["solidity", "rust", "docker", "cryptography", "node.js", "web3"],
        "salary_range": "$100K – $180K",
        "icon": "⛓️",
        "description": "Build decentralized applications and smart contracts.",
    },
    "Technical Writer": {
        "required_skills": ["communication", "git"],
        "preferred_skills": ["html", "css", "python", "markdown", "confluence", "jira"],
        "salary_range": "$65K – $110K",
        "icon": "📝",
        "description": "Create clear technical documentation and developer guides.",
    },
    "Data Analyst": {
        "required_skills": ["sql", "python", "data analysis", "data visualization"],
        "preferred_skills": ["tableau", "power bi", "pandas", "statistics", "r", "excel"],
        "salary_range": "$65K – $110K",
        "icon": "📈",
        "description": "Analyze data to generate actionable business insights.",
    },
    "Solutions Architect": {
        "required_skills": ["aws", "python", "sql", "communication"],
        "preferred_skills": ["docker", "kubernetes", "terraform", "azure", "leadership", "agile"],
        "salary_range": "$120K – $190K",
        "icon": "🏗️",
        "description": "Design end-to-end technical solutions for complex business problems.",
    },
    "Game Developer": {
        "required_skills": ["c++", "python", "git"],
        "preferred_skills": ["c#", "unity", "unreal", "javascript", "3d modeling", "agile"],
        "salary_range": "$70K – $140K",
        "icon": "🎮",
        "description": "Design and develop interactive video games and game engines.",
    },
    "Embedded Systems Engineer": {
        "required_skills": ["c++", "python", "linux", "git"],
        "preferred_skills": ["c", "assembly", "rtos", "iot", "electronics", "testing"],
        "salary_range": "$85K – $150K",
        "icon": "🔌",
        "description": "Develop software for embedded hardware and IoT devices.",
    },
    "Business Analyst": {
        "required_skills": ["sql", "communication", "data analysis", "project management"],
        "preferred_skills": ["power bi", "tableau", "jira", "agile", "python", "strategic planning"],
        "salary_range": "$70K – $120K",
        "icon": "💼",
        "description": "Bridge business needs with technical solutions through data-driven analysis.",
    },
    "Marketing Analyst": {
        "required_skills": ["data analysis", "sql", "communication"],
        "preferred_skills": ["python", "tableau", "power bi", "statistics", "excel", "strategic planning"],
        "salary_range": "$60K – $105K",
        "icon": "📣",
        "description": "Analyze marketing performance and optimize campaigns with data.",
    },
}


# ─── Job Matching ──────────────────────────────────────────────────────────────

def match_jobs(parsed_data):
    """
    Match resume skills against job role requirements using Gemini API.
    Falls back to heuristic matching if API fails.
    Returns list of job matches sorted by match percentage.
    """
    def heuristic_match():
        resume_skills = set(parsed_data.get("skills", {}).keys())
        matches = []
        for role_name, role_data in JOB_ROLES.items():
            required = set(role_data["required_skills"])
            preferred = set(role_data["preferred_skills"])
            all_role_skills = required | preferred
            required_matched = required & resume_skills
            preferred_matched = preferred & resume_skills
            all_matched = all_role_skills & resume_skills
            
            if len(required) + len(preferred) > 0:
                weighted_score = (
                    (len(required_matched) * 2 + len(preferred_matched))
                    / (len(required) * 2 + len(preferred))
                    * 100
                )
            else:
                weighted_score = 0
                
            missing_required = required - resume_skills
            missing_preferred = preferred - resume_skills
            
            matches.append({
                "role": role_name,
                "match_percent": round(weighted_score),
                "icon": role_data["icon"],
                "description": role_data["description"],
                "salary_range": role_data["salary_range"],
                "matched_skills": sorted(all_matched),
                "missing_required": sorted(missing_required),
                "missing_preferred": sorted(missing_preferred),
                "required_count": len(required),
                "required_matched_count": len(required_matched),
            })
        matches.sort(key=lambda x: x["match_percent"], reverse=True)
        return matches[:8]

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return heuristic_match()

    try:
        prompt = f"""
        You are an expert career counselor and ATS system.
        Analyze the following parsed resume data:
        {json.dumps(parsed_data, indent=2)}
        
        And the following available job roles:
        {json.dumps(JOB_ROLES, indent=2)}
        
        Select the top 8 job roles that best match this candidate based on their skills, experience, and overall profile.
        For each match, evaluate:
        1. match_percent (0-100)
        2. matched_skills (list of skills they have that match the role)
        3. missing_required (list of required skills they are missing)
        4. missing_preferred (list of preferred skills they are missing)
        5. required_count (total required skills for the role)
        6. required_matched_count (how many required skills they matched)
        
        Return the result STRICTLY as a JSON array of objects, with these exact keys, plus the original role keys ('role', 'icon', 'description', 'salary_range'). Do not include any markdown fences or other text.
        """
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        text_content = data["candidates"][0]["content"]["parts"][0]["text"]
        matches = json.loads(text_content)
        
        if isinstance(matches, list) and len(matches) > 0:
            return matches
        else:
            logger.warning("Gemini API returned empty or invalid job matches list.")
            return heuristic_match()
    except Exception as e:
        logger.error(f"Error calling Gemini API for job matching: {e}")
        return heuristic_match()


# ─── Course & Certification Recommendations ───────────────────────────────────

COURSE_DATABASE = {
    "python": {
        "course": "Python for Everybody Specialization",
        "provider": "Coursera",
        "provider_icon": "🎓",
        "duration": "8 months",
        "level": "Beginner",
        "url": "https://www.coursera.org/specializations/python",
    },
    "javascript": {
        "course": "The Complete JavaScript Course",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "69 hours",
        "level": "Beginner to Advanced",
        "url": "https://www.udemy.com/course/the-complete-javascript-course/",
    },
    "react": {
        "course": "React — The Complete Guide",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "50 hours",
        "level": "Intermediate",
        "url": "https://www.udemy.com/course/react-the-complete-guide/",
    },
    "machine learning": {
        "course": "Machine Learning Specialization",
        "provider": "Coursera (Stanford)",
        "provider_icon": "🎓",
        "duration": "3 months",
        "level": "Intermediate",
        "url": "https://www.coursera.org/specializations/machine-learning-introduction",
    },
    "deep learning": {
        "course": "Deep Learning Specialization",
        "provider": "Coursera (deeplearning.ai)",
        "provider_icon": "🎓",
        "duration": "5 months",
        "level": "Intermediate",
        "url": "https://www.coursera.org/specializations/deep-learning",
    },
    "aws": {
        "course": "AWS Certified Solutions Architect – Associate",
        "provider": "AWS",
        "provider_icon": "☁️",
        "duration": "3 months",
        "level": "Intermediate",
        "url": "https://aws.amazon.com/certification/certified-solutions-architect-associate/",
    },
    "docker": {
        "course": "Docker Mastery: with Kubernetes + Swarm",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "20 hours",
        "level": "Beginner to Advanced",
        "url": "https://www.udemy.com/course/docker-mastery/",
    },
    "kubernetes": {
        "course": "Certified Kubernetes Administrator (CKA)",
        "provider": "Linux Foundation",
        "provider_icon": "🐧",
        "duration": "3 months",
        "level": "Advanced",
        "url": "https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka/",
    },
    "terraform": {
        "course": "HashiCorp Certified: Terraform Associate",
        "provider": "HashiCorp",
        "provider_icon": "🔷",
        "duration": "2 months",
        "level": "Intermediate",
        "url": "https://www.hashicorp.com/certification/terraform-associate",
    },
    "sql": {
        "course": "The Complete SQL Bootcamp",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "9 hours",
        "level": "Beginner",
        "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/",
    },
    "tensorflow": {
        "course": "TensorFlow Developer Certificate",
        "provider": "Google",
        "provider_icon": "🔵",
        "duration": "4 months",
        "level": "Intermediate",
        "url": "https://www.tensorflow.org/certificate",
    },
    "pytorch": {
        "course": "PyTorch for Deep Learning",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "25 hours",
        "level": "Intermediate",
        "url": "https://www.udemy.com/course/pytorch-for-deep-learning/",
    },
    "gcp": {
        "course": "Google Cloud Professional Cloud Architect",
        "provider": "Google Cloud",
        "provider_icon": "🔵",
        "duration": "3 months",
        "level": "Advanced",
        "url": "https://cloud.google.com/certification/cloud-architect",
    },
    "azure": {
        "course": "Microsoft Certified: Azure Fundamentals (AZ-900)",
        "provider": "Microsoft",
        "provider_icon": "🟦",
        "duration": "1 month",
        "level": "Beginner",
        "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/",
    },
    "java": {
        "course": "Java Programming Masterclass",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "80 hours",
        "level": "Beginner to Advanced",
        "url": "https://www.udemy.com/course/java-the-complete-java-developer-course/",
    },
    "django": {
        "course": "Django for Everybody Specialization",
        "provider": "Coursera",
        "provider_icon": "🎓",
        "duration": "3 months",
        "level": "Intermediate",
        "url": "https://www.coursera.org/specializations/django",
    },
    "typescript": {
        "course": "Understanding TypeScript",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "15 hours",
        "level": "Intermediate",
        "url": "https://www.udemy.com/course/understanding-typescript/",
    },
    "node.js": {
        "course": "The Complete Node.js Developer Course",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "35 hours",
        "level": "Intermediate",
        "url": "https://www.udemy.com/course/the-complete-nodejs-developer-course/",
    },
    "ci/cd": {
        "course": "CI/CD Pipelines with GitHub Actions",
        "provider": "LinkedIn Learning",
        "provider_icon": "🔗",
        "duration": "4 hours",
        "level": "Intermediate",
        "url": "https://www.linkedin.com/learning/",
    },
    "linux": {
        "course": "Linux Mastery: Master the Linux Command Line",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "12 hours",
        "level": "Beginner",
        "url": "https://www.udemy.com/course/linux-mastery/",
    },
    "git": {
        "course": "Git Complete: The Definitive Guide",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "6 hours",
        "level": "Beginner",
        "url": "https://www.udemy.com/course/git-complete/",
    },
    "figma": {
        "course": "Google UX Design Professional Certificate",
        "provider": "Coursera (Google)",
        "provider_icon": "🎓",
        "duration": "6 months",
        "level": "Beginner",
        "url": "https://www.coursera.org/professional-certificates/google-ux-design",
    },
    "tableau": {
        "course": "Tableau Desktop Specialist Certification",
        "provider": "Tableau",
        "provider_icon": "📊",
        "duration": "2 months",
        "level": "Intermediate",
        "url": "https://www.tableau.com/learn/certification",
    },
    "power bi": {
        "course": "Microsoft Power BI Data Analyst (PL-300)",
        "provider": "Microsoft",
        "provider_icon": "🟦",
        "duration": "2 months",
        "level": "Intermediate",
        "url": "https://learn.microsoft.com/en-us/certifications/power-bi-data-analyst-associate/",
    },
    "agile": {
        "course": "Certified ScrumMaster (CSM)",
        "provider": "Scrum Alliance",
        "provider_icon": "🏅",
        "duration": "2 days + exam",
        "level": "Beginner",
        "url": "https://www.scrumalliance.org/get-certified/scrum-master-track/certified-scrummaster",
    },
    "data analysis": {
        "course": "Google Data Analytics Professional Certificate",
        "provider": "Coursera (Google)",
        "provider_icon": "🎓",
        "duration": "6 months",
        "level": "Beginner",
        "url": "https://www.coursera.org/professional-certificates/google-data-analytics",
    },
    "nlp": {
        "course": "Natural Language Processing Specialization",
        "provider": "Coursera (deeplearning.ai)",
        "provider_icon": "🎓",
        "duration": "4 months",
        "level": "Advanced",
        "url": "https://www.coursera.org/specializations/natural-language-processing",
    },
    "flutter": {
        "course": "The Complete Flutter Development Bootcamp",
        "provider": "Udemy",
        "provider_icon": "📕",
        "duration": "28 hours",
        "level": "Intermediate",
        "url": "https://www.udemy.com/course/flutter-bootcamp-with-dart/",
    },
    "go": {
        "course": "Programming with Google Go Specialization",
        "provider": "Coursera",
        "provider_icon": "🎓",
        "duration": "3 months",
        "level": "Intermediate",
        "url": "https://www.coursera.org/specializations/google-golang",
    },
    "rust": {
        "course": "The Rust Programming Language (Official Book + Exercises)",
        "provider": "Rust Foundation",
        "provider_icon": "🦀",
        "duration": "Self-paced",
        "level": "Intermediate",
        "url": "https://doc.rust-lang.org/book/",
    },
}


def recommend_courses(parsed_data, job_matches):
    """
    Identify skill gaps from top job matches and recommend courses using Gemini API.
    Falls back to heuristic recommendation if API fails.
    Returns list of course recommendation dicts.
    """
    def heuristic_recommend():
        resume_skills = set(parsed_data.get("skills", {}).keys())
        recommendations = []
        seen_skills = set()

        # Focus on top 3 job matches for skill gaps
        for match in job_matches[:3]:
            missing = match.get("missing_required", []) + match.get("missing_preferred", [])
            for skill in missing:
                if skill in seen_skills:
                    continue
                seen_skills.add(skill)

                course_info = COURSE_DATABASE.get(skill)
                if course_info:
                    recommendations.append({
                        "skill": skill,
                        "for_role": match["role"],
                        "priority": "High" if skill in match.get("missing_required", []) else "Medium",
                        **course_info,
                    })

        # Sort: High priority first, then alphabetically
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        recommendations.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["skill"]))

        return recommendations[:12]  # Cap at 12 recommendations

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return heuristic_recommend()

    try:
        prompt = f"""
        You are an expert career and learning advisor.
        Based on the candidate's parsed resume data:
        {json.dumps(parsed_data, indent=2)}
        
        And their top job matches:
        {json.dumps(job_matches[:3], indent=2)}
        
        And the following available course database:
        {json.dumps(COURSE_DATABASE, indent=2)}
        
        Identify the most critical skill gaps the candidate has for these top roles and recommend up to 12 courses from the course database.
        For each recommendation, provide:
        1. skill (the skill being addressed)
        2. for_role (the role this skill is for)
        3. priority ("High", "Medium", or "Low")
        And include all the fields from the course database for that skill ('course', 'provider', 'provider_icon', 'duration', 'level', 'url').
        
        Return the result STRICTLY as a JSON array of objects. Do not include any markdown fences or other text.
        """
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        text_content = data["candidates"][0]["content"]["parts"][0]["text"]
        recommendations = json.loads(text_content)
        
        if isinstance(recommendations, list):
            return recommendations[:12]
        else:
            logger.warning("Gemini API returned invalid course recommendations format.")
            return heuristic_recommend()
    except Exception as e:
        logger.error(f"Error calling Gemini API for course recommendations: {e}")
        return heuristic_recommend()
