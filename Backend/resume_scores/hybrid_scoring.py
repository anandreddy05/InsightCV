import nltk
# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')
# nltk.download('omw-1.4')
from nltk.stem import WordNetLemmatizer
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from models import Resume
from types import SimpleNamespace

# Load English stopwords from nltk
STOP_WORDS = set(stopwords.words('english'))

def ensure_json_list(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    elif isinstance(value, list):
        return value
    return []

def get_combined_resume_text(resume: Resume) -> str:
    sections = []

    if resume.extracted_text:
        sections.append(resume.extracted_text)

    if resume.skills:
        skills = ensure_json_list(resume.skills)
        sections.append("Skills: " + ", ".join(skills))

    for exp in ensure_json_list(resume.experience):
        role = exp.get("role", "")
        company = exp.get("company", "")
        sections.append(f"{role} at {company}")

    for proj in ensure_json_list(resume.projects):
        name = proj.get("name", "")
        tech = ", ".join(proj.get("tech_stack", []))
        sections.append(f"Project: {name} using {tech}")

    for edu in ensure_json_list(resume.education):
        degree = edu.get("degree", "")
        institution = edu.get("institution", "")
        sections.append(f"Education: {degree} from {institution}")

    return "\n".join(sections).lower()

lemmatizer = WordNetLemmatizer()

def extract_keywords(text: str) -> set:
    tokens = word_tokenize(text.lower())
    keywords = {
        lemmatizer.lemmatize(word)
        for word in tokens
        if word.isalnum() and word not in STOP_WORDS
    }
    return keywords

def tfidf_match_score(job_desc: str, resume_text: str) -> float:
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform([job_desc, resume_text])
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return round(similarity * 100, 2)

def keyword_match_score(job_desc: str, resume_text: str) -> float:
    job_keywords = extract_keywords(job_desc)
    resume_keywords = extract_keywords(resume_text)
    
    if not job_keywords:
        return 0.0
    
    match_count = len(job_keywords.intersection(resume_keywords))
    score = match_count / len(job_keywords) * 100
    return round(score, 2)

def hybrid_match_score(job_desc: str, resume_text: str, tfidf_weight: float = 0.6, keyword_weight: float = 0.4) -> float:
    keyword_score = keyword_match_score(job_desc, resume_text)
    tfidf_score = tfidf_match_score(job_desc, resume_text)
    combined_score = (keyword_score * keyword_weight) + (tfidf_score * tfidf_weight)
    return round(combined_score, 2)



mock_resume = SimpleNamespace(
    extracted_text="""
Senior Python Developer with 6+ years of experience in designing and developing machine learning and deep learning solutions. 
Extensive hands-on experience with Python, TensorFlow, PyTorch, scikit-learn, and SQL. 
Proficient in NLP and Computer Vision projects. Strong understanding of model deployment and API integration.
""",
    skills=json.dumps([
        "Python", "TensorFlow", "PyTorch", "scikit-learn", "SQL", 
        "Git", "NLP", "Computer Vision", "React.js", "Node.js"
    ]),
    experience=json.dumps([
        {"role": "Senior Python Developer", "company": "Tech Solutions Inc"},
        {"role": "Machine Learning Engineer", "company": "AI Innovations"},
    ]),
    projects=json.dumps([
        {
            "name": "VisionAI",
            "tech_stack": ["Python", "OpenCV", "TensorFlow", "Computer Vision", "Docker"]
        },
        {
            "name": "ChatNLP",
            "tech_stack": ["Python", "BERT", "NLP", "FastAPI", "scikit-learn"]
        },
        {
            "name": "FullStackML",
            "tech_stack": ["React.js", "Node.js", "Flask", "SQL", "Git"]
        }
    ]),
    education=json.dumps([
        {"degree": "B.Tech in Computer Science", "institution": "ABC University"},
        {"degree": "M.S. in Artificial Intelligence", "institution": "XYZ Institute"}
    ])
)


job_desc = """
We are hiring a Senior Python Developer with 5+ years experience in Machine Learning and Deep Learning.
Required skills: Python, TensorFlow, PyTorch, scikit-learn, SQL, Git.
The candidate should have experience with NLP and Computer Vision projects.
Knowledge of React.js and Node.js is a plus for full-stack development.
"""

combined_text = get_combined_resume_text(mock_resume)
print("Hybrid Match Score:", hybrid_match_score(job_desc, combined_text))
