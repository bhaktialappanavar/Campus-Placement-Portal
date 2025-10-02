import os
import datetime
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        MONGO_URI=os.getenv('MONGO_URI'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from flask import g, render_template, redirect, url_for
    @app.route('/')
    def index():
        if getattr(g, 'user', None):
            # Check if student profile is complete
            if g.user.get('user_type') == 'student' and not g.user.get('profile_complete', False):
                return redirect(url_for('profile.student_profile'))
            # Check if recruiter profile is complete
            elif g.user.get('user_type') == 'recruiter' and not g.user.get('profile_complete', False):
                return redirect(url_for('profile.recruiter_profile'))
            username = g.user['username']
        else:
            username = None
        return render_template('index.html', username=username)

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    # Initialize database indexes
    auth.init_db_indexes(app)

    # Register admin blueprint
    from . import admin
    app.register_blueprint(admin.bp)


    # Import datetime here to ensure it's available in this scope
    import datetime
    
    # Create first admin user if none exists
    with app.app_context():
        database = db.get_db()
        
        # Check if any admin exists in either students or recruiters collection
        student_admin = database['students'].find_one({'is_admin': True})
        recruiter_admin = database['recruiters'].find_one({'is_admin': True})
        
        if not student_admin and not recruiter_admin:
            # No admin exists, so promote the first user (student or recruiter) to admin
            
            # First check if there are any students
            first_student = database['students'].find_one({}, sort=[('created_at', 1)])
            
            # Then check if there are any recruiters
            first_recruiter = database['recruiters'].find_one({}, sort=[('created_at', 1)])
            
            # Determine which user was registered first (if both exist)
            if first_student and first_recruiter:
                # Compare creation timestamps to find the first registered user
                if first_student.get('created_at', datetime.datetime.max) <= first_recruiter.get('created_at', datetime.datetime.max):
                    # Student was first, promote them
                    database['students'].update_one(
                        {'_id': first_student['_id']},
                        {'$set': {'is_admin': True}}
                    )
                    from flaskr.admin_log import log_admin_event
                    log_admin_event('admin_creation', f'Student {first_student.get("email")} automatically promoted to admin as first user')
                else:
                    # Recruiter was first, promote them
                    database['recruiters'].update_one(
                        {'_id': first_recruiter['_id']},
                        {'$set': {'is_admin': True}}
                    )
                    from flaskr.admin_log import log_admin_event
                    log_admin_event('admin_creation', f'Recruiter {first_recruiter.get("email")} automatically promoted to admin as first user')
            elif first_student:
                # Only students exist, promote the first student
                database['students'].update_one(
                    {'_id': first_student['_id']},
                    {'$set': {'is_admin': True}}
                )
                from flaskr.admin_log import log_admin_event
                log_admin_event('admin_creation', f'Student {first_student.get("email")} automatically promoted to admin as first user')
            elif first_recruiter:
                # Only recruiters exist, promote the first recruiter
                database['recruiters'].update_one(
                    {'_id': first_recruiter['_id']},
                    {'$set': {'is_admin': True}}
                )
                from flaskr.admin_log import log_admin_event
                log_admin_event('admin_creation', f'Recruiter {first_recruiter.get("email")} automatically promoted to admin as first user')
    
    from . import profile
    app.register_blueprint(profile.bp)
    
    # Register jobs blueprint
    from . import jobs
    app.register_blueprint(jobs.bp)
    
    # Register applications blueprint
    from . import applications
    app.register_blueprint(applications.bp)

    return app
