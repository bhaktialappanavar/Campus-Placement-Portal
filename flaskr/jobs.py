import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)
from werkzeug.exceptions import abort
from bson.objectid import ObjectId
import datetime

from flaskr.db import get_db
from flaskr.auth import login_required, recruiter_required, student_required

bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@bp.route('/')
def index():
    """Show all job listings with filtering options."""
    db = get_db()
    
    # Retrieve job listings without debug messages
    
    # Get filter parameters
    min_cgpa = request.args.get('min_cgpa', type=float)
    branch = request.args.get('branch')
    company = request.args.get('company')
    job_type = request.args.get('job_type')
    location = request.args.get('location')
    
    # Build the query
    query = {}
    
    if min_cgpa is not None:
        # Convert to float to ensure proper comparison
        min_cgpa_float = float(min_cgpa)
        query['min_cgpa'] = {'$lte': min_cgpa_float}
    
    if branch:
        query['eligible_branches'] = branch
    
    if company:
        query['company_name'] = {'$regex': company, '$options': 'i'}
    
    if job_type:
        query['job_type'] = job_type
    
    if location:
        query['location'] = {'$regex': location, '$options': 'i'}
    
    try:
        # Get all job listings that match the query
        jobs = list(db['jobs'].find(query).sort('created_at', -1))
        
        # Process job listings without debug messages
        
        # Convert ObjectId to string for each job
        for job in jobs:
            job['_id'] = str(job['_id'])
        
        # Get unique values for filter dropdowns
        all_branches = []
        all_companies = []
        all_job_types = []
        all_locations = []
        
        # Get all jobs for dropdown values if no jobs match the query
        all_jobs = list(db['jobs'].find())
        
        # Extract unique values for dropdowns
        for job in all_jobs:
            # Handle branches (which is a list)
            if 'eligible_branches' in job and job['eligible_branches']:
                for branch_item in job['eligible_branches']:
                    if branch_item and branch_item not in all_branches:
                        all_branches.append(branch_item)
            
            # Handle other fields
            if 'company_name' in job and job['company_name'] and job['company_name'] not in all_companies:
                all_companies.append(job['company_name'])
            
            if 'job_type' in job and job['job_type'] and job['job_type'] not in all_job_types:
                all_job_types.append(job['job_type'])
            
            if 'location' in job and job['location'] and job['location'] not in all_locations:
                all_locations.append(job['location'])
        
        # Check eligibility for each job if user is a student
        if g.user and g.user.get('user_type') == 'student':
            student_cgpa = g.user.get('cgpa', 0)
            student_branch = g.user.get('branch', '')
            
            for job in jobs:
                job['is_eligible'] = (
                    student_cgpa >= job.get('min_cgpa', 0) and
                    (not job.get('eligible_branches') or student_branch in job.get('eligible_branches', []))
                )
    except Exception as e:
        flash(f'Error retrieving job listings: {str(e)}', 'error')
        jobs = []
        all_branches = []
        all_companies = []
        all_job_types = []
        all_locations = []
    
    return render_template('jobs/index.html', 
                          jobs=jobs,
                          all_branches=all_branches,
                          all_companies=all_companies,
                          all_job_types=all_job_types,
                          all_locations=all_locations,
                          filters={
                              'min_cgpa': min_cgpa,
                              'branch': branch,
                              'company': company,
                              'job_type': job_type,
                              'location': location
                          })

