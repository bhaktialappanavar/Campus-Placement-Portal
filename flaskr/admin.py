import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import os
from flaskr.db import get_db
from flaskr.auth import login_required
from flaskr.admin_log import log_admin_event, get_log_path, get_user_activity_data

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(view):
    """View decorator that requires the user to be an administrator."""
    @functools.wraps(view)
    @login_required
    def wrapped_view(**kwargs):
        # Check if the user has admin privileges
        is_admin = g.user.get('is_admin', False)
        
        if not is_admin:
            log_admin_event('unauthorized_access', 'Non-admin user attempted to access admin area', 
                           user_email=g.user.get('email'), ip=request.remote_addr)
            flash('Administrator privileges required.', 'error')
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

@bp.route('/')
@admin_required
def index():
    """Admin dashboard home page."""
    db = get_db()
    
    # Get user statistics from students and recruiters collections
    total_students = db['students'].count_documents({})
    total_recruiters = db['recruiters'].count_documents({})
    total_users = total_students + total_recruiters
    
    # Get admin users count
    admin_students = db['students'].count_documents({'is_admin': True})
    admin_recruiters = db['recruiters'].count_documents({'is_admin': True})
    admin_users = admin_students + admin_recruiters
    
    # Get login statistics
    one_day_ago = datetime.now() - timedelta(days=1)
    students_logged_in_today = db['students'].count_documents({
        'last_login': {'$gte': one_day_ago}
    })
    recruiters_logged_in_today = db['recruiters'].count_documents({
        'last_login': {'$gte': one_day_ago}
    })
    total_logged_in_today = students_logged_in_today + recruiters_logged_in_today
    
    # Get users who have never logged in
    students_never_logged_in = db['students'].count_documents({
        'last_login': {'$exists': False}
    })
    recruiters_never_logged_in = db['recruiters'].count_documents({
        'last_login': {'$exists': False}
    })
    total_never_logged_in = students_never_logged_in + recruiters_never_logged_in
    
    # Get recent users (limited to 5 each)
    recent_students = list(db['students'].find(
        {},
        {
            'username': 1, 
            'email': 1, 
            'created_at': 1, 
            'last_login': 1,
            'is_admin': 1,
            'profile_complete': 1
        }
    ).sort('created_at', -1).limit(5))
    
    recent_recruiters = list(db['recruiters'].find(
        {},
        {
            'username': 1, 
            'email': 1, 
            'company_name': 1,
            'created_at': 1, 
            'last_login': 1,
            'is_admin': 1,
            'profile_complete': 1
        }
    ).sort('created_at', -1).limit(5))
    
    # Get job and application statistics
    total_jobs = db['jobs'].count_documents({})
    total_applications = db['applications'].count_documents({})
    
    # Get recent registrations (last 7 days)
    one_week_ago = datetime.now() - timedelta(days=7)
    recent_students_count = db['students'].count_documents({
        'created_at': {'$gte': one_week_ago}
    })
    recent_recruiters_count = db['recruiters'].count_documents({
        'created_at': {'$gte': one_week_ago}
    })
    recent_users = recent_students_count + recent_recruiters_count
    
    # Get recent job postings (last 7 days)
    recent_jobs = db['jobs'].count_documents({
        'created_at': {'$gte': one_week_ago}
    })
    
    # Get recent applications (last 7 days)
    recent_applications = db['applications'].count_documents({
        'created_at': {'$gte': one_week_ago}
    })
    
    # Get application status statistics
    application_statuses = {}
    status_pipeline = [
        {
            '$group': {
                '_id': '$status',
                'count': {'$sum': 1}
            }
        }
    ]
    status_results = list(db['applications'].aggregate(status_pipeline))
    for status in status_results:
        application_statuses[status['_id']] = status['count']
    
    # Get recent login activity
    try:
        with open(get_log_path(), 'r') as f:
            log_lines = f.readlines()[-50:]  # Get last 50 lines
            login_activities = [line for line in log_lines if 'LOGIN_' in line]
    except (FileNotFoundError, IOError):
        login_activities = []
    
    # Get user activity data for the chart (default 7 days)
    user_activity = get_user_activity_data(days=7)
    
    log_admin_event('admin_dashboard_access', 'Admin accessed dashboard', 
                   user_email=g.user.get('email'), ip=request.remote_addr)
    
    return render_template('admin/index.html', 
                           total_users=total_users,
                           total_students=total_students,
                           total_recruiters=total_recruiters,
                           admin_users=admin_users,
                           total_jobs=total_jobs,
                           total_applications=total_applications,
                           recent_users=recent_users,
                           recent_jobs=recent_jobs,
                           recent_applications=recent_applications,
                           application_statuses=application_statuses,
                           login_activities=login_activities,
                           user_activity=user_activity,
                           # Login statistics
                           total_logged_in_today=total_logged_in_today,
                           students_logged_in_today=students_logged_in_today,
                           recruiters_logged_in_today=recruiters_logged_in_today,
                           total_never_logged_in=total_never_logged_in,
                           students_never_logged_in=students_never_logged_in,
                           recruiters_never_logged_in=recruiters_never_logged_in,
                           # Recent registration counts
                           recent_students_count=recent_students_count,
                           recent_recruiters_count=recent_recruiters_count,
                           # User lists
                           recent_students=recent_students,
                           recent_recruiters=recent_recruiters,
                           now=datetime.now())

