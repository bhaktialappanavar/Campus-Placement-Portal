import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import re
import time
from datetime import datetime
from flask import request as flask_request
from flaskr.admin_log import log_admin_event
from werkzeug.security import check_password_hash, generate_password_hash
from bson.objectid import ObjectId

from flaskr.db import get_db
from pymongo.errors import DuplicateKeyError

from flask import current_app

bp = Blueprint('auth', __name__)

def init_db_indexes(app):
    """Initialize database indexes for optimal performance"""
    with app.app_context():
        db = get_db()
        # Create indexes for students collection
        db['students'].create_index([('email', 1)], unique=True)
        db['students'].create_index([('username', 1)], unique=True)
        db['students'].create_index([('phone', 1)], unique=True, sparse=True)
        db['students'].create_index([('email', 1), ('password', 1)])
        
        # Create indexes for recruiters collection
        db['recruiters'].create_index([('email', 1)], unique=True)
        db['recruiters'].create_index([('username', 1)], unique=True)
        db['recruiters'].create_index([('phone', 1)], unique=True, sparse=True)
        db['recruiters'].create_index([('company_name', 1)])
        db['recruiters'].create_index([('email', 1), ('password', 1)])

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/auth-select')
def auth_select():
    """Display page to select between student and recruiter authentication"""
    return render_template('auth/auth_select.html')

@bp.route('/student/register', methods=('GET', 'POST'))
def student_register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        db = get_db()
        error = None

        # --- (Your validation logic remains the same) ---
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        password_regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$"

        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not re.match(email_regex, email):
            error = 'Please enter a valid email address.'
        elif not password:
            error = 'Password is required.'
        elif not confirm_password:
            error = 'Please confirm your password.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif not re.match(password_regex, password):
            error = 'Password must be at least 8 characters long, contain an uppercase letter, a lowercase letter, and a digit.'
        # --- (End of validation logic) ---

        if error is None:
            try:
                student_count = db['students'].count_documents({})
                recruiter_count = db['recruiters'].count_documents({})
                is_first_user = (student_count == 0 and recruiter_count == 0)
                
                result = db['students'].insert_one({
                    'username': username,
                    'email': email,
                    'password': generate_password_hash(password),
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                    'profile_complete': False,
                    'is_admin': is_first_user
                })
                
                if is_first_user:
                    log_admin_event('admin_creation', f'Student {username} ({email}) automatically promoted to admin as first user')
                
                log_admin_event("student_registration", f"New student registered: {username} ({email})")
                
                session.clear()
                session['user_id'] = str(result.inserted_id)
                session['user_type'] = 'student'
                
                flash('Registration successful! Please complete your profile to apply for jobs.')
                return redirect(url_for('profile.student_profile'))
                
            except DuplicateKeyError as e:
                # This part is fine and handles existing emails correctly
                error_str = str(e)
                if 'email' in error_str:
                    error = f"Email {email} is already registered."
                elif 'username' in error_str:
                    error = f"Username {username} is already taken."
                else:
                    error = "A registration error occurred. This username or email may already be in use."
                current_app.logger.error(f"Registration DuplicateKeyError: {error_str}")

            # --- START OF FIX ---
            # Add a general exception handler to catch any other errors
            except Exception as e:
                error = "An unexpected error occurred during registration. Please try again later."
                # Log the full, detailed error for you to debug later
                current_app.logger.error(f"An unexpected exception occurred on /student/register: {e}", exc_info=True)
            # --- END OF FIX ---

        # If any error occurred (validation or during try block), flash it
        flash(error)
        
        # Repopulate form data on error
        form_data = {
            'username': username,
            'email': email
        }
        return render_template('auth/student_register.html', form_data=form_data)
        
    # For a GET request, just show the blank form
    return render_template('auth/student_register.html', form_data={})


@bp.route('/recruiter/register', methods=('GET', 'POST'))
def recruiter_register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        db = get_db()
        error = None

        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        password_regex = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$"

        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not re.match(email_regex, email):
            error = 'Please enter a valid email address.'
        elif not password:
            error = 'Password is required.'
        elif not confirm_password:
            error = 'Please confirm your password.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif not re.match(password_regex, password):
            error = 'Password must be at least 8 characters long, contain an uppercase letter, a lowercase letter, and a digit.'

        if error is None:
            try:
                student_count = db['students'].count_documents({})
                recruiter_count = db['recruiters'].count_documents({})
                is_first_user = (student_count == 0 and recruiter_count == 0)
                
                result = db['recruiters'].insert_one({
                    'username': username,
                    'email': email,
                    'password': generate_password_hash(password),
                    'verified': True,
                    'created_at': datetime.now(), # Corrected
                    'updated_at': datetime.now(), # Corrected
                    'profile_complete': False,
                    'is_admin': is_first_user
                })
                
                if is_first_user:
                    log_admin_event('admin_creation', f'Recruiter {username} ({email}) automatically promoted to admin as first user')
                
                log_admin_event("recruiter_registration", f"New recruiter registered: {username} ({email})")
                
                session.clear()
                session['user_id'] = str(result.inserted_id)
                session['user_type'] = 'recruiter'
                
                flash('Registration successful! Please complete your profile with company details to post jobs.')
                return redirect(url_for('profile.recruiter_profile'))
                
            except DuplicateKeyError as e:
                error_str = str(e)
                if 'email' in error_str:
                    error = f"Email {email} is already registered."
                elif 'username' in error_str:
                    error = f"Username {username} is already taken."
                else:
                    error = "An error occurred during registration. Please try again."
                current_app.logger.error(f"Registration error: {error_str}")

            # --- FIX: Added general exception handler ---
            except Exception as e:
                error = "An unexpected error occurred during registration. Please try again later."
                current_app.logger.error(f"An unexpected exception occurred on /recruiter/register: {e}", exc_info=True)

        # If any error occurred, flash it and re-render the form
        flash(error)
        form_data = {'username': username, 'email': email}
        return render_template('auth/recruiter_register.html', form_data=form_data)
        
    # For a GET request, just show the blank form
    return render_template('auth/recruiter_register.html', form_data={})



