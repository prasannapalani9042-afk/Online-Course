# CourseHub — Online Course Management System

Full-stack educational project:
- **Frontend:** HTML5, CSS3, JavaScript
- **Backend:** Python + Flask
- **Database:** SQLite (automatically created at `instance/coursehub.db`)

## Features
- Student registration/login with hashed passwords
- Course catalogue and search
- Course detail pages and enrollment
- Student dashboard
- Enrolled course lessons and lesson completion
- Three-question quiz with instant score
- Admin dashboard to add/delete courses and view counts
- Responsive layout and flash messages
- Database seeded with sample courses/lessons on first run

## Run locally (Windows)
1. Install Python 3.10 or later.
2. Extract this ZIP and open the extracted folder in VS Code or a terminal.
3. Create and activate a virtual environment:
   ```bat
   py -m venv .venv
   .venv\\Scripts\\activate
   ```
4. Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
5. Run:
   ```bat
   python app.py
   ```
6. Open `http://127.0.0.1:5000`.

The SQLite database is created automatically at `instance/coursehub.db`. Sample courses and lessons are added on first run.

## Make an admin account
1. Register a normal account in the app.
2. Stop the app with Ctrl+C.
3. Run this command in the project folder:
   ```bat
   python
   ```
4. In the Python prompt, run:
   ```python
   from app import app, db, User
   with app.app_context():
       user = User.query.filter_by(email="your-email@example.com").first()
       user.role = "ADMIN"
       db.session.commit()
   ```
5. Type `exit()` and restart `python app.py`. The Admin link will appear after login.

## Important
- This is a learning/demo project, not production-hardened. Before public deployment, set a strong `SECRET_KEY`, add CSRF protection, rate limiting, email verification, secure deployment configuration, and backups.
- Sample lesson video links open YouTube search results; this app does not host video files.
- Do not commit `instance/coursehub.db` or real secrets to a public repository.


## Demo admin account

The app creates this administrator account automatically on startup:

- **Email:** `admin@coursehub.com`
- **Password:** `Admin@12345`

Sign in at `/login`, then open **Admin Workspace** or visit `/admin`. Change the demo password before deploying publicly. The admin can add/delete courses, add lessons, view registered users and enrollments, promote users to admin, and preview every course quiz. Each course has a topic-specific quiz; submitting the quiz records course completion.