@bp.route('/users')
@admin_required
def users():
    """List all users."""
    db = get_db()
    
    # Get students with type indicator
    students_list = list(db['students'].find({}, {
        'username': 1, 
        'email': 1, 
        'phone': 1, 
        'is_admin': 1,
        'created_at': 1,
        'last_login': 1,
        'profile_complete': 1
    }).sort('created_at', -1))
    
    for student in students_list:
        student['user_type'] = 'student'
    
    # Get recruiters with type indicator
    recruiters_list = list(db['recruiters'].find({}, {
        'username': 1, 
        'email': 1, 
        'phone': 1, 
        'company_name': 1,
        'is_admin': 1,
        'created_at': 1,
        'last_login': 1,
        'profile_complete': 1
    }).sort('created_at', -1))
    
    for recruiter in recruiters_list:
        recruiter['user_type'] = 'recruiter'
    
    # Combine and sort by creation date
    users_list = students_list + recruiters_list
    users_list.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    
    log_admin_event('admin_users_view', 'Admin viewed user list', 
                   user_email=g.user.get('email'), ip=request.remote_addr)
    
    return render_template('admin/users.html', users=users_list)

@bp.route('/users/<user_type>/<id>', methods=('GET', 'POST'))
@admin_required
def user_edit(user_type, id):
    """Edit a user."""
    db = get_db()
    
    # Determine collection based on user type
    if user_type == 'student':
        collection = 'students'
    elif user_type == 'recruiter':
        collection = 'recruiters'
    else:
        flash('Invalid user type.', 'error')
        return redirect(url_for('admin.users'))
    
    user = db[collection].find_one({'_id': ObjectId(id)})
    
    if user is None:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        is_admin = 'is_admin' in request.form
        
        # Check if we're changing the password
        password = request.form.get('password')
        
        # Prepare update document
        update_doc = {
            'username': username,
            'email': email,
            'phone': phone,
            'is_admin': is_admin
        }
        
        if password:
            update_doc['password'] = generate_password_hash(password)
        
        try:
            db[collection].update_one(
                {'_id': ObjectId(id)},
                {'$set': update_doc}
            )
            log_admin_event('admin_user_edit', f'Admin edited user {email}', 
                           user_email=g.user.get('email'), ip=request.remote_addr)
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('admin/user_edit.html', user=user)

