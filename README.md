# 🚀 HireAI: Intelligent AI Resume Scanner & Matcher

HireAI is an AI-powered Applicant Tracking System (ATS) that automates the recruitment process. It allows HR professionals to auto-generate Job Descriptions and rank candidate resumes using a Hybrid AI Scoring system (Semantic Meaning + Keyword Matching).

## ✨ Features
* **Role-Based Portals:** Secure logins for 'Applicants' to submit resumes and 'Recruiters' to manage postings.
* **Hybrid Match Scoring:** Uses NLP to calculate a 0-100% match score by combining exact Keyword frequencies (TF-IDF) and Contextual meaning (SentenceTransformers).
* **Gemini AI Deep Analysis:** Automatically reads a candidate's resume and provides a JSON-structured executive summary, highlighting exact matched and missing skills.
* **AI Job Description Generator:** Recruiters can input a job title and instantly generate a professional 100-word JD.
* **Automated SMTP Emails:** Automatically emails candidates when their application status is updated to "Selected" or "Rejected".

## 🛠️ Tech Stack
| Component | Technology Used | Function |
| :--- | :--- | :--- |
| **Backend** | Python, Flask | Server routing, file uploads, authentication, and core logic. |
| **Generative AI** | Google Gemini API (1.5 Flash) | Auto-generating JDs and deep JSON resume analysis. |
| **Semantic AI** | SentenceTransformers (`all-MiniLM-L6-v2`) | Understanding the contextual meaning of resumes. |
| **Machine Learning** | Scikit-Learn (TF-IDF) | Mathematical keyword extraction and cosine similarity matching. |
| **Database** | SQLite, Flask-SQLAlchemy | Securely storing users, roles, and application statuses. |
| **Frontend** | HTML5, CSS3, Bootstrap 4, JS | Custom responsive dashboards with Glassmorphism UI. |
| **File Parsing** | PyPDF2, docx2txt | Extracting raw text from candidate PDF and DOCX uploads. |

## 🚀 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Yashb5599/HireAI.git](https://github.com/YOUR_USERNAME/HireAI.git)
   cd HireAI