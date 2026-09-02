from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'csw-dynamic-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model (Database Table)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/')
@login_required
def home():
    studio_address = "Dynamic Studio, Magway, Myanmar"
    return render_template('index.html', name=current_user.username, address=studio_address)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('ဒီအကောင့်နာမည် ရှိနှင့်ပြီးသားပါ ညီလေး၊ တခြားနာမည်တစ်ခုပေးပါနော်! 😅')
            return redirect(url_for('signup'))
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('အကောင့်ဖွင့်တာ အောင်မြင်သွားပါပြီ ညီလေးရေ! 🎉 လော့ဂ်အင် ဝင်လိုက်ပါတော့ခင်ဗျာ။')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('အကောင့်နာမည် သို့မဟုတ် စကားဝှက် မှားနေပါတယ် ညီလေး၊ ပြန်စစ်ပေးပါနော်! ⚠️')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('အကောင့်ကနေ ထွက်လိုက်ပါပြီ ညီလေးရေ 👋!')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

