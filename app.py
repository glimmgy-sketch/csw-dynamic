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

# SQLite database ချိတ်ဆက်ရန်
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///csw.db'
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

# Request ပြီးဆုံးတိုင်း Database session ကို သေချာရှင်းလင်းပေးရန် (Error မတက်စေရန်)
@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

with app.app_context():
    db.create_all()
    
    # SQLite တွင် Error မတက်စေရန် Safe Column Migration
    try:
        with db.engine.connect() as connection:
            result = connection.execute(db.text("PRAGMA table_info(post);"))
            columns = [row[1] for row in result.fetchall()]
            if 'media_file' not in columns:
                connection.execute(db.text('ALTER TABLE post ADD COLUMN media_file VARCHAR(200);'))
                connection.commit()
    except Exception as e:
        print("Migration note:", e)

    if not User.query.filter_by(username='MinNaungChan').first():
        default_user = User(username='MinNaungChan', password=generate_password_hash('123456'))
        db.session.add(default_user)
        db.session.commit()

@app.route('/')
def index():
    # Login ဝင်စရာမလိုဘဲ App ဖွင့်လိုက်တာနဲ့ Admin အကောင့်နဲ့ တန်းဝင်ပေးရန် (Auto-login)
    admin_user = User.query.filter_by(username='MinNaungChan').first()
    if admin_user:
        login_user(admin_user)
        
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
        new_user = User(username=username, name=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user, remember=True)
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile/<username>')
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', user=user)

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/add_post', methods=['POST'])
def add_post():
    if not current_user.is_authenticated:
        admin_user = User.query.filter_by(username='MinNaungChan').first()
        if admin_user:
            login_user(admin_user)
            
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
def like_post(post_id):
    if not current_user.is_authenticated:
        admin_user = User.query.filter_by(username='MinNaungChan').first()
        if admin_user:
            login_user(admin_user)
            
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
def add_comment(post_id):
    if not current_user.is_authenticated:
        admin_user = User.query.filter_by(username='MinNaungChan').first()
        if admin_user:
            login_user(admin_user)
            
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

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        posts = Post.query.filter(Post.content.like(f'%{query}%')).order_by(Post.id.desc()).all()
    else:
        posts = []
    return render_template('index.html', posts=posts, search_query=query)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
