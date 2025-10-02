# CareerBridge: Campus Placement Portal

## 🚀 Overview

CareerBridge is a comprehensive campus placement management system designed to streamline the recruitment process for educational institutions. It connects students, recruiters, and administrators in a unified platform, making the job application and hiring process more efficient and transparent.

This application addresses the challenges faced in traditional placement processes by providing a centralized solution for tracking placement-related events, company listings, and job applications.

## ✨ Key Features

### For Students
- **Profile Management**: Create and manage comprehensive profiles with academic details, skills, and resume uploads
- **Job Discovery**: Browse and filter job listings based on eligibility criteria (CGPA, branch, etc.)
- **Application Tracking**: Apply to jobs and track application status in real-time
- **Interview Management**: Receive notifications about interviews and view schedules
- **SMS Notifications**: Get real-time updates about application status changes and interview schedules

### For Recruiters
- **Company Profile**: Create detailed company profiles to attract top talent
- **Job Posting**: Post job opportunities with detailed descriptions and eligibility criteria
- **Application Review**: View and filter student applications with resume preview
- **AI-Powered Resume Analysis**: Leverage Google's Gemini AI to analyze resumes and assess candidate fit
- **Interview Scheduling**: Schedule and manage interviews with selected candidates
- **Hiring Workflow**: Track candidates through the entire recruitment process

### For Administrators
- **User Management**: Approve and manage student and recruiter accounts
- **Analytics Dashboard**: View placement statistics and track institutional performance
- **System Monitoring**: Access logs and system activities for security and auditing

## 🛠️ Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: MongoDB (NoSQL database)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Authentication**: Session-based authentication with security features
- **AI Integration**: Google Gemini API for resume analysis
- **Document Processing**: Support for PDF, DOCX, and image-based resumes
- **Notifications**: Twilio SMS integration for real-time alerts

## 📋 Prerequisites

- Python 3.8+
- MongoDB
- Tesseract OCR (for image-based resume processing)
- Google Gemini API key (for AI resume analysis)
- Twilio account (for SMS notifications)

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Campus_Placement_Portal.git
   cd Campus_Placement_Portal
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key_here
   MONGO_URI=mongodb://localhost:27017/Campus_Placement_Portal
   
   # Twilio configuration (optional for SMS)
   TWILIO_ENABLED=False  # Set to True to enable SMS
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=your_twilio_phone
   
   # Google Gemini API (for resume analysis)
   GEMINI_API_KEY=your_gemini_api_key
   ```

5. Initialize the database:
   ```bash
   flask run
   ```
   The first run will automatically set up the database collections and indexes.

## 🚀 Usage

1. Start the application:
   ```bash
   flask run
   ```

2. Access the application at `http://localhost:5000`

3. Register as either a student or recruiter to begin using the platform


## 🙏 Acknowledgements

- [Flask](https://flask.palletsprojects.com/)
- [MongoDB](https://www.mongodb.com/)
- [Google Gemini AI](https://ai.google.dev/)
- [Twilio](https://www.twilio.com/)
- [Bootstrap](https://getbootstrap.com/)
- [PyTesseract](https://github.com/madmaze/pytesseract)

---

