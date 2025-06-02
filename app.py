import os
from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Replace with your actual Supabase URL and anon key
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # Use the anon key provided

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
# In a real app, use a strong random key from environment variables
app.secret_key = 'your_secret_key_here'

# --- Basic Admin Authentication (for demonstration) ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

def is_admin():
    return session.get('logged_in')

def require_admin(func):
    def wrapper(*args, **kwargs):
        if not is_admin():
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__ # Preserve original function name for Flask routing
    return wrapper

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid credentials. Please try again."
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
@require_admin
def dashboard():
    try:
        error_message = None
        data = supabase.from_('admission_enquiries').select('*').order('token_number').execute()
        enquiries = data.data if data and data.data else []
        connected = True
    except Exception as e:
        connected = False
        enquiries = []
        error_message = f"Error connecting to Supabase or fetching data: {e}"
        return render_template('dashboard.html', connected=connected, error=error_message)
    return render_template('dashboard.html', connected=connected, enquiries=enquiries, error=error_message)

@app.route('/student_details/<enquiry_id>')
@require_admin
def student_details(enquiry_id):
    try:
        data = supabase.from_('admission_enquiries').select('*').eq('id', enquiry_id).single().execute()
        enquiry = data.data if data and data.data else None
        student_name = enquiry['student_name'] if enquiry else "Unknown Student"
        # Parse course preferences from JSON and sort by order
        course_preferences = []
        if enquiry and enquiry.get('course_preferences'):
            cp = enquiry['course_preferences']
            course_preferences = [
                {'course_name': k, 'preference_order': v}
                for k, v in cp.items()
            ]
            course_preferences.sort(key=lambda x: x['preference_order'])
        connected = True
        error_message = None
    except Exception as e:
        connected = False
        student_name = "Error"
        course_preferences = []
        error_message = f"Error fetching student details or course preferences: {e}"
    return render_template('student_details.html', connected=connected, student_name=student_name, course_preferences=course_preferences, error=error_message)

@app.route('/edit_enquiry/<enquiry_id>', methods=['GET', 'POST'])
@require_admin
def edit_enquiry(enquiry_id):
    error_message = None
    connected = True
    all_courses = [
        "BE Computer Science and Engineering",
        "BE Computer Science and Engineering (Artificial Intelligence)",
        "BE Computer Science and Engineering (Data Science)",
        "BE Computer Science and Engineering (Cyber Security)",
        "BE Information Science and Engineering",
        "BE Electronics and Communication Engineering",
        "BE Civil Engineering",
        "BE Mechanical Engineering"
    ]
    education_board_options = [
        "CBSE",
        "Karnataka",
        "AP/Telangana",
        "Others"
    ]
    try:
        if request.method == 'POST':
            form_data = request.form
            # Update admission_enquiries table
            enquiry_update_data = {
                'enquiry_date': form_data.get('enquiry_date'),
                'student_name': form_data.get('student_name'),
                'student_email': form_data.get('student_email'),
                'student_mobile': form_data.get('student_mobile'),
                'father_name': form_data.get('father_name'),
                'father_mobile': form_data.get('father_mobile'),
                'mother_name': form_data.get('mother_name'),
                'mother_mobile': form_data.get('mother_mobile'),
                'address': form_data.get('address'),
                'reference': form_data.get('reference'),
                'physics_marks': form_data.get('physics_marks') or None,
                'chemistry_marks': form_data.get('chemistry_marks') or None,
                'mathematics_marks': form_data.get('mathematics_marks') or None,
                'cs_marks': form_data.get('cs_marks') or None,
                'bio_marks': form_data.get('bio_marks') or None,
                'ece_marks': form_data.get('ece_marks') or None,
                'pcm_percentage': form_data.get('pcm_percentage') or None,
                'total_percentage': form_data.get('total_percentage') or None,
                'jee_rank': form_data.get('jee_rank') or None,
                'comedk_rank': form_data.get('comedk_rank') or None,
                'cet_rank': form_data.get('cet_rank') or None,
                'updated_at': datetime.now().isoformat()
            }
            # Handle Course Preferences Update (JSON)
            selected_courses = request.form.getlist('course_preference')
            course_orders = []
            for course_name in selected_courses:
                input_name = f"preference_order_{course_name.replace(' ', '_').replace('(', '').replace(')', '').replace('.', '')}"
                order_val = request.form.get(input_name)
                try:
                    order_val = int(order_val)
                except (TypeError, ValueError):
                    order_val = 9999
                course_orders.append((course_name, order_val))
            # Sort and reassign order
            course_orders.sort(key=lambda x: x[1])
            course_preferences_json = {course: idx+1 for idx, (course, _) in enumerate(course_orders)}
            enquiry_update_data['course_preferences'] = course_preferences_json
            update_response = supabase.table('admission_enquiries').update(enquiry_update_data).eq('id', enquiry_id).execute()
            if hasattr(update_response, 'error') and update_response.error:
                error_message = f"Error updating admission enquiry: {update_response.error}"
            else:
                return redirect(url_for('dashboard'))
        # GET or POST with error: Fetch current data
        data = supabase.from_('admission_enquiries').select('*').eq('id', enquiry_id).single().execute()
        enquiry = data.data if data and data.data else None
        # Prepare current_preferences and course_preferences_list for template
        current_preferences = {}
        course_preferences_list = []
        if enquiry and enquiry.get('course_preferences'):
            cp = enquiry['course_preferences']
            current_preferences = {k: {'course_name': k, 'preference_order': v} for k, v in cp.items()}
            course_preferences_list = [
                {'course_name': k, 'preference_order': v} for k, v in cp.items()
            ]
            course_preferences_list.sort(key=lambda x: x['preference_order'])
    except Exception as e:
        connected = False
        enquiry = None
        course_preferences_list = []
        current_preferences = {}
        error_message = f"An unexpected error occurred: {e}"
        print(f"Unexpected error in edit_enquiry: {e}")
    return render_template('edit_enquiry.html', connected=connected, enquiry=enquiry, course_preferences=course_preferences_list, all_courses=all_courses, current_preferences=current_preferences, error=error_message, education_board_options=education_board_options)


if __name__ == '__main__':
    # Use debug=True only for development
    app.run(debug=True) 