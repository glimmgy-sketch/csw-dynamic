import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chan_secret_key_2026'

# File Upload Settings
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database Setup (Supabase PostgreSQL / SQLite Fallback)
basedir = os.path.abspath(os.path.dirname(__file__))
db_url = os.environ.get('DATABASE_URL')

# Render/Supabase postgres:// URL ကို SQLAlchemy ဖတ်နိုင်သော postgresql:// သို့ ပြောင်းပေးခြင်း
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or ('sqlite:///' + os.path.join(basedir, 'database_v6.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Helper Function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    reactions = db.relationship('Reaction', backref='user', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(300), nullable=True)
    media_type = db.Column(db.String(50), nullable=True) # 'image' or 'video'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reactions = db.relationship('Reaction', backref='post', lazy=True, cascade="all, delete-orphan")

class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False) # 'like', 'love', 'haha', 'wow', 'sad', 'angry'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
@login_required
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('ဒီ အကောင့်အမည် သုံးပြီးသားဖြစ်နေပါတယ်! အခြားအမည်ပြောင်းပါ။', 'danger')
            return redirect(url_for('signup'))
            
        hashed_pw = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Username သို့မဟုတ် Password မှားယွင်းနေပါသည်။', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    file = request.files.get('file')
    
    media_url = None
    media_type = None
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        saved_filename = timestamp + filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))
        
        media_url = url_for('static', filename='uploads/' + saved_filename)
        ext = filename.rsplit('.', 1)[1].lower()
        if ext in ['mp4', 'mov', 'avi', 'webm']:
            media_type = 'video'
        else:
            media_type = 'image'

    if content or media_url:
        new_post = Post(
            content=content,
            media_url=media_url,
            media_type=media_type,
            user_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        
    return redirect(url_for('index'))

@app.route('/react/<int:post_id>/<string:reaction_type>', methods=['POST'])
@login_required
def react(post_id, reaction_type):
    existing_reaction = Reaction.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    
    if existing_reaction:
        if existing_reaction.type == reaction_type:
            db.session.delete(existing_reaction) # Toggle Off
        else:
            existing_reaction.type = reaction_type # Change Reaction
    else:
        new_reaction = Reaction(type=reaction_type, user_id=current_user.id, post_id=post_id)
        db.session.add(new_reaction)
        
    db.session.commit()
    return redirect(url_for('index'))

# Database Table Auto-creation
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
