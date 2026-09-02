import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dynamic-studio-secret-key-2026'

db_path = os.path.join(os.getcwd(), 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    bio = db.Column(db.Text, nullable=True, default="Dynamic Studio (မကွေးမြို့) - 📍 လေ့ကျင့်ခန်းနှင့် ကြံ့ခိုင်ရေး")
    followers_count = db.Column(db.Integer, default=120)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    media_file = db.Column(db.String(300), nullable=True)
    likes = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('posts', lazy=True))

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    media_file = db.Column(db.String(300), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('stories', lazy=True))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('comments', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        content = request.form.get('content')
        file = request.files.get('media_file')
        
        filename = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        new_post = Post(content=content, media_file=filename, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))
        
    posts = Post.query.order_by(Post.id.desc()).all()
    stories = Story.query.order_by(Story.id.desc()).all()
    return render_template('index.html', posts=posts, stories=stories)

@app.route('/add_story', methods=['POST'])
@login_required
def add_story():
    file = request.files.get('story_file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_story = Story(media_file=filename, user_id=current_user.id)
        db.session.add(new_story)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return jsonify({'likes': post.likes})

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    text = request.form.get('text')
    if text:
        comment = Comment(text=text, post_id=post_id, user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_bio = request.form.get('bio')
        if new_bio is not None:
            current_user.bio = new_bio
            db.session.commit()
            return redirect(url_for('profile'))
            
        content = request.form.get('content')
        file = request.files.get('media_file')
        filename = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        new_post = Post(content=content, media_file=filename, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('profile'))

    user_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.id.desc()).all()
    return render_template('profile.html', posts=user_posts)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            return redirect(url_for('signup'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    app.run(host='0.0.0.0', port=5000)
