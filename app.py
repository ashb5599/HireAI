from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os, json, re, smtplib
from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util
import docx2txt, PyPDF2
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recruiter.db'
app.config['UPLOAD_FOLDER'] = 'uploads/'

# --- AI CONFIG ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY")) 
semantic_model = SentenceTransformer('all-MiniLM-L6-v2')

# --- EMAIL CONFIG ---
# Replace these with your actual Gmail and the App Password you generated
SENDER_EMAIL = os.getenv("EMAIL") 
SENDER_PASSWORD = os.getenv("PW")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'index'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    default_jd = db.Column(db.Text, nullable=True)

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    course = db.Column(db.String(100))
    exp = db.Column(db.Integer)
    resume_path = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Pending')
    feedback = db.Column(db.String(500), default='Your application is under review.')
    score = db.Column(db.Float, default=0.0)
    user = db.relationship('User', backref=db.backref('profile', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def extract_text(file_path):
    text = ""
    try:
        if file_path.endswith('.pdf'):
            with open(file_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f); text = "".join([p.extract_text() or "" for p in pdf.pages])
        elif file_path.endswith('.docx'):
            text = docx2txt.process(file_path)
    except: pass
    return re.sub(r'[^a-zA-Z\s]', '', text.lower())

def get_best_model():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            if 'flash' in m.name: return m.name
    return "gemini-1.5-flash"

# --- HELPER: SEND EMAIL ---
def send_status_email(to_email, username, status, feedback, course):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"HireAI Recruitment <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = f"Application Update: {course}"
        
        body = f"""Hello {username},

This is an automated update regarding your application for the {course} position.

Status: {status}
Feedback: {feedback}

Thank you for using the HireAI portal.
"""
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@app.route('/')
def index(): return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(username=request.form.get('username')).first()
    if user and user.password == request.form.get('password'):
        login_user(user); return redirect(url_for('dashboard'))
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    u, e, p, r = request.form.get('username'), request.form.get('email'), request.form.get('password'), request.form.get('role')
    if User.query.filter_by(username=u).first(): return redirect(url_for('index'))
    db.session.add(User(username=u, email=e, password=p, role=r)); db.session.commit()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'applicant':
        p = Profile.query.filter_by(user_id=current_user.id).first()
        return render_template('applicant_dash.html', profile=p, courses=Course.query.all())
    return render_template('recruiter_dash.html', course_data=[{'name':c.name, 'count':Profile.query.filter_by(course=c.name).count(), 'default_jd':c.default_jd} for c in Course.query.all()])

@app.route('/rank_candidates', methods=['POST'])
@login_required
def rank_candidates():
    target, jd = request.form.get('course'), request.form.get('jd')
    candidates = Profile.query.filter_by(course=target).all()
    if not candidates: return redirect(url_for('dashboard'))
    resumes = [extract_text(c.resume_path) for c in candidates]
    
    v = TfidfVectorizer(); tf = v.fit_transform([jd] + resumes); kw = cosine_similarity(tf[0:1], tf[1:])[0]
    j_e = semantic_model.encode(jd, convert_to_tensor=True); r_e = semantic_model.encode(resumes, convert_to_tensor=True)
    sm = util.cos_sim(j_e, r_e)[0]
    
    for i, c in enumerate(candidates):
        c.score = round(((kw[i] + sm[i].item()) / 2) * 100, 2)
        c.preview_text = resumes[i][:300] + "..."
    db.session.commit()
    return render_template('rankings.html', candidates=sorted(candidates, key=lambda x: x.score, reverse=True), jd=jd, course=target)

@app.route('/api/generate_jd', methods=['POST'])
def generate_jd():
    model = genai.GenerativeModel(get_best_model())
    res = model.generate_content(f"Write a 100-word professional JD for {request.get_json().get('course')}.")
    return jsonify({"jd": res.text})

@app.route('/api/analyze_candidate', methods=['POST'])
def analyze_candidate():
    d = request.get_json(); p = db.session.get(Profile, d.get('profile_id'))
    m = genai.GenerativeModel(get_best_model(), generation_config={"response_mime_type": "application/json"})
    prompt = f"Resume: {extract_text(p.resume_path)} vs JD: {d.get('jd')}. JSON: summary, matched, missing."
    return jsonify(json.loads(m.generate_content(prompt).text))

@app.route('/add_course', methods=['POST'])
@login_required
def add_course():
    db.session.add(Course(name=request.form.get('course_name'), default_jd=request.form.get('default_jd'))); db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/submit_profile', methods=['POST'])
@login_required
def submit_profile():
    f = request.files['resume']
    if f:
        path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)); f.save(path)
        db.session.add(Profile(user_id=current_user.id, course=request.form.get('course'), exp=int(request.form.get('exp') or 0), resume_path=path)); db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/update_status/<int:pid>', methods=['POST'])
@login_required
def update_status(pid):
    p = db.session.get(Profile, pid)
    p.status, p.feedback = request.form.get('status'), request.form.get('feedback')
    db.session.commit()
    
    # Trigger the email when the status is updated
    send_status_email(p.user.email, p.user.username, p.status, p.feedback, p.course)
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('index'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context(): db.create_all()
    app.run(debug=True)