# Simple in-memory rate limiting (per session)
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_WINDOW = 60  # seconds

@bp.route('/student/login', methods=('GET', 'POST'))
def student_login():
    if 'login_attempts' not in session:
        session['login_attempts'] = []

    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            db = get_db()
            error = None

            email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if not email:
                error = 'Email is required.'
            elif not re.match(email_regex, email):
                error = 'Please enter a valid email address.'
            elif not password:
                error = 'Password is required.'

            now = time.time()
            attempts = [t for t in session['login_attempts'] if now - t < LOGIN_ATTEMPT_WINDOW]
            session['login_attempts'] = attempts

            if len(attempts) >= LOGIN_ATTEMPT_LIMIT:
                error = f'Too many login attempts. Please try again in a minute.'
            
            if error is None:
                user = db['students'].find_one({'email': email})
                
                if user is None:
                    error = 'No student account found with this email.'
                    session['login_attempts'].append(now) # Record failed attempt
                elif not check_password_hash(user['password'], password):
                    error = 'Incorrect password.'
                    session['login_attempts'].append(now) # Record failed attempt

            if error is None:
                db['students'].update_one(
                    {'_id': user['_id']},
                    {'$set': {'last_login': datetime.now()}}
                )
                
                session.clear()
                session['user_id'] = str(user['_id'])
                session['user_type'] = 'student'
                
                log_admin_event('LOGIN_SUCCESS', f'Student login successful | User: {email} | IP: {request.remote_addr}')
                
                return redirect(url_for('index')) # Redirect to profile
            
            flash(error)

        except Exception as e:
            error = "An unexpected error occurred during login. Please try again later."
            current_app.logger.error(f"An unexpected exception occurred on /student/login: {e}", exc_info=True)
            flash(error)
    
    return render_template('auth/student_login.html')

@bp.route('/recruiter/login', methods=('GET', 'POST'))
def recruiter_login():
    if 'login_attempts' not in session:
        session['login_attempts'] = []
        
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            db = get_db()
            error = None
            
            email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            if not email:
                error = 'Email is required.'
            elif not re.match(email_regex, email):
                error = 'Please enter a valid email address.'
            elif not password:
                error = 'Password is required.'
            
            now = time.time()
            attempts = [t for t in session['login_attempts'] if now - t < LOGIN_ATTEMPT_WINDOW]
            session['login_attempts'] = attempts

            if len(attempts) >= LOGIN_ATTEMPT_LIMIT:
                error = f'Too many login attempts. Please try again in a minute.'
            
            if error is None:
                user = db['recruiters'].find_one({'email': email})
                
                if user is None:
                    error = 'No recruiter account found with this email.'
                    session['login_attempts'].append(now)
                elif not check_password_hash(user['password'], password):
                    error = 'Incorrect password.'
                    session['login_attempts'].append(now)
            
            if error is None:
                db['recruiters'].update_one(
                    {'_id': user['_id']},
                    {'$set': {'last_login': datetime.now()}}
                )
                
                session.clear()
                session['user_id'] = str(user['_id'])
                session['user_type'] = 'recruiter'
                
                log_admin_event('LOGIN_SUCCESS', f'Recruiter login successful | User: {email} | IP: {request.remote_addr}')
                
                return redirect(url_for('index')) # Redirect to profile
            
            flash(error)

        except Exception as e:
            error = "An unexpected error occurred during login. Please try again later."
            current_app.logger.error(f"An unexpected exception occurred on /recruiter/login: {e}", exc_info=True)
            flash(error)

    return render_template('auth/recruiter_login.html')


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    user_type = session.get('user_type')

    g.user = None
    if user_id and user_type:
        db = get_db()
        collection = db['students'] if user_type == 'student' else db['recruiters']
        user = collection.find_one({'_id': ObjectId(user_id)})
        if user:
            g.user = user
            g.user['user_type'] = user_type

@bp.route('/logout')
def logout():
    """Log out the current user."""
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    """Decorator to require login for views."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.auth_select'))
        return view(**kwargs)
    return wrapped_view

def student_required(view):
    """Decorator to require student login for views."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user.get('user_type') != 'student':
            flash('You must be logged in as a student to access this page.')
            return redirect(url_for('auth.auth_select'))
        return view(**kwargs)
    return wrapped_view

def recruiter_required(view):
    """Decorator to require recruiter login for views."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user.get('user_type') != 'recruiter':
            flash('You must be logged in as a recruiter to access this page.')
            return redirect(url_for('auth.auth_select'))
        return view(**kwargs)
    return wrapped_view