@bp.route('/users/delete/<user_type>/<id>', methods=('POST',))
@admin_required
def user_delete(user_type, id):
    """Delete a user."""
    db = get_db()
    
    # Determine collection based on user type
    if user_type == 'student':
        collection = 'students'
    elif user_type == 'recruiter':
        collection = 'recruiters'
    else:
        flash('Invalid user type.', 'error')
        return redirect(url_for('admin.users'))
    
    user = db[collection].find_one({'_id': ObjectId(id)})
    
    if user is None:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    # Don't allow deleting yourself
    if str(user['_id']) == session.get('user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        db[collection].delete_one({'_id': ObjectId(id)})
        log_admin_event('admin_user_delete', f'Admin deleted {user_type} {user.get("email")}', 
                       user_email=g.user.get('email'), ip=request.remote_addr)
        flash(f'{user_type.capitalize()} user deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@bp.route('/logs')
@admin_required
def logs():
    """View admin logs."""
    try:
        with open(get_log_path(), 'r') as f:
            log_content = f.readlines()
    except (FileNotFoundError, IOError):
        log_content = []
    
    # Parse log entries for better display
    parsed_logs = []
    for line in log_content:
        try:
            # Extract timestamp, event type, and message
            parts = line.strip().split(']', 1)
            timestamp = parts[0].strip('[')
            
            # Extract event type
            event_parts = parts[1].split(':', 1)
            event_type = event_parts[0].strip()
            
            # Extract message and additional info
            message_parts = event_parts[1].split('|')
            message = message_parts[0].strip()
            
            # Extract user and IP if available
            user_email = None
            ip = None
            for part in message_parts[1:]:
                if 'User:' in part:
                    user_email = part.split('User:')[1].strip()
                elif 'IP:' in part:
                    ip = part.split('IP:')[1].strip()
            
            parsed_logs.append({
                'timestamp': timestamp,
                'event_type': event_type,
                'message': message,
                'user_email': user_email,
                'ip': ip
            })
        except Exception:
            # If parsing fails, just add the raw line
            parsed_logs.append({
                'timestamp': 'Unknown',
                'event_type': 'PARSE_ERROR',
                'message': line.strip(),
                'user_email': None,
                'ip': None
            })
    
    log_admin_event('admin_logs_view', 'Admin viewed logs', 
                   user_email=g.user.get('email'), ip=request.remote_addr)
    
    return render_template('admin/logs.html', logs=parsed_logs[::-1])  # Reverse to show newest first

@bp.route('/make-admin/<user_type>/<id>', methods=('POST',))
@admin_required
def make_admin(user_type, id):
    """Promote a user to admin status."""
    db = get_db()
    
    # Determine collection based on user type
    if user_type == 'student':
        collection = 'students'
    elif user_type == 'recruiter':
        collection = 'recruiters'
    else:
        flash('Invalid user type.', 'error')
        return redirect(url_for('admin.users'))
    
    user = db[collection].find_one({'_id': ObjectId(id)})
    
    if user is None:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        db[collection].update_one(
            {'_id': ObjectId(id)},
            {'$set': {'is_admin': True}}
        )
        flash('User has been granted admin privileges.', 'success')
        log_admin_event('admin_make_admin', f'Admin granted admin privileges to {user_type} {user.get("email")}', 
                       user_email=g.user.get('email'), ip=request.remote_addr)
    except Exception as e:
        flash(f'Error granting admin privileges: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@bp.route('/revoke-admin/<user_type>/<id>', methods=('POST',))
@admin_required
def revoke_admin(user_type, id):
    """Revoke admin status from a user."""
    db = get_db()
    
    # Determine collection based on user type
    if user_type == 'student':
        collection = 'students'
    elif user_type == 'recruiter':
        collection = 'recruiters'
    else:
        flash('Invalid user type.', 'error')
        return redirect(url_for('admin.users'))
    
    user = db[collection].find_one({'_id': ObjectId(id)})
    
    if user is None:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    # Don't allow revoking admin from self
    if str(user['_id']) == session.get('user_id'):
        flash('You cannot revoke your own admin privileges.', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        db[collection].update_one(
            {'_id': ObjectId(id)},
            {'$set': {'is_admin': False}}
        )
        log_admin_event('admin_demotion', f'Admin privileges revoked from {user_type} {user.get("email")}', 
                       user_email=g.user.get('email'), ip=request.remote_addr)
        flash(f'Admin privileges revoked from {user.get("username")}.', 'success')
    except Exception as e:
        flash(f'Error revoking admin status: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))
