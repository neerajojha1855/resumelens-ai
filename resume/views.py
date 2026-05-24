from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Resume
from .utils import extract_text, parse_resume, compute_ats_score, match_jobs, recommend_courses
import json


def home(request):
    """Render the landing page with resume upload form."""
    return render(request, 'resume/home.html')


def upload_resume(request):
    """Handle resume file upload, run NLP analysis, and redirect to results."""
    if request.method != 'POST':
        return redirect('home')

    uploaded_file = request.FILES.get('resume_file')
    if not uploaded_file:
        messages.error(request, 'Please select a resume file to upload.')
        return redirect('home')

    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc']
    file_ext = '.' + uploaded_file.name.rsplit('.', 1)[-1].lower() if '.' in uploaded_file.name else ''
    if file_ext not in allowed_extensions:
        messages.error(request, 'Unsupported file format. Please upload a PDF or DOCX file.')
        return redirect('home')

    # Validate file size (max 5MB)
    if uploaded_file.size > 5 * 1024 * 1024:
        messages.error(request, 'File size exceeds 5MB limit.')
        return redirect('home')

    try:
        # Extract text from the resume
        raw_text = extract_text(uploaded_file)

        if not raw_text or len(raw_text.strip()) < 50:
            messages.error(request, 'Could not extract sufficient text from the file. Please ensure the resume contains readable text.')
            return redirect('home')

        # Run NLP parsing pipeline
        parsed_data = parse_resume(raw_text)

        # Compute ATS score
        ats_score, ats_breakdown = compute_ats_score(parsed_data)

        # Match to job roles
        job_match_results = match_jobs(parsed_data)

        # Get course recommendations
        course_recs = recommend_courses(parsed_data, job_match_results)

        # Save to database
        resume = Resume.objects.create(
            file=uploaded_file,
            original_filename=uploaded_file.name,
            raw_text=raw_text,
            parsed_data=parsed_data,
            ats_score=ats_score,
            ats_breakdown=ats_breakdown,
            job_matches=job_match_results,
            recommendations=course_recs,
        )

        return redirect('results', pk=resume.pk)

    except ValueError as e:
        messages.error(request, str(e))
        return redirect('home')
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f'An error occurred while processing your resume: {str(e)}')
        return redirect('home')


def results(request, pk):
    """Display the full analysis dashboard for a processed resume."""
    resume = get_object_or_404(Resume, pk=pk)

    # Prepare ATS breakdown for the template
    ats_breakdown_list = []
    for category, data in resume.ats_breakdown.items():
        ats_breakdown_list.append({
            "category": category,
            "score": data["score"],
            "weight": data["weight"],
            "details": data["details"],
        })

    # Determine ATS score color/label
    score = resume.ats_score
    if score >= 80:
        score_label = "Excellent"
        score_color = "success"
    elif score >= 60:
        score_label = "Good"
        score_color = "warning"
    elif score >= 40:
        score_label = "Needs Work"
        score_color = "caution"
    else:
        score_label = "Poor"
        score_color = "danger"

    # Skills grouped by category for display
    skills_by_category = resume.parsed_data.get("skills_by_category", {})

    context = {
        "resume": resume,
        "ats_score": score,
        "score_label": score_label,
        "score_color": score_color,
        "ats_breakdown": ats_breakdown_list,
        "job_matches": resume.job_matches,
        "recommendations": resume.recommendations,
        "skills_by_category": skills_by_category,
        "skill_count": resume.parsed_data.get("skill_count", 0),
        "contact": resume.parsed_data.get("contact", {}),
        "action_verb_count": resume.parsed_data.get("action_verb_count", 0),
        "metric_count": resume.parsed_data.get("metric_count", 0),
        "word_count": resume.parsed_data.get("word_count", 0),
        "ats_breakdown_json": json.dumps(ats_breakdown_list),
    }
    return render(request, 'resume/results.html', context)
