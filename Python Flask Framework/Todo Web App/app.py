from flask_mail import Mail, Message
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todos.db'
app.config['SECRET_KEY'] = 'your secret key'
app.config['SECURITY_PASSWORD_SALT'] = 'your security password salt'

app.config['MAIL_SERVER'] = 'smtp.domain.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'your_email@domain.com'
app.config['MAIL_PASSWORD'] = 'your password'

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))
    is_verified = db.Column(db.Boolean, default=False)
    verified_on = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __repr__(self):
        return f'<Todo {self.title}>'


def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

def send_verification_email(user):
    token = generate_verification_token(user.email)
    verify_url = url_for('verify_email', token=token, _external=True)
    subject = 'Please verify your email'
    sender = app.config['MAIL_USERNAME']
    recipients = [user.email]
    body = f'Welcome {user.username}! Thanks for signing up. Please follow this link to verify your email address: {verify_url}'
    msg = Message(subject, sender=sender, recipients=recipients, body=body)
    mail.send(msg)

def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])

def send_reset_email(user):
    token = generate_reset_token(user.email)
    reset_url = url_for('reset_password', token=token, _external=True)
    subject = 'Password Reset Request'
    sender = app.config['MAIL_USERNAME']
    recipients = [user.email]
    body = f'Dear {user.username},\n\nTo reset your password, please follow this link: {reset_url}\n\nIf you did not make this request, please ignore this email.'
    msg = Message(subject, sender=sender, recipients=recipients, body=body)
    mail.send(msg)

def verify_token(token):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt=app.config['SECURITY_PASSWORD_SALT'], max_age=3600)
    except SignatureExpired:
        return False
    return email

@app.route('/verify-email/<token>')
def verify_email(token):
    email = verify_token(token)
    if not email:
        # token is invalid or expired
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('index'))
    user = User.query.filter_by(email=email).first()
    if not user:
        # user not found
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('index'))
    if user.is_verified:
        # email already verified
        flash('Your email has already been verified.', 'success')
        return redirect(url_for('index'))
    # verify user's email
    user.is_verified = True
    user.verified_on = datetime.utcnow()
    db.session.commit()
    flash('Your email has been verified!', 'success')
    return redirect(url_for('index'))


@app.route('/reset-password/', methods=['GET', 'POST'])
def reset_password_request():
    print(f"reset_password: {request.method} {request.url}")
    if request.method == 'POST':
        # validate form data and send password reset email
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('No account found with that email address.', 'danger')
            return redirect(url_for('reset_password_request'))
        send_reset_email(user)
        flash('A password reset email has been sent to your email address.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    print(f"reset_password: {request.method} {request.url}")
    email = verify_token(token)
    if not email:
        # token is invalid or expired
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('index'))
    user = User.query.filter_by(email=email).first()
    if not user:
        # user not found
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # validate form data and update user's password
        password = request.form['password']
        user.set_password(password)
        db.session.commit()
        flash('Your password has been reset!', 'success')
        return redirect(url_for('login'))

    print(f"Token: {token}")
    return render_template('reset_password.html', token=token)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # validate form data and log in user
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user is not None and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # validate form data and create new user
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        send_verification_email(new_user)
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/')
def index():
    return render_template('index.html')

# This route is for the dashboard page
@app.route('/dashboard', defaults={'page': 1}, methods=['GET', 'POST'])
@app.route('/dashboard/page/<int:page>', methods=['GET', 'POST'])
@login_required
def dashboard(page):
    current_time = datetime.now()
    if request.method == 'POST':
        todo_title = request.form['text']
        if todo_title.strip():  # check if todo_title is not an empty string
            new_todo = Todo(title=todo_title, user_id=current_user.id)
            db.session.add(new_todo)
            db.session.commit()
        return redirect('/dashboard')
    else:
        todos = Todo.query.filter_by(user_id=current_user.id).paginate(page=page, per_page=5)
        return render_template('dashboard.html', todos=todos, current_time=current_time)


# This route is for updating the status of a todo
@app.route('/update/<int:todo_id>')
@login_required
def update(todo_id):
    todo = Todo.query.get(todo_id)
    todo.complete = not todo.complete
    db.session.commit()
    return redirect('/dashboard')


# This route is for deleting a todo
@app.route('/delete/<int:todo_id>')
@login_required
def delete(todo_id):
    todo = Todo.query.get(todo_id)
    db.session.delete(todo)
    db.session.commit()
    return redirect('/dashboard')


# This route is for editing a todo
@app.route('/edit/<int:todo_id>', methods=['GET', 'POST'])
@login_required
def edit(todo_id):
    todo = Todo.query.get(todo_id)
    if request.method == 'POST':
        todo.title = request.form['title']
        db.session.commit()
        return redirect('/dashboard')
    else:
        return render_template('edit.html', todo=todo)

@app.route('/about/')
def about():
    return render_template('about.html')

@app.route('/faq/')
def faq():
    return render_template('faq.html')

@app.errorhandler(404)
def page_not_found(e):
    # your custom 404 error page
    return render_template('404.html'), 404

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        msg = Message('Contact Form Submission',
                      sender='test@teeglad.com.ng',
                      recipients=['tboy.kelly@gmail.com'])
        msg.body = f'''Name: {name}
Email: {email}
Message: {message}
'''
        mail.send(msg)

        flash('Your message has been sent. Thank you!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')



with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)