import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'csw-dynamic-secret-key'

db_path = os.path.join('/tmp', 'csw.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- DATABASE MODELS ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    posts = db.relationship('Post', backref='author', lazy=True)
    notifications = db.relationship('Notification', backref='recipient', lazy=True, cascade="all, delete-orphan")

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    emoji = db.Column(db.String(10), default='👍')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    author = db.relationship('User', backref='user_comments')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    # Render တွင် Database Table အသစ်များ အပြည့်အစုံ ဆောက်လုပ်ရန်
    db.drop_all() # Temporary fix to reset clean tables and avoid internal server errors
    db.create_all()
    if not User.query.filter_by(username='MinNaungChan').first():
        default_user = User(username='MinNaungChan', password=generate_password_hash('123456'))
        db.session.add(default_user)
        db.session.commit()

# --- ROUTES ---

@app.route('/')
@login_required
def index():
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect(url_for('index'))
        flash('Username သို့မဟုတ် Password မှားနေပါတယ် သားကြီး!')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('ဒီ Username က ရှိနှင့်ပြီးသားပါ ညီလေး!')
            return redirect(url_for('signup'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user, remember=True)
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', user=user)

@app.route('/add_post', methods=['POST'])
@login_required
def add_post():
    content = request.form.get('content')
    if content:
        new_post = Post(content=content, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    emoji = request.form.get('emoji', '👍')
    
    existing_like = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing_like:
        if existing_like.emoji == emoji:
            db.session.delete(existing_like)
        else:
            existing_like.emoji = emoji
    else:
        new_like = Like(user_id=current_user.id, post_id=post_id, emoji=emoji)
        db.session.add(new_like)
        if post.user_id != current_user.id:
            notif_msg = f"{current_user.username} က သင့်ပို့စ်ကို {emoji} ပေးသွားပါတယ်။"
            notif = Notification(message=notif_msg, user_id=post.user_id)
            db.session.add(notif)
            
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('content')
    if content:
        new_comment = Comment(content=content, user_id=current_user.id, post_id=post_id)
        db.session.add(new_comment)
        if post.user_id != current_user.id:
            notif_msg = f"{current_user.username} က သင့်ပို့စ်တွင် မန့်သွားသည်: '{content[:20]}...'"
            notif = Notification(message=notif_msg, user_id=post.user_id)
            db.session.add(notif)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/notifications')
@login_required
def notifications():
    user_notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.id.desc()).all()
    return render_template('notifications.html', notifications=user_notifs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
