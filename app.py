import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Post, Like, Comment, Notification
from notifications import notif_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'csw-dynamic-secret-key'

db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///csw.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ပုံဖိုင်တွေ သိမ်းမယ့် နေရာ (Upload folder) နဲ့ ခွင့်ပြုထားတဲ့ Extension တွေ
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.register_blueprint(notif_bp)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()
    
    # 🔴 Database ထဲမှာ media_file column မရှိသေးရင် အလိုအလျောက် ထည့်ပေးမယ့် Auto-Migration 
    try:
        db.engine.execute('ALTER TABLE post ADD COLUMN media_file VARCHAR(200);')
    except Exception as e:
        print("Column already exists or added:", e)

    if not User.query.filter_by(username='MinNaungChan').first():
        default_user = User(username='MinNaungChan', password=generate_password_hash('123456'))
        db.session.add(default_user)
        db.session.commit()

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
        name = request.form.get('name')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('ဒီ Username က ရှိနှင့်ပြီးသားပါ ညီလေး!')
            return redirect(url_for('signup'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, name=name, password=hashed_password)
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
    media_file = request.files.get('media')
    
    filename = None
    if media_file and media_file.filename != '' and allowed_file(media_file.filename):
        filename = secure_filename(media_file.filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        media_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    if content or filename:
        new_post = Post(content=content, media_file=filename, user_id=current_user.id)
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
            notif_msg = f"{current_user.username} reacted {emoji} to your post."
            notif = Notification(message=notif_msg, user_id=post.user_id, post_id=post.id)
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
            notif_msg = f"{current_user.username} commented on your post: '{content[:15]}...'"
            notif = Notification(message=notif_msg, user_id=post.user_id, post_id=post.id)
            db.session.add(notif)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
