from celery import shared_task
from django.conf import settings
from .models import Question
from papers.models import QuestionPaper
from django.contrib.auth.models import User
import json
import logging
import random
import os

logger = logging.getLogger(__name__)


def generate_fallback_questions(topic, difficulty, marks, question_type, count):
    """
    Generate template-based questions locally when all AI APIs fail.
    Returns a list of question dicts in the same format as the AI response.
    """
    SHORT_TEMPLATES = [
        "Define the concept of {topic} in your own words.",
        "What are the key characteristics of {topic}?",
        "Explain the importance of {topic} in modern applications.",
        "List any three properties of {topic}.",
        "What is the difference between {topic} and its alternatives?",
        "Describe the fundamental principles underlying {topic}.",
        "What are the limitations of {topic}?",
        "How does {topic} contribute to problem-solving in this domain?",
        "State and explain the main theorem related to {topic}.",
        "Give a real-world example that illustrates {topic}.",
    ]
    LONG_TEMPLATES = [
        "Discuss {topic} in detail, covering its definition, types, applications, and limitations.",
        "Explain the working mechanism of {topic} with a suitable diagram and example.",
        "Compare and contrast {topic} with any other related concept. Provide examples to support your answer.",
        "Analyse the role of {topic} in modern systems. Discuss challenges and future directions.",
        "With the help of suitable examples, explain how {topic} is applied in real-world scenarios.",
    ]
    MCQ_TEMPLATES = [
        "Which of the following best describes {topic}? (A) Option A  (B) Option B  (C) Option C  (D) Option D",
        "The primary purpose of {topic} is: (A) A  (B) B  (C) C  (D) D",
        "Which statement about {topic} is CORRECT? (A) Statement A  (B) Statement B  (C) Statement C  (D) Statement D",
        "In the context of {topic}, which of the following is true? (A) A  (B) B  (C) C  (D) D",
        "{topic} is best described as: (A) A process  (B) A structure  (C) An algorithm  (D) A framework",
    ]
    CASE_TEMPLATES = [
        "A company is implementing {topic} in their production system. Identify the challenges they may face and suggest solutions.",
        "Consider a scenario where {topic} fails midway through execution. What corrective measures would you apply?",
        "An organisation wants to adopt {topic}. As a consultant, outline a step-by-step implementation plan.",
        "Evaluate the impact of {topic} on a large-scale distributed system. Justify your answer with examples.",
    ]

    template_map = {
        'Short Questions': SHORT_TEMPLATES,
        'Long Questions': LONG_TEMPLATES,
        'MCQ': MCQ_TEMPLATES,
        'Case Study': CASE_TEMPLATES,
    }
    templates = template_map.get(question_type, SHORT_TEMPLATES)
    pool = (templates * ((count // len(templates)) + 2))
    selected = random.sample(pool, min(count, len(pool)))

    questions = []
    for tmpl in selected[:count]:
        questions.append({
            "text": tmpl.format(topic=topic),
            "subject": topic,
            "difficulty": difficulty,
            "marks": marks,
            "sub_topic": topic,
            "tags": f"{topic}, {difficulty}, {question_type}",
        })
    return questions


def _build_prompt(topic, difficulty, marks, question_type, count):
    return (
        f"You are an expert academic question generator.\n"
        f"Generate {count} {question_type} questions for the topic '{topic}'.\n"
        f"Difficulty level: {difficulty}\n"
        f"Marks per question: {marks}\n\n"
        f"Return ONLY a valid JSON object with a \"questions\" array. "
        f"Each question must have: text, subject, difficulty, marks, sub_topic, tags."
    )


def _try_gemini(topic, difficulty, marks, question_type, count):
    """Try generating questions using Google Gemini (primary AI)."""
    gemini_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY')
    if not gemini_key:
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            generation_config={"response_mime_type": "application/json"},
        )
        prompt = _build_prompt(topic, difficulty, marks, question_type, count)
        response = model.generate_content(prompt)
        data = json.loads(response.text)
        questions = data.get('questions', data)
        if isinstance(questions, dict):
            for val in questions.values():
                if isinstance(val, list):
                    questions = val
                    break
        logger.info(f"Gemini successfully generated {len(questions)} questions.")
        return questions
    except Exception as e:
        logger.warning(f"Gemini failed: {e}")
        return None


def _try_groq(topic, difficulty, marks, question_type, count):
    """Try generating questions using Groq (primary AI)."""
    api_key = getattr(settings, 'GROQ_API_KEY', None) or os.environ.get('GROQ_API_KEY')
    if not api_key:
        return None

    try:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        prompt = _build_prompt(topic, difficulty, marks, question_type, count)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON objects."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        questions = data.get('questions', data)
        if isinstance(questions, dict):
            for val in questions.values():
                if isinstance(val, list):
                    questions = val
                    break
        logger.info(f"Groq successfully generated {len(questions)} questions.")
        return questions
    except Exception as e:
        logger.warning(f"Groq failed: {e}")
        return None


def _try_openai(topic, difficulty, marks, question_type, count):
    """Try generating questions using OpenAI (tertiary AI)."""
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        return None

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        prompt = _build_prompt(topic, difficulty, marks, question_type, count)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON objects."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        questions = data.get('questions', data)
        if isinstance(questions, dict):
            for val in questions.values():
                if isinstance(val, list):
                    questions = val
                    break
        logger.info(f"OpenAI successfully generated {len(questions)} questions.")
        return questions
    except Exception as e:
        logger.warning(f"OpenAI failed: {e}")
        return None


@shared_task
def generate_ai_questions_task(topic, difficulty, marks, question_type, count, user_id, department):
    """
    Celery task to generate questions with a tiered AI strategy:
      1. Groq (primary — free, extremely fast)
      2. Google Gemini (secondary — free tier)
      3. OpenAI gpt-4o-mini (tertiary — if others fail)
      4. Academic template fallback (last resort — always works offline)
    """
    questions_data = None
    used_fallback = False
    ai_provider = None

    # --- Tier 1: Groq ---
    questions_data = _try_groq(topic, difficulty, marks, question_type, count)
    if questions_data is not None:
        ai_provider = "groq"

    # --- Tier 2: Gemini ---
    if questions_data is None:
        logger.info("Falling back to Gemini...")
        questions_data = _try_gemini(topic, difficulty, marks, question_type, count)
        if questions_data is not None:
            ai_provider = "gemini"

    # --- Tier 3: OpenAI ---
    if questions_data is None:
        logger.info("Falling back to OpenAI...")
        questions_data = _try_openai(topic, difficulty, marks, question_type, count)
        if questions_data is not None:
            ai_provider = "openai"

    # --- Tier 4: Template fallback ---
    if questions_data is None:
        logger.warning("All AI APIs failed — using template fallback.")
        questions_data = generate_fallback_questions(topic, difficulty, marks, question_type, count)
        used_fallback = True
        ai_provider = "template"

    # --- Save questions to DB ---
    try:
        user = User.objects.get(id=user_id)
        institution = user.profile.institution if hasattr(user, 'profile') else None
        created_questions = []

        for q in questions_data:
            if isinstance(q, dict) and 'text' in q:
                if not Question.objects.filter(text__iexact=q['text'], institution=institution).exists():
                    question = Question.objects.create(
                        text=q['text'],
                        subject=q.get('subject', topic),
                        difficulty=difficulty,
                        marks=marks,
                        sub_topic=topic,
                        tags=q.get('tags', ''),
                        department=department,
                        institution=institution,
                        created_by=user
                    )
                    created_questions.append(question)

        paper_id = None
        if created_questions:
            # Also bundle these into an AI-generated Question Paper
            paper = QuestionPaper.objects.create(
                subject=topic,
                created_by=user,
                institution=institution,
                distribution=[{
                    "type": "AI Generated Set", 
                    "marks": marks, 
                    "count": len(created_questions),
                    "ai_provider": ai_provider
                }]
            )
            paper.questions.set(created_questions)
            paper_id = paper.id

        return {
            "status": "success",
            "created_count": len(created_questions),
            "ids": [q.id for q in created_questions],
            "paper_id": paper_id,
            "used_fallback": used_fallback,
            "ai_provider": ai_provider,
        }

    except Exception as e:
        logger.error(f"Error saving questions: {str(e)}")
        return {"error": f"Failed to save questions: {str(e)}"}
