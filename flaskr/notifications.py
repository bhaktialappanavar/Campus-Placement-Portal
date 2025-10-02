import os
import traceback
import re
from twilio.rest import Client
from flask import current_app, flash

def send_sms(to_number, message):
    """
    Send an SMS notification to a user using Twilio.
    
    Args:
        to_number (str): The recipient's phone number in E.164 format (e.g., +1234567890)
        message (str): The message content to send
        
    Returns:
        bool: True if the message was sent successfully, False otherwise
    """
    # Print debug info
    current_app.logger.info(f"Sending SMS to: {to_number}")
    current_app.logger.info(f"Message: {message}")
    
    # Validate phone number format
    if not to_number.startswith('+'):
        # Add +91 prefix for Indian numbers if not already present
        if to_number.startswith('91'):
            to_number = '+' + to_number
        else:
            to_number = '+91' + to_number.lstrip('0')
    
    # Ensure the phone number is in E.164 format (only digits and + sign)
    if not re.match(r'^\+[1-9]\d{1,14}$', to_number):
        current_app.logger.error(f"Invalid phone number format: {to_number}")
        return False
    
    try:
        # Check if Twilio is enabled
        twilio_enabled = os.environ.get('TWILIO_ENABLED', 'False').lower() in ('true', '1', 't')
        if not twilio_enabled:
            current_app.logger.info("Twilio is disabled in .env file. SMS will not be sent.")
            return False
            
        # Get Twilio credentials from environment variables
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
        from_number = os.environ.get('TWILIO_PHONE_NUMBER', '')
        
        # Log the credentials (with partial masking for security)
        if account_sid:
            masked_sid = account_sid[:4] + '****' + account_sid[-4:] if len(account_sid) > 8 else '****'
            current_app.logger.info(f"Using Twilio Account SID: {masked_sid}")
        
        if auth_token:
            masked_token = auth_token[:2] + '****' + auth_token[-2:] if len(auth_token) > 4 else '****'
            current_app.logger.info(f"Using Twilio Auth Token: {masked_token}")
            
        current_app.logger.info(f"Using Twilio phone: {from_number}")
        
        # Check for missing credentials
        if not account_sid or account_sid == "your_account_sid_here" or not account_sid.strip():
            error_msg = "ERROR: Twilio Account SID is missing or invalid in .env file"
            current_app.logger.error(error_msg)
            flash(error_msg, 'error')
            return False
            
        if not auth_token or auth_token == "your_auth_token_here" or not auth_token.strip():
            error_msg = "ERROR: Twilio Auth Token is missing or invalid in .env file"
            current_app.logger.error(error_msg)
            flash(error_msg, 'error')
            return False
            
        if not from_number or from_number == "your_twilio_phone_number_here" or not from_number.strip():
            error_msg = "ERROR: Twilio Phone Number is missing or invalid in .env file"
            current_app.logger.error(error_msg)
            flash(error_msg, 'error')
            return False
        
        # Initialize Twilio client
        current_app.logger.info("Creating Twilio client...")
        client = Client(account_sid, auth_token)
        
        # Send the message
        current_app.logger.info(f"Sending message from {from_number} to {to_number}")
        sms_response = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        
        # Log success
        current_app.logger.info(f"Success! SMS sent with SID: {sms_response.sid}")
        return True
        
    except Exception as e:
        # Log the full error with traceback
        error_msg = f"Failed to send SMS: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        flash(f"SMS notification could not be sent: {str(e)}", 'error')
        return False


def notify_student_shortlisted(student, job):
    """
    Send an SMS notification to a student when they are shortlisted for a job.
    
    Args:
        student (dict): The student document from the database
        job (dict): The job document from the database
        
    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    if not student.get('phone'):
        error_msg = f"Cannot send SMS notification: Student {student.get('_id')} has no phone number"
        current_app.logger.warning(error_msg)
        flash(error_msg, 'warning')
        return False
    
    # Get the phone number from the student record
    to_number = student['phone']
    current_app.logger.info(f"Student phone number from database: {to_number}")
    
    # Create the message
    company_name = job.get('company_name', 'A company')
    job_title = job.get('title', 'a position')
    
    message = f"Congratulations! You have been shortlisted for {job_title} at {company_name}. Log in to CareerBridge to check the details and next steps."
    
    # Send the SMS
    return send_sms(to_number, message)


def notify_student_selected(student, job):
    """
    Send an SMS notification to a student when they are selected for a job.
    
    Args:
        student (dict): The student document from the database
        job (dict): The job document from the database
        
    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    if not student.get('phone'):
        error_msg = f"Cannot send SMS notification: Student {student.get('_id')} has no phone number"
        current_app.logger.warning(error_msg)
        flash(error_msg, 'warning')
        return False
    
    # Get the phone number from the student record
    to_number = student['phone']
    current_app.logger.info(f"Student phone number from database: {to_number}")
    
    # Create the message
    company_name = job.get('company_name', 'A company')
    job_title = job.get('title', 'a position')
    
    message = f"Great news! You have been SELECTED for {job_title} at {company_name}. Congratulations on your success! Log in to CareerBridge for more details."
    
    # Send the SMS
    return send_sms(to_number, message)


def notify_student_interview_scheduled(student, job, interview):
    """
    Send an SMS notification to a student when an interview is scheduled.
    
    Args:
        student (dict): The student document from the database
        job (dict): The job document from the database
        interview (dict): The interview document from the database
        
    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    if not student.get('phone'):
        error_msg = f"Cannot send SMS notification: Student {student.get('_id')} has no phone number"
        current_app.logger.warning(error_msg)
        flash(error_msg, 'warning')
        return False
    
    # Get the phone number from the student record
    to_number = student['phone']
    current_app.logger.info(f"Student phone number from database: {to_number}")
    
    # Format the interview date and time
    interview_datetime = interview.get('interview_datetime')
    formatted_date = interview_datetime.strftime('%d %b, %Y')
    formatted_time = interview_datetime.strftime('%H:%M')
    interview_type = interview.get('interview_type', 'an interview')
    interview_location = interview.get('interview_location', 'to be confirmed')
    
    # Create the message
    company_name = job.get('company_name', 'A company')
    job_title = job.get('title', 'a position')
    
    message = f"Interview Scheduled: {interview_type} interview for {job_title} at {company_name} on {formatted_date} at {formatted_time}. Location: {interview_location}. Log in to CareerBridge for details."
    
    # Send the SMS
    return send_sms(to_number, message)


def notify_student_interview_result(student, job, interview):
    """
    Send an SMS notification to a student when an interview result is updated.
    
    Args:
        student (dict): The student document from the database
        job (dict): The job document from the database
        interview (dict): The interview document from the database
        
    Returns:
        bool: True if the notification was sent successfully, False otherwise
    """
    if not student.get('phone'):
        error_msg = f"Cannot send SMS notification: Student {student.get('_id')} has no phone number"
        current_app.logger.warning(error_msg)
        flash(error_msg, 'warning')
        return False
    
    # Get the phone number from the student record
    to_number = student['phone']
    current_app.logger.info(f"Student phone number from database: {to_number}")
    
    # Get the result
    result = interview.get('result', 'Unknown')
    
    # Create the message
    company_name = job.get('company_name', 'A company')
    job_title = job.get('title', 'a position')
    
    if result == 'Pass':
        message = f"Congratulations! You have passed the interview for {job_title} at {company_name}. Log in to CareerBridge for next steps."
    else:
        message = f"Interview Result: Your interview for {job_title} at {company_name} has been completed. Please log in to CareerBridge to check the details."
    
    # Send the SMS
    return send_sms(to_number, message)
