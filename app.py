import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chan_secret_key_2026'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'webm'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

basedir = os.path.abspath(os.path.dirname(__file__))
db_url = os.environ.get('DATABASE_URL')

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or ('sqlite:///' + os.path.join(basedir, 'database_v6.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Friendship Table
friendships = db.Table('friendships',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    bio = db.Column(db.String(300), nullable=True)
    posts = db.relationship('Post', backref='author', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    
    friends = db.relationship('User', 
                              secondary=friendships,
                              primaryjoin=(friendships.c.user_id == id),
                              secondaryjoin=(friendships.c.friend_id == id),
                              backref=db.backref('friend_of', lazy='dynamic'),
                              lazy='dynamic')

class Post(db.Model):
    id = db.Column(db.Integer, primary_primary=True) if hasattr(db, 'Integer') else None
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String(300), nullable=True)
    media_type = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    return render_template('index.html', posts=posts, notifications=unread_notifications)

@app.route('/user/<username>')
@login_required
def view_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all()
    is_friend = current_user.friends.filter(friendships.c.friend_id == user.id).count() > 0
    return render_template('profile.html', user=user, posts=posts, is_friend=is_friend)

@app.route('/add_friend/<int:user_id>', methods=['POST'])
@login_required
def add_friend(user_id):
    target_user = User.query.get_or_404(user_id)
    if target_user != current_user:
        current_user.friends.append(target_user)
        target_user.friends.append(current_user)
        
        # Send Notification
        notif = Notification(
            message=f"{current_user.username} က သင့်အား Friend အဖြစ် ထည့်သွင်းလိုက်ပါပြီ 🤝",
            user_id=target_user.id
        )
        db.session.add(notif)
        db.session.commit()
    return redirect(url_for('view_profile', username=target_user.username))

@app.route('/read_notifications', methods=['POST'])
@login_required
def read_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('ဒီ အကောင့်အမည် သုံးပြီးသားဖြစ်နေပါတယ်!', 'danger')
            return redirect(url_for('signup'))
        new_user = User(username=username, password=generate_password_hash(password, method='scrypt'))
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
        flash('Username သို့မဟုတ် Password မှားနေပါသည်။', 'danger')
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
    file = request.files.get('file') or request.files.get('media_file')
    media_url = None
    media_type = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        saved_filename = datetime.now().strftime("%Y%m%d_%H%M%S_") + filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], saved_filename))
        media_url = url_for('static', filename='uploads/' + saved_filename)
        media_type = 'video' if filename.rsplit('.', 1)[1].lower() in ['mp4', 'mov', 'avi', 'webm'] else 'image'

    if content or media_url:
        new_post = Post(content=content, media_url=media_url, media_type=media_type, user_id=current_user.id)
        db.session.add(new_post)
        db.session.commit()
    return redirect(request.referrer or url_for('index'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
