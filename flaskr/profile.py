from flask import (Blueprint, flash, g, redirect, render_template, request, session, url_for, send_file, current_app, jsonify)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
import re
import datetime
import os
import uuid
from flask import Blueprint, flash, g, redirect, render_template, request, url_for, send_from_directory
from flaskr.auth import login_required, student_required, recruiter_required
from flaskr.db import get_db

bp = Blueprint('profile', __name__, url_prefix='/profile')

# Configure upload folder - use /tmp for serverless environments like Vercel
# /tmp is the only writable directory in AWS Lambda/Vercel serverless functions
UPLOAD_FOLDER = '/tmp/uploads'
RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')
PROFILE_PHOTOS_FOLDER = os.path.join(UPLOAD_FOLDER, 'profile_photos')
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'jpg', 'jpeg'}
ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

def ensure_upload_dirs():
    """Create upload directories if they don't exist - call this lazily, not at import time"""
    try:
        os.makedirs(RESUME_FOLDER, exist_ok=True)
        os.makedirs(PROFILE_PHOTOS_FOLDER, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create upload directories: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_photo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS

@bp.route('/')
@login_required
def index():
    """Redirect to the appropriate profile page based on user type"""
    if g.user['user_type'] == 'student':
        return redirect(url_for('profile.student_profile'))
    elif g.user['user_type'] == 'recruiter':
        return redirect(url_for('profile.recruiter_profile'))
    return redirect(url_for('index'))

@bp.route('/user')
@login_required
def user():
    """Display appropriate user profile based on user type"""
    if g.user['user_type'] == 'student':
        return redirect(url_for('profile.student_view'))
    elif g.user['user_type'] == 'recruiter':
        return redirect(url_for('profile.recruiter_view'))
    return render_template('prof/user.html')

@bp.route('/student/view')
@bp.route('/student/view/<student_id>')
@login_required
def student_view(student_id=None):
    """Display student profile view"""
    db = get_db()
    
    # If student_id is provided, load that student's profile
    # Only recruiters can view other students' profiles
    if student_id and g.user['user_type'] == 'recruiter':
        student = db['students'].find_one({'_id': ObjectId(student_id)})
        if not student:
            flash('Student not found', 'error')
            return redirect(url_for('index'))
    elif g.user['user_type'] == 'student':
        # Students can only view their own profile
        student = g.user
    else:
        flash('You do not have permission to view this profile', 'error')
        return redirect(url_for('index'))
    
    return render_template('prof/student_view.html', student=student)

@bp.route('/recruiter/view')
@recruiter_required
def recruiter_view():
    """Display recruiter profile view"""
    return render_template('prof/recruiter_view.html', recruiter=g.user)

@bp.route('/resume/<student_id>')
@login_required
def download_resume(student_id):
    """Download a student's resume"""
    db = get_db()
    
    # Get the student
    student = db['students'].find_one({'_id': ObjectId(student_id)})
    
    if not student or not student.get('resume_url'):
        flash('Resume not found', 'error')
        return redirect(url_for('index'))
    
    # Security check: Only allow recruiters or the student themselves to view the resume
    if g.user['user_type'] != 'recruiter' and str(g.user['_id']) != str(student['_id']):
        flash('You do not have permission to view this resume', 'error')
        return redirect(url_for('index'))
    
    # Get the resume file path
    resume_path = os.path.join(RESUME_FOLDER, student['resume_url'])
    
    if not os.path.exists(resume_path):
        flash('Resume file not found', 'error')
        return redirect(url_for('index'))
    
    # Generate a display filename
    display_filename = f"{student['full_name'].replace(' ', '_')}_Resume.pdf"
    
    # Return the file
    return send_file(resume_path, as_attachment=True, download_name=display_filename)

@bp.route('/resume/view/<student_id>')
@login_required
def view_resume(student_id):
    """View a student's resume inline (not as download)"""
    db = get_db()
    student = db['students'].find_one({'_id': ObjectId(student_id)})
    
    if not student or not student.get('resume_url'):
        flash('Resume not found', 'error')
        return redirect(url_for('index'))
    
    # Check if the current user is the student or a recruiter
    if g.user['user_type'] != 'recruiter' and str(g.user['_id']) != str(student['_id']):
        flash('You do not have permission to view this resume', 'error')
        return redirect(url_for('index'))
    
    resume_path = os.path.join(RESUME_FOLDER, student['resume_url'])
    
    if not os.path.exists(resume_path):
        flash('Resume file not found', 'error')
        return redirect(url_for('index'))
    
    # Determine file type based on extension
    file_extension = student['resume_url'].rsplit('.', 1)[1].lower() if '.' in student['resume_url'] else ''
    
    # Set appropriate MIME type based on file extension
    if file_extension in ['pdf']:
        mimetype = 'application/pdf'
    elif file_extension in ['doc', 'docx']:
        # For Word documents, always set as attachment to force download
        mimetype = 'application/msword'
        if file_extension == 'docx':
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        # Return Word documents as attachments (force download)
        return send_file(resume_path, mimetype=mimetype, as_attachment=True)
    elif file_extension in ['jpg', 'jpeg']:
        mimetype = 'image/jpeg'
    else:
        mimetype = 'application/octet-stream'  # Default binary file type
    
    # Store the file extension in the session for the frontend to use
    session['resume_file_type'] = file_extension
    
    # Return the file for inline viewing (not as attachment) for non-Word documents
    return send_file(resume_path, mimetype=mimetype)

@bp.route('/student', methods=('GET', 'POST'))
@student_required
def student_profile():
    """Handle student profile completion and updates"""
    db = get_db()
    student = g.user
    form_data = {}
    
    if request.method == 'POST':
        # Ensure upload directories exist before processing uploads
        ensure_upload_dirs()
        
        # Get form data - Personal Information
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        dob = request.form.get('dob', '').strip()
        gender = request.form.get('gender', '').strip()
        address = request.form.get('address', '').strip()
        
        # Get form data - Academic Information
        college = request.form.get('college', '').strip()
        branch = request.form.get('branch', '').strip()
        degree = request.form.get('degree', '').strip()
        current_year = request.form.get('current_year', '').strip()
        graduation_year = request.form.get('graduation_year', '').strip()
        cgpa = request.form.get('cgpa', '').strip()
        tenth_marks = request.form.get('tenth_marks', '').strip()
        twelfth_marks = request.form.get('twelfth_marks', '').strip()
        backlogs = request.form.get('backlogs', '0').strip()
        
        # Get form data - Skills & Qualifications
        technical_skills = request.form.get('technical_skills', '').strip()
        soft_skills = request.form.get('soft_skills', '').strip()
        certifications = request.form.get('certifications', '').strip()
        
        # Get resume file and profile photo
        resume_file = request.files.get('resume')
        profile_photo = request.files.get('profile_photo')
        
        # Create form_data dictionary to preserve user input in case of validation errors
        form_data = {
            '_id': student['_id'],
            'email': student['email'],
            'full_name': full_name,
            'phone': f"+91{phone}" if phone else '',
            'dob': dob,  # Keep as string for now
            'gender': gender,
            'address': address,
            'college': college,
            'branch': branch,
            'degree': degree,
            'current_year': current_year,
            'graduation_year': graduation_year,
            'cgpa': cgpa,
            'tenth_marks': tenth_marks,
            'twelfth_marks': twelfth_marks,
            'backlogs': backlogs,
            'technical_skills': technical_skills,
            'soft_skills': soft_skills,
            'certifications': certifications,
            'resume_url': student.get('resume_url'),
            'profile_photo_url': student.get('profile_photo_url'),
            'resume_updated_at': student.get('resume_updated_at'),
            'photo_updated_at': student.get('photo_updated_at'),
            'profile_complete': student.get('profile_complete', False)
        }
        
        error = None
        
        # Phone number validation: exactly 10 digits starting with 6, 7, 8, or 9
        phone_regex = r"^[6-9]\d{9}$"
        
        # Validate required fields
        if not full_name:
            error = 'Full name is required.'
        elif not phone:
            error = 'Phone number is required.'
        elif not re.match(phone_regex, phone):
            error = 'Please enter a valid 10-digit phone number starting with 6, 7, 8, or 9.'
        elif not dob:
            error = 'Date of birth is required.'
        elif not gender:
            error = 'Gender is required.'
        elif not address:
            error = 'Address is required.'
        elif not college:
            error = 'College name is required.'
        elif not branch:
            error = 'Branch is required.'
        elif not degree:
            error = 'Degree is required.'
        elif not current_year:
            error = 'Current year is required.'
        elif not graduation_year:
            error = 'Graduation year is required.'
        elif not cgpa:
            error = 'CGPA is required.'
        # Resume validation - required if not already uploaded
        elif not student.get('resume_url') and (not resume_file or resume_file.filename == ''):
            error = 'Resume is required. Please upload your resume in PDF, Word (doc/docx), or JPEG format.'
        elif resume_file and resume_file.filename != '' and not allowed_file(resume_file.filename):
            error = 'Only PDF, Word (doc/docx), and JPEG files are allowed for resume upload.'
        elif profile_photo and profile_photo.filename != '' and not allowed_photo_file(profile_photo.filename):
            error = 'Only JPG, JPEG, and PNG files are allowed for profile photos.'
            
        if error is None:
            try:
                # Convert date string to datetime object
                dob_date = datetime.datetime.strptime(dob, '%Y-%m-%d')
                
                # Prepare update data
                update_data = {
                    # Personal Information
                    'full_name': full_name,
                    'phone': f"+91{phone}",
                    'dob': dob_date,
                    'gender': gender,
                    'address': address,
                    
                    # Academic Information
                    'college': college,
                    'branch': branch,
                    'degree': degree,
                    'current_year': current_year,
                    'graduation_year': int(graduation_year),
                    'cgpa': float(cgpa),
                    'profile_complete': True,
                    'updated_at': datetime.datetime.now()
                }
                
                # Add optional fields if provided
                if tenth_marks:
                    update_data['tenth_marks'] = float(tenth_marks)
                if twelfth_marks:
                    update_data['twelfth_marks'] = float(twelfth_marks)
                if backlogs:
                    update_data['backlogs'] = int(backlogs)
                
                # Add skills and qualifications
                update_data['technical_skills'] = technical_skills
                update_data['soft_skills'] = soft_skills
                update_data['certifications'] = certifications
                
                try:
                    # Check if phone number already exists for another user
                    phone_with_code = f"+91{phone}"
                    existing_user = db['students'].find_one({
                        '_id': {'$ne': ObjectId(student['_id'])},
                        'phone': phone_with_code
                    })
                    
                    if existing_user:
                        error = 'This phone number is already registered with another account.'
                        flash(error, 'error')
                        return render_template('prof/student_profile.html', student=student)
                    
                    # Handle resume upload if provided
                    if resume_file and resume_file.filename != '':
                        # Generate a unique filename
                        filename = secure_filename(resume_file.filename)
                        file_ext = filename.rsplit('.', 1)[1].lower()
                        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                        file_path = os.path.join(RESUME_FOLDER, unique_filename)
                        
                        # Save the file
                        resume_file.save(file_path)
                        
                        # Update resume URL in database
                        update_data['resume_url'] = unique_filename
                        update_data['resume_filename'] = filename
                        update_data['resume_updated_at'] = datetime.datetime.now()
                    
                    # Handle profile photo upload if provided
                    if profile_photo and profile_photo.filename != '':
                        # Generate a unique filename
                        photo_filename = secure_filename(profile_photo.filename)
                        photo_ext = photo_filename.rsplit('.', 1)[1].lower()
                        unique_photo_filename = f"{uuid.uuid4().hex}.{photo_ext}"
                        photo_path = os.path.join(PROFILE_PHOTOS_FOLDER, unique_photo_filename)
                        
                        # Save the file
                        profile_photo.save(photo_path)
                        
                        # Update profile photo URL in database
                        update_data['profile_photo_url'] = unique_photo_filename
                        update_data['photo_updated_at'] = datetime.datetime.now()
                
                    # Update student profile
                    db['students'].update_one(
                        {'_id': ObjectId(student['_id'])},
                        {'$set': update_data}
                    )
                    
                    # Update the session user data
                    g.user.update(update_data)
                    
                    flash('Profile updated successfully!', 'success')
                    return redirect(url_for('index'))
                except Exception as e:
                    if 'duplicate key error' in str(e).lower():
                        error = 'This phone number is already registered with another account.'
                    else:
                        error = f'An error occurred: {str(e)}'
                    flash(error, 'error')
                    return render_template('prof/student_profile.html', student=form_data)
            except Exception as e:
                error = f'An error occurred: {str(e)}'
                flash(error, 'error')
                return render_template('prof/student_profile.html', student=form_data)
        else:
            flash(error, 'error')
            
            return render_template('prof/student_profile.html', student=form_data)
    
    # Pre-populate form with existing data if available
    return render_template('prof/student_profile.html', student=student)

@bp.route('/recruiter', methods=('GET', 'POST'))
@recruiter_required
def recruiter_profile():
    """Handle recruiter profile completion and updates"""
    db = get_db()
    recruiter = g.user
    form_data = {}
    
    if request.method == 'POST':
        # Ensure upload directories exist before processing uploads
        ensure_upload_dirs()
        
        # Get form data
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        company_name = request.form.get('company_name', '').strip()
        company_website = request.form.get('company_website', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        industry = request.form.get('industry', '').strip()
        designation = request.form.get('designation', '').strip()
        
        # Get profile photo
        profile_photo = request.files.get('profile_photo')
        
        # Create form_data dictionary to preserve user input in case of validation errors
        formatted_phone = f"+91{phone}" if phone else ''
        form_data = {
            '_id': recruiter['_id'],
            'email': recruiter['email'],
            'full_name': full_name,
            'phone': formatted_phone,
            'company_name': company_name,
            'company_website': company_website,
            'linkedin_url': linkedin_url,
            'industry': industry,
            'designation': designation,
            'profile_photo_url': recruiter.get('profile_photo_url'),
            'photo_updated_at': recruiter.get('photo_updated_at'),
            'profile_complete': recruiter.get('profile_complete', False)
        }
        
        # Eligibility criteria and job details removed
        
        error = None
        
        # Phone number validation: exactly 10 digits starting with 6, 7, 8, or 9
        phone_regex = r"^[6-9]\d{9}$"
        
        if not full_name:
            error = 'Full name is required.'
        elif not phone:
            error = 'Phone number is required.'
        elif not re.match(phone_regex, phone):
            if len(phone) != 10:
                error = 'Please enter a valid 10-digit phone number.'
            elif not phone[0] in ['6', '7', '8', '9']:
                error = 'Phone number must start with 6, 7, 8, or 9.'
            else:
                error = 'Please enter a valid 10-digit phone number.'
        elif not company_name:
            error = 'Company name is required.'
        elif not industry:
            error = 'Industry is required.'
        elif not designation:
            error = 'Your designation is required.'
        elif profile_photo and profile_photo.filename != '' and not allowed_photo_file(profile_photo.filename):
            error = 'Only JPG, JPEG, and PNG files are allowed for profile photos.'
            
        if error is None:
            # Check if phone number is already used by another recruiter
            formatted_phone = f"+91{phone}"
            existing_phone = db['recruiters'].find_one({
                '_id': {'$ne': ObjectId(recruiter['_id'])},  # Not the current user
                'phone': formatted_phone
            })
            
            if existing_phone:
                error = 'This phone number is already registered by another recruiter.'
                
                flash(error, 'error')
                return render_template('prof/recruiter_profile.html', recruiter=form_data)
            else:
                try:
                    # CGPA conversion removed
                        
                    # Create update data dictionary
                    update_data = {
                        'full_name': full_name,
                        'phone': formatted_phone,
                        'company_name': company_name,
                        'company_website': company_website,
                        'linkedin_url': linkedin_url,
                        'industry': industry,
                        'designation': designation,
                        'profile_complete': True,
                        'updated_at': datetime.datetime.now()
                    }
                    
                    # Handle profile photo upload if provided
                    if profile_photo and profile_photo.filename != '':
                        # Generate a unique filename
                        photo_filename = secure_filename(profile_photo.filename)
                        photo_ext = photo_filename.rsplit('.', 1)[1].lower()
                        unique_photo_filename = f"{uuid.uuid4().hex}.{photo_ext}"
                        photo_path = os.path.join(PROFILE_PHOTOS_FOLDER, unique_photo_filename)
                        
                        # Save the file
                        profile_photo.save(photo_path)
                        
                        # Update profile photo URL in database
                        update_data['profile_photo_url'] = unique_photo_filename
                        update_data['photo_updated_at'] = datetime.datetime.now()
                    
                    # Update recruiter profile in database
                    db['recruiters'].update_one(
                        {'_id': ObjectId(recruiter['_id'])},
                        {'$set': update_data}
                    )
                    
                    # Update the session user data
                    g.user.update(update_data)
                except Exception as e:
                    error = f'An error occurred while updating your profile: {str(e)}'
                    
                    flash(error, 'error')
                    return render_template('prof/recruiter_profile.html', recruiter=form_data)
            
            if error is None:
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('profile.recruiter_view'))
        
        # If we get here, there was a validation error
        flash(error, 'error')
        
        # Preserve form data by creating a temporary recruiter object with form values
        form_data = {
            '_id': recruiter['_id'],
            'email': recruiter['email'],
            'full_name': full_name,
            'phone': f"+91{phone}",
            'company_name': company_name,
            'company_website': company_website,
            'linkedin_url': linkedin_url,
            'industry': industry,
            'designation': designation,
            'profile_photo_url': recruiter.get('profile_photo_url'),
            'photo_updated_at': recruiter.get('photo_updated_at')
        }
        
        return render_template('prof/recruiter_profile.html', recruiter=form_data)
    
    # Pre-populate form with existing data if available
    return render_template('prof/recruiter_profile.html', recruiter=recruiter)

@bp.route('/profile-photo/<filename>')
def profile_photo(filename):
    """Serve profile photos"""
    return send_from_directory(PROFILE_PHOTOS_FOLDER, filename)