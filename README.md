# Supabase Admin Flask Dashboard

A Flask-based admin dashboard for managing admission enquiries with Supabase backend.

## Features

- **Multi-user Authentication**: Support for admin and counselor roles
- **Dashboard Management**: View and manage admission enquiries
- **Status Tracking**: Track student counseling status and follow-ups
- **Live Search**: Real-time search functionality for student names
- **Token Management**: Support for both PG and UG token formats
- **Responsive Design**: Modern UI with mobile-friendly layout

## Live Search Feature

The dashboard now includes a live search functionality that allows you to:

- **Real-time Results**: Search results appear as you type (with 300ms debounce)
- **Keyboard Navigation**: Use arrow keys to navigate through results
- **Quick Access**: Click on any search result to go directly to the student's details
- **Filter Integration**: Search respects current status and date filters
- **Smart Navigation**: Automatically detects PG/UG forms and navigates to the correct edit page

### How to Use Live Search

1. **Start Typing**: Begin typing a student's name in the search box
2. **View Results**: Matching students will appear in a dropdown below the search box
3. **Navigate**: 
   - Use mouse to click on a result
   - Use arrow keys (↑/↓) to navigate
   - Press Enter to select the highlighted result
   - Press Escape to close the search results
4. **Quick Access**: Clicking any result takes you directly to that student's edit page

### Search Features

- **Debounced Search**: Prevents excessive API calls while typing
- **Request Cancellation**: Cancels previous searches when typing new queries
- **Loading States**: Shows "Searching..." while fetching results
- **Error Handling**: Graceful error messages if search fails
- **Empty State**: Clear message when no results are found

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
   - `ADMIN1_PASSWORD`: Password for admin1 user
   - `ADMIN2_PASSWORD`: Password for admin2 user
   - `COUNCELLOR1_PASSWORD`: Password for counselor1 user
   - `COUNCELLOR2_PASSWORD`: Password for counselor2 user
4. Run the application: `python app.py`

## API Endpoints

- `GET /search_enquiries`: AJAX endpoint for live search functionality
- `GET /dashboard`: Main dashboard page
- `GET /edit_enquiry/<id>`: Edit student enquiry page
- `POST /dashboard`: Update student status and remarks
- `POST /delete_enquiry/<id>`: Delete student enquiry (admin only)

## Database Schema

The application uses a Supabase table called `admission_enquiries` with fields for:
- Student information (name, email, mobile, etc.)
- Academic details (marks, ranks, percentages)
- Status tracking (counseling status, follow-up dates)
- Token management (PG/UG token formats)

## Security

- Session-based authentication
- Role-based access control (admin/counselor)
- CSRF protection for form submissions
- Input validation and sanitization 