@bp.route('/create', methods=('GET', 'POST'))
@recruiter_required
def create():
    """Create a new job listing."""
    # Check profile completion status
    profile_complete = g.user.get('profile_complete', False)
    
    # Always allow job creation (removing the profile check temporarily)
    # if not profile_complete:
    #     flash('Please complete your profile before posting jobs.', 'warning')
    #     return redirect(url_for('profile.recruiter_profile'))
        
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        company_name = request.form['company_name']
        location = request.form['location']
        job_type = request.form['job_type']
        salary_range = request.form['salary_range']
        min_cgpa = float(request.form['min_cgpa'])
        eligible_branches = request.form.getlist('eligible_branches')
        application_deadline = request.form['application_deadline']
        
        error = None
        
        if not title:
            error = 'Title is required.'
        elif not description:
            error = 'Description is required.'
        elif not company_name:
            error = 'Company name is required.'
        elif not location:
            error = 'Location is required.'
        elif not job_type:
            error = 'Job type is required.'
        elif not min_cgpa:
            error = 'Minimum CGPA is required.'
        elif not eligible_branches:
            error = 'At least one eligible branch is required.'
        elif not application_deadline:
            error = 'Application deadline is required.'
        
        if error is None:
            try:
                db = get_db()
                
                # Format the deadline as a datetime object
                deadline_date = datetime.datetime.strptime(application_deadline, '%Y-%m-%d')
                
                # Create job without debug messages
                
                # Insert the job
                result = db['jobs'].insert_one({
                    'title': title,
                    'description': description,
                    'company_name': company_name,
                    'location': location,
                    'job_type': job_type,
                    'salary_range': salary_range,
                    'min_cgpa': min_cgpa,
                    'eligible_branches': eligible_branches,
                    'application_deadline': deadline_date,
                    'created_at': datetime.datetime.now(),
                    'recruiter_id': g.user['_id'],
                    'recruiter_name': g.user.get('full_name', 'Recruiter'),
                    'company_logo': g.user.get('company_logo', '')
                })
                
                if not result.inserted_id:
                    flash('Failed to create job listing. Please try again.', 'error')
            except Exception as e:
                error = f'An error occurred: {str(e)}'
                flash(error, 'error')
                return render_template('jobs/create.html', branches=branches, job_types=job_types)
            
            # Success message removed
            return redirect(url_for('jobs.index'))
        
        flash(error, 'error')
    
    # Get all branches for the form
    branches = [
        'Computer Science',
        'Information Technology',
        'Electronics',
        'Electrical',
        'Mechanical',
        'Civil',
        'Chemical',
        'Biotechnology',
        'Other'
    ]
    
    # Get job types for the form
    job_types = [
        'Full-time',
        'Part-time',
        'Internship',
        'Contract',
        'Remote'
    ]
    
    return render_template('jobs/create.html', branches=branches, job_types=job_types)

@bp.route('/<id>')
def detail(id):
    """Show a single job listing."""
    job = get_job(id)
    
    # Check eligibility if user is a student
    if g.user and g.user.get('user_type') == 'student':
        student_cgpa = g.user.get('cgpa', 0)
        student_branch = g.user.get('branch', '')
        
        job['is_eligible'] = (
            student_cgpa >= job.get('min_cgpa', 0) and
            (not job.get('eligible_branches') or student_branch in job.get('eligible_branches', []))
        )
    
    # Check if student has already applied
    has_applied = False
    if g.user and g.user.get('user_type') == 'student':
        db = get_db()
        application = db['applications'].find_one({
            'job_id': ObjectId(id),
            'student_id': g.user['_id']
        })
        has_applied = application is not None
    
    # Pass the current datetime to the template
    now = datetime.datetime.now()
    
    return render_template('jobs/detail.html', job=job, has_applied=has_applied, now=now)

@bp.route('/<id>/update', methods=('GET', 'POST'))
@recruiter_required
def update(id):
    """Update a job listing."""
    job = get_job(id)
    
    # Check if the current user is the creator of this job listing
    if g.user['_id'] != job['recruiter_id']:
        abort(403)
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        job_type = request.form['job_type']
        salary_range = request.form['salary_range']
        min_cgpa = float(request.form['min_cgpa'])
        eligible_branches = request.form.getlist('eligible_branches')
        application_deadline = request.form['application_deadline']
        
        error = None
        
        if not title:
            error = 'Title is required.'
        elif not description:
            error = 'Description is required.'
        elif not location:
            error = 'Location is required.'
        elif not job_type:
            error = 'Job type is required.'
        elif not min_cgpa:
            error = 'Minimum CGPA is required.'
        elif not eligible_branches:
            error = 'At least one eligible branch is required.'
        elif not application_deadline:
            error = 'Application deadline is required.'
        
        if error is None:
            db = get_db()
            
            # Format the deadline as a datetime object
            deadline_date = datetime.datetime.strptime(application_deadline, '%Y-%m-%d')
            
            db['jobs'].update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'title': title,
                    'description': description,
                    'location': location,
                    'job_type': job_type,
                    'salary_range': salary_range,
                    'min_cgpa': min_cgpa,
                    'eligible_branches': eligible_branches,
                    'application_deadline': deadline_date,
                    'updated_at': datetime.datetime.now()
                }}
            )
            
            flash('Job listing updated successfully!', 'success')
            return redirect(url_for('jobs.detail', id=id))
        
        flash(error, 'error')
    
    # Get all branches for the form
    branches = [
        'Computer Science',
        'Information Technology',
        'Electronics',
        'Electrical',
        'Mechanical',
        'Civil',
        'Chemical',
        'Biotechnology',
        'Other'
    ]
    
    # Get job types for the form
    job_types = [
        'Full-time',
        'Part-time',
        'Internship',
        'Contract',
        'Remote'
    ]
    
    # Format the deadline for the form
    if isinstance(job.get('application_deadline'), datetime.datetime):
        job['application_deadline_formatted'] = job['application_deadline'].strftime('%Y-%m-%d')
    
    # Pass the current datetime to the template
    now = datetime.datetime.now()
    
    return render_template('jobs/update.html', job=job, branches=branches, job_types=job_types, now=now)

@bp.route('/<id>/delete', methods=('POST',))
@recruiter_required
def delete(id):
    """Delete a job listing."""
    job = get_job(id)
    
    # Check if the current user is the creator of this job listing
    if g.user['_id'] != job['recruiter_id']:
        abort(403)
    
    db = get_db()
    db['jobs'].delete_one({'_id': ObjectId(id)})
    
    flash('Job listing deleted successfully!', 'success')
    return redirect(url_for('jobs.index'))

@bp.route('/<id>/apply', methods=('POST',))
@student_required
def apply(id):
    """Apply for a job."""
    # Check if student profile is complete
    if not g.user.get('profile_complete', False):
        flash('Please complete your profile before applying for jobs.', 'warning')
        return redirect(url_for('profile.student_profile'))
        
    job = get_job(id)
    db = get_db()
    
    # Check if student has already applied
    existing_application = db['applications'].find_one({
        'job_id': ObjectId(id),
        'student_id': g.user['_id']
    })
    
    if existing_application:
        flash('You have already applied for this job.', 'warning')
        return redirect(url_for('jobs.detail', id=id))
    
    # Check eligibility
    student_cgpa = g.user.get('cgpa', 0)
    student_branch = g.user.get('branch', '')
    
    is_eligible = (
        student_cgpa >= job.get('min_cgpa', 0) and
        (not job.get('eligible_branches') or student_branch in job.get('eligible_branches', []))
    )
    
    if not is_eligible:
        flash('You do not meet the eligibility criteria for this job.', 'error')
        return redirect(url_for('jobs.detail', id=id))
    
    # Create application
    db['applications'].insert_one({
        'job_id': ObjectId(id),
        'student_id': g.user['_id'],
        'student_name': g.user.get('full_name', ''),
        'student_email': g.user.get('email', ''),
        'student_phone': g.user.get('phone', ''),
        'student_cgpa': student_cgpa,
        'student_branch': student_branch,
        'job_title': job.get('title', ''),
        'company_name': job.get('company_name', ''),
        'status': 'Applied',
        'created_at': datetime.datetime.now()
    })
    
    flash('Application submitted successfully!', 'success')
    return redirect(url_for('jobs.detail', id=id))

@bp.route('/my-listings')
@recruiter_required
def my_listings():
    """Show job listings created by the current recruiter."""
    db = get_db()
    
    try:
        # Get jobs created by the current recruiter
        jobs = list(db['jobs'].find({'recruiter_id': g.user['_id']}).sort('created_at', -1))
        
        # Convert ObjectId to string for each job
        for job in jobs:
            job_id = job['_id']
            job['_id'] = str(job['_id'])
            
            # Count applications for each job - use the ObjectId for querying
            job['application_count'] = db['applications'].count_documents({'job_id': job_id})
    except Exception as e:
        flash(f'Error retrieving job listings: {str(e)}', 'error')
        jobs = []
    
    # Pass the current datetime to the template
    now = datetime.datetime.now()
    
    return render_template('jobs/my_listings.html', jobs=jobs, now=now)

@bp.route('/my-applications')
@student_required
def my_applications():
    """Show job applications submitted by the current student."""
    db = get_db()
    
    try:
        applications = list(db['applications'].find({'student_id': g.user['_id']}).sort('created_at', -1))
        
        # Get job details for each application
        for app in applications:
            # Ensure the application ID is a string
            app['_id'] = str(app['_id'])
            
            if 'job_id' in app:
                # Store the original job_id (ObjectId)
                original_job_id = app['job_id']
                
                # Convert job_id to string for template use
                app['job_id'] = str(app['job_id'])
                
                # Get the job details
                job = db['jobs'].find_one({'_id': original_job_id})
                if job:
                    # Convert ObjectId to string
                    job['_id'] = str(job['_id'])
                    
                    # Store job details directly in the application object
                    # This ensures the template has access to job details even without nested access
                    if 'job_title' not in app or not app['job_title']:
                        app['job_title'] = job.get('title', 'Unknown Job')
                    if 'company_name' not in app or not app['company_name']:
                        app['company_name'] = job.get('company_name', 'Unknown Company')
                        
                    # Store job as a separate property for templates that expect it
                    app['job'] = job
    except Exception as e:
        flash(f'Error retrieving applications: {str(e)}', 'error')
        applications = []
    
    # Pass the current datetime to the template
    now = datetime.datetime.now()
    
    return render_template('jobs/my_applications.html', applications=applications, now=now)

def get_job(id):
    """Get a job by id."""
    try:
        db = get_db()
        job = db['jobs'].find_one({'_id': ObjectId(id)})
    except:
        abort(404, f"Job id {id} doesn't exist.")
        
    if job is None:
        abort(404, f"Job id {id} doesn't exist.")
        
    return job
