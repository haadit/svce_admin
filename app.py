import os
from flask import Flask, render_template, request, redirect, url_for, session, abort
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()

# Replace with your actual Supabase URL and anon key
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") # Use the anon key provided

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
# In a real app, use a strong random key from environment variables
app.secret_key = 'your_secret_key_here'

# --- Multi-User Authentication ---
USERS = {
    'admin1': {'password': os.environ.get('ADMIN1_PASSWORD'), 'role': 'admin'},
    'admin2': {'password': os.environ.get('ADMIN2_PASSWORD'), 'role': 'admin'},
    'councellor1': {'password': os.environ.get('COUNCELLOR1_PASSWORD'), 'role': 'councellor'},
    'councellor2': {'password': os.environ.get('COUNCELLOR2_PASSWORD'), 'role': 'councellor'},
}

def is_admin():
    return session.get('logged_in') and session.get('role') == 'admin'

def is_councellor():
    return session.get('logged_in') and session.get('role') == 'councellor'

def require_admin_or_councellor(func):
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = USERS.get(username)
        if user and password == user['password']:
            session['logged_in'] = True
            session['user'] = {'id': username}
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid credentials. Please try again."
            return render_template('login.html', error=error)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@require_admin_or_councellor
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']['id']
    user_role = session.get('role', '')
    connected = session.get('connected', True)
    error = None
    enquiries = []
    available_ranges = []
    selected_range = request.args.get('range')
    token_date = request.args.get('token_date')
    page = int(request.args.get('page', 1))
    per_page = 25
    total_pages = 1

    if connected:
        try:
            status_filter = request.args.get('status')
            follow_up_date_filter = request.args.get('follow_up_date')
            search_query = request.args.get('search_query')

            # Get all token numbers to compute ranges
            all_tokens_data = supabase.table('admission_enquiries').select('token_number').execute()
            all_token_numbers = [row['token_number'] for row in all_tokens_data.data if row.get('token_number')]
            # Extract date prefixes (e.g., 07/06/2025 from 07/06/2025/01)
            date_prefixes = set()
            for token in all_token_numbers:
                match = re.match(r'^(\d{2}/\d{2}/\d{4})', token)
                if match:
                    date_prefixes.add(match.group(1))
            available_ranges = sorted(date_prefixes, key=lambda d: [int(x) for x in d.split('/')][::-1])  # Sort by date descending

            # Base query
            query = supabase.table('admission_enquiries').select('*')

            # Apply range filter if selected
            if selected_range:
                query = query.ilike('token_number', f"{selected_range}%")

            # Apply other filters
            if status_filter and status_filter != 'All':
                query = query.eq('status', status_filter)
            if follow_up_date_filter:
                query = query.eq('follow_up_date', follow_up_date_filter)
            if search_query:
                query = query.ilike('student_name', f"%{search_query}%")

            # Apply token_date filter if provided
            if token_date:
                # Convert yyyy-mm-dd to dd/mm/yyyy
                try:
                    parts = token_date.split('-')
                    if len(parts) == 3:
                        date_prefix = f"{parts[2]}/{parts[1]}/{parts[0]}"
                        query = query.ilike('token_number', f"{date_prefix}%")
                except Exception as e:
                    pass

            # Sort by created_at descending to show latest entries first
            query = query.order('created_at', desc=True)
            data = query.execute()
            all_enquiries = data.data
            total_entries = len(all_enquiries)
            total_pages = max(1, (total_entries + per_page - 1) // per_page)
            start = (page - 1) * per_page
            end = start + per_page
            enquiries = all_enquiries[start:end]

        except Exception as e:
            error = f"Database error: {e}"
            enquiries = []
            connected = False

    if request.method == 'POST':
        if request.form.get('status_update'):
            # Process status updates
            try:
                for key, value in request.form.items():
                    match = re.match(r'status_([0-9a-fA-F-]{36})$', key)
                    if match:
                        enquiry_id = match.group(1)
                        new_status = value
                        new_remarks = request.form.get(f'remarks_{enquiry_id}')
                        new_follow_up_date = request.form.get(f'follow_up_date_{enquiry_id}')

                        if enquiry_id and new_status:
                            update_data = {
                                'status': new_status,
                                'updated_at': datetime.now().isoformat()
                            }
                            # Add remarks to update data if it's available
                            if new_remarks is not None:
                                update_data['remarks'] = new_remarks
                            # Add follow_up_date to update data if it's available
                            if new_follow_up_date:
                                update_data['follow_up_date'] = new_follow_up_date
                            else:
                                update_data['follow_up_date'] = None # Ensure it's set to null if empty

                            update_response = supabase.table('admission_enquiries').update(update_data).eq('id', enquiry_id).execute()
                            print(f"Update response for dashboard: {update_response}") # Added print for debugging
                            if hasattr(update_response, 'error') and update_response.error:
                                error = f"Error updating status for ID {enquiry_id}: {update_response.error}"
                                print(error) # Log the error for debugging
            except Exception as e:
                error = f"Error processing status updates: {e}"
                print(error)

    return render_template('dashboard.html', connected=connected, error=error, enquiries=enquiries, status_filter=status_filter, follow_up_date_filter=follow_up_date_filter, today_date=datetime.now().date().isoformat(), search_query=search_query, user_role=user_role, available_ranges=available_ranges, selected_range=selected_range, token_date=token_date, page=page, total_pages=total_pages)

@app.route('/student_details/<enquiry_id>')
@require_admin_or_councellor
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
@require_admin_or_councellor
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
    education_qualification_options = [
        "12th",
        "Diploma"
    ]
    user_role = session.get('role', '')
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
                'educational_qualification': form_data.get('education_qualification'),
                'status': form_data.get('status'),
                'course_interested_in': form_data.get('course_interested_in'),
                'ug_percentage': form_data.get('ug_percentage'),
                'pg_12th_percentage': form_data.get('pg_12th_percentage'),
                'pg_course_applying_for': form_data.get('pg_course_applying_for'),
                'physics_marks': form_data.get('physics_marks') or None,
                'chemistry_marks': form_data.get('chemistry_marks') or None,
                'mathematics_marks': form_data.get('mathematics_marks') or None,
                'physics_marks_11': form_data.get('physics_marks_11') or None,
                'chemistry_marks_11': form_data.get('chemistry_marks_11') or None,
                'mathematics_marks_12a': form_data.get('mathematics_marks_12a') or None,
                'mathematics_marks_12b': form_data.get('mathematics_marks_12b') or None,
                'mathematics_marks_11a': form_data.get('mathematics_marks_11a') or None,
                'mathematics_marks_11b': form_data.get('mathematics_marks_11b') or None,
                'physics_marks_11_practical': form_data.get('physics_marks_11_practical') or None,
                'chemistry_marks_11_practical': form_data.get('chemistry_marks_11_practical') or None,
                'physics_marks_12_practical': form_data.get('physics_marks_12_practical') or None,
                'chemistry_marks_12_practical': form_data.get('chemistry_marks_12_practical') or None,
                'cs_marks': form_data.get('cs_marks') or None,
                'ece_marks': form_data.get('ece_marks') or None,
                'kannada_marks_12': form_data.get('kannada_marks_12') or None,
                'english_marks_12': form_data.get('english_marks_12') or None,
                'other_unnamed_marks_12': form_data.get('other_unnamed_marks_12') or None,
                'pcm_percentage': form_data.get('pcm_percentage') or None,
                'total_percentage': form_data.get('total_percentage') or None,
                'jee_rank': form_data.get('jee_rank') or None,
                'comedk_rank': form_data.get('comedk_rank') or None,
                'cet_rank': form_data.get('cet_rank') or None,
                'diploma_percentage': form_data.get('diploma_percentage') or None,
                'dcet_rank': form_data.get('dcet_rank') or None,
                'updated_at': datetime.now().isoformat()
            }
            # Set enquiry_date to current date if not provided, otherwise use form value
            enquiry_date_val = form_data.get('enquiry_date')
            if enquiry_date_val:
                enquiry_update_data['enquiry_date'] = enquiry_date_val
            else:
                enquiry_update_data['enquiry_date'] = datetime.now().date().isoformat() # Use current date

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
            print(f"Update response for edit_enquiry: {update_response}") # Added print for debugging
            if hasattr(update_response, 'error') and update_response.error:
                error_message = f"Error updating admission enquiry: {update_response.error}"
            else:
                return redirect(url_for('dashboard'))
        # GET or POST with error: Fetch current data
        data = supabase.from_('admission_enquiries').select('*').eq('id', enquiry_id).single().execute()
        enquiry = data.data if data and data.data else None
        # Format created_at timestamp for display
        if enquiry and isinstance(enquiry.get('created_at'), str):
            try:
                # Attempt to parse the ISO 8601 string, handling potential variations
                # Replace 'Z' with '+00:00' if necessary, though fromisoformat is robust
                timestamp_str = enquiry['created_at'].replace('Z', '+00:00')
                # Handle potential space instead of 'T' in ISO format
                timestamp_str = timestamp_str.replace(' ', 'T', 1)
                created_at_dt = datetime.fromisoformat(timestamp_str)
                # Format into "DD Mon YYYY HH:MM:SS (offset)"
                enquiry['created_at'] = created_at_dt.strftime("%d %b %Y %H:%M:%S")
            except (ValueError, TypeError) as e:
                print(f"Error parsing or formatting created_at: {e} - Value: {enquiry.get('created_at')}")
                enquiry['created_at'] = 'N/A'

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
    return render_template('edit_enquiry.html', connected=connected, enquiry=enquiry, course_preferences=course_preferences_list, all_courses=all_courses, current_preferences=current_preferences, error=error_message, education_board_options=education_board_options, education_qualification_options=education_qualification_options, user_role=user_role)

@app.route('/delete_enquiry/<enquiry_id>', methods=['POST'])
@require_admin_or_councellor
def delete_enquiry(enquiry_id):
    # Only allow admin role to delete
    if session.get('role') != 'admin':
        abort(403)
    try:
        response = supabase.table('admission_enquiries').delete().eq('id', enquiry_id).execute()
        # Optionally, check response for errors
    except Exception as e:
        print(f"Error deleting enquiry {enquiry_id}: {e}")
    return redirect(url_for('dashboard'))

@app.route('/change_password', methods=['GET', 'POST'])
@require_admin_or_councellor
def change_password():
    username = session['user']['id']
    user = USERS.get(username)
    message = None
    error = None
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if not old_password or not new_password or not confirm_password:
            error = 'All fields are required.'
        elif old_password != user['password']:
            error = 'Old password is incorrect.'
        elif new_password != confirm_password:
            error = 'New passwords do not match.'
        else:
            USERS[username]['password'] = new_password
            message = 'Password changed successfully!'
    return render_template('change_password.html', message=message, error=error)

if __name__ == '__main__':
    # Use debug=True only for development
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True) 