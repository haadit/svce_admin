# Supabase Admin Flask App

A simple admin dashboard built with Flask for managing student admission enquiries using Supabase as the backend.

## Features
- Admin login authentication
- View, edit, and update student admission enquiries
- Course preference management
- Secure environment variable usage

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd <your-project-directory>
   ```

2. **Create a virtual environment and activate it:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   - Copy the provided `.env` example or create a new `.env` file in the root directory:
     ```
     ADMIN_PASSWORD=your_admin_password_here
     SUPABASE_URL=your_supabase_url
     SUPABASE_KEY=your_supabase_anon_key
     ```

5. **Run the application:**
   ```bash
   python supabase_admin_flask/app.py
   ```

6. **Access the app:**
   Open your browser and go to [http://localhost:5000](http://localhost:5000)

## Notes
- For production, set a strong `app.secret_key` in `app.py` and do not expose your Supabase keys.
- Only the admin user (username: `admin`) can log in.
- Make sure your Supabase project and table names match those in the code.

## License
MIT 