import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "coursehub.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
os.makedirs(app.instance_path, exist_ok=True)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(190), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="STUDENT")
    enrollments = db.relationship("Enrollment", backref="student", cascade="all, delete-orphan")

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False, default="General")
    level = db.Column(db.String(40), nullable=False, default="Beginner")
    instructor = db.Column(db.String(120), nullable=False, default="CourseHub Team")
    duration_hours = db.Column(db.Integer, nullable=False, default=4)
    lessons = db.relationship("Lesson", backref="course", cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", backref="course", cascade="all, delete-orphan")

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "course_id", name="unique_enrollment"),)

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False)
    video_url = db.Column(db.String(500), default="")
    position = db.Column(db.Integer, default=1)

class CourseCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    total = db.Column(db.Integer, nullable=False, default=0)
    completed_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    __table_args__ = (db.UniqueConstraint("user_id", "course_id", name="unique_course_completion"),)

class LessonProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lesson.id"), nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "lesson_id", name="unique_lesson_progress"),)

def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None

@app.context_processor
def inject_user():
    return {"current_user": current_user()}

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in first.", "info")
            return redirect(url_for("login"))
        if user.role != "ADMIN":
            abort(403)
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    courses = Course.query.order_by(Course.id.desc()).limit(6).all()
    return render_template("home.html", courses=courses)

@app.route("/courses")
def courses():
    q = request.args.get("q", "").strip()
    query = Course.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Course.title.ilike(like), Course.category.ilike(like), Course.instructor.ilike(like)))
    return render_template("courses.html", courses=query.order_by(Course.title).all(), q=q)

@app.route("/course/<int:course_id>")
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    enrolled = False
    user = current_user()
    if user:
        enrolled = Enrollment.query.filter_by(user_id=user.id, course_id=course.id).first() is not None
    return render_template("course_detail.html", course=course, enrolled=enrolled)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or len(name) > 120 or "@" not in email or len(password) < 8:
            flash("Enter your name, a valid email, and a password of at least 8 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            flash("Account created! You can now log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            flash(f"Welcome back, {user.name}!", "success")
            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/enroll/<int:course_id>", methods=["POST"])
@login_required
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    user = current_user()
    existing = Enrollment.query.filter_by(user_id=user.id, course_id=course.id).first()
    if not existing:
        db.session.add(Enrollment(user_id=user.id, course_id=course.id))
        db.session.commit()
        flash("You are enrolled! Happy learning.", "success")
    else:
        flash("You are already enrolled in this course.", "info")
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    enrollments = Enrollment.query.filter_by(user_id=user.id).all()
    completed_course_ids = {c.course_id for c in CourseCompletion.query.filter_by(user_id=user.id).all()}
    return render_template("dashboard.html", enrollments=enrollments, completed_course_ids=completed_course_ids)

@app.route("/lessons/<int:course_id>")
@login_required
def lessons(course_id):
    course = Course.query.get_or_404(course_id)
    user = current_user()
    enrolled = Enrollment.query.filter_by(user_id=user.id, course_id=course.id).first()
    if not enrolled and user.role != "ADMIN":
        abort(403)
    lesson_list = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.position, Lesson.id).all()
    progress_ids = {p.lesson_id for p in LessonProgress.query.filter_by(user_id=user.id, completed=True).all()}
    return render_template("lessons.html", course=course, lessons=lesson_list, progress_ids=progress_ids)

@app.route("/lesson/<int:lesson_id>/complete", methods=["POST"])
@login_required
def complete_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    user = current_user()
    enrolled = Enrollment.query.filter_by(user_id=user.id, course_id=lesson.course_id).first()
    if not enrolled and user.role != "ADMIN":
        abort(403)
    progress = LessonProgress.query.filter_by(user_id=user.id, lesson_id=lesson.id).first()
    if not progress:
        progress = LessonProgress(user_id=user.id, lesson_id=lesson.id, completed=True)
        db.session.add(progress)
    else:
        progress.completed = True
    db.session.commit()
    flash("Lesson marked as complete.", "success")
    return redirect(url_for("lessons", course_id=lesson.course_id))

QUIZ_BANKS = {
    "java": [
        {"id":"q1", "question":"Which keyword is used to create a class in Java?", "options":[("a","class"),("b","define"),("c","struct"),("d","object")], "answer":"a"},
        {"id":"q2", "question":"Which method is the usual entry point of a Java application?", "options":[("a","start()"),("b","main()"),("c","runApp()"),("d","init()")], "answer":"b"},
        {"id":"q3", "question":"Which concept lets a class inherit fields and methods from another class?", "options":[("a","Encapsulation"),("b","Compilation"),("c","Inheritance"),("d","Overloading")], "answer":"c"},
        {"id":"q4", "question":"Which type stores a true or false value in Java?", "options":[("a","int"),("b","String"),("c","char"),("d","boolean")], "answer":"d"},
    ],
    "web": [
        {"id":"q1", "question":"Which HTML element creates a hyperlink?", "options":[("a","<link>"),("b","<a>"),("c","<href>"),("d","<url>")], "answer":"b"},
        {"id":"q2", "question":"Which CSS property changes text colour?", "options":[("a","font-style"),("b","background"),("c","color"),("d","text-align")], "answer":"c"},
        {"id":"q3", "question":"Which JavaScript keyword declares a block-scoped variable that can be reassigned?", "options":[("a","let"),("b","const"),("c","static"),("d","define")], "answer":"a"},
        {"id":"q4", "question":"Which HTML attribute provides alternative text for an image?", "options":[("a","src"),("b","title-only"),("c","href"),("d","alt")], "answer":"d"},
    ],
    "sql": [
        {"id":"q1", "question":"Which SQL command retrieves rows from a table?", "options":[("a","UPDATE"),("b","SELECT"),("c","INSERT"),("d","ALTER")], "answer":"b"},
        {"id":"q2", "question":"Which key uniquely identifies each row in a table?", "options":[("a","Foreign key"),("b","Sort key"),("c","Primary key"),("d","Duplicate key")], "answer":"c"},
        {"id":"q3", "question":"Which clause filters rows before grouping?", "options":[("a","WHERE"),("b","ORDER BY"),("c","FROM"),("d","AS")], "answer":"a"},
        {"id":"q4", "question":"Which JOIN returns only rows with matching values in both tables?", "options":[("a","CROSS JOIN"),("b","LEFT JOIN"),("c","FULL JOIN"),("d","INNER JOIN")], "answer":"d"},
    ],
    "python": [
        {"id":"q1", "question":"Which keyword defines a function in Python?", "options":[("a","func"),("b","def"),("c","function"),("d","method")], "answer":"b"},
        {"id":"q2", "question":"Which Python type stores an ordered, changeable collection?", "options":[("a","tuple"),("b","set"),("c","list"),("d","frozenset")], "answer":"c"},
        {"id":"q3", "question":"Which loop is commonly used to iterate over items in a sequence?", "options":[("a","for"),("b","switch"),("c","case"),("d","define")], "answer":"a"},
        {"id":"q4", "question":"What does len(my_list) return?", "options":[("a","The last item"),("b","The list type"),("c","The memory address"),("d","The number of items")], "answer":"d"},
    ],
}

def quiz_questions_for(course):
    text = (course.title + " " + course.category).lower()
    if "java" in text:
        key = "java"
    elif any(word in text for word in ("web", "html", "css", "javascript")):
        key = "web"
    elif any(word in text for word in ("sql", "database")):
        key = "sql"
    else:
        key = "python"
    return QUIZ_BANKS[key]

@app.route("/quiz")
@login_required
def quiz_choose_course():
    return redirect(url_for("courses"))

@app.route("/quiz/<int:course_id>", methods=["GET", "POST"])
@login_required
def quiz(course_id):
    course = Course.query.get_or_404(course_id)
    user = current_user()
    enrolled = Enrollment.query.filter_by(user_id=user.id, course_id=course.id).first()
    if not enrolled and user.role != "ADMIN":
        abort(403)
    questions = quiz_questions_for(course)
    score = None
    completed = False
    if request.method == "POST":
        score = sum(1 for q in questions if request.form.get(q["id"]) == q["answer"])
        completion = CourseCompletion.query.filter_by(user_id=user.id, course_id=course.id).first()
        if completion is None:
            db.session.add(CourseCompletion(user_id=user.id, course_id=course.id, score=score, total=len(questions)))
        else:
            completion.score = score
            completion.total = len(questions)
        db.session.commit()
        completed = True
        flash("Quiz submitted. Course marked as complete.", "success")
    else:
        completed = CourseCompletion.query.filter_by(user_id=user.id, course_id=course.id).first() is not None
    return render_template("quiz.html", course=course, questions=questions, score=score, completed=completed)

@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", courses=Course.query.order_by(Course.id.desc()).all(), users=User.query.order_by(User.id.desc()).all(), users_count=User.query.count(), enrollment_count=Enrollment.query.count())

@app.route("/admin/course/add", methods=["POST"])
@admin_required
def add_course():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "General").strip() or "General"
    level = request.form.get("level", "Beginner")
    instructor = request.form.get("instructor", "CourseHub Team").strip() or "CourseHub Team"
    try:
        duration = int(request.form.get("duration_hours", "4"))
    except ValueError:
        duration = 4
    if not title or not description:
        flash("Course title and description are required.", "error")
    else:
        course = Course(title=title, description=description, category=category, level=level, instructor=instructor, duration_hours=max(1, min(duration, 500)))
        db.session.add(course)
        db.session.commit()
        flash("Course added successfully.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/course/<int:course_id>/delete", methods=["POST"])
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    db.session.delete(course)
    db.session.commit()
    flash("Course deleted.", "info")
    return redirect(url_for("admin"))


@app.route("/admin/lesson/add", methods=["POST"])
@admin_required
def admin_add_lesson():
    course_id = request.form.get("course_id", type=int)
    course = Course.query.get_or_404(course_id)
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    video_url = request.form.get("video_url", "").strip()
    if not title or not content:
        flash("Lesson title and content are required.", "error")
    else:
        position = (db.session.query(db.func.max(Lesson.position)).filter_by(course_id=course.id).scalar() or 0) + 1
        db.session.add(Lesson(course_id=course.id, title=title, content=content, video_url=video_url, position=position))
        db.session.commit()
        flash("Lesson added successfully.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/user/<int:user_id>/promote", methods=["POST"])
@admin_required
def promote_user(user_id):
    user = User.query.get_or_404(user_id)
    user.role = "ADMIN"
    db.session.commit()
    flash(f"{user.email} now has admin access.", "success")
    return redirect(url_for("admin"))

@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You don't have permission to access this page."), 403

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="We couldn't find that page."), 404

def seed_database():
    if Course.query.count() == 0:
        seed = [
            Course(title="Java Programming Fundamentals", description="Learn Java syntax, object-oriented programming, collections and exception handling with practical examples.", category="Programming", level="Beginner", instructor="Arun Kumar", duration_hours=12),
            Course(title="Web Development with HTML, CSS & JavaScript", description="Build responsive web pages and add interactive behaviour with HTML, CSS and modern JavaScript.", category="Web Development", level="Beginner", instructor="Priya S", duration_hours=10),
            Course(title="SQL and Database Design", description="Learn relational database concepts, table design, joins, constraints and practical SQL queries.", category="Database", level="Intermediate", instructor="Karthik R", duration_hours=8),
            Course(title="Python for Everybody", description="Start with Python fundamentals, functions, loops, files and data structures.", category="Programming", level="Beginner", instructor="Meena V", duration_hours=9),
        ]
        db.session.add_all(seed)
        db.session.flush()
        lessons = [
            Lesson(course_id=seed[0].id, title="Introduction to Java", content="Install a JDK and understand how Java source code is compiled and executed.", video_url="https://www.youtube.com/results?search_query=java+introduction", position=1),
            Lesson(course_id=seed[0].id, title="Variables and Data Types", content="Learn variables, primitive types, operators and type conversion.", video_url="https://www.youtube.com/results?search_query=java+variables", position=2),
            Lesson(course_id=seed[0].id, title="Object-Oriented Programming", content="Explore classes, objects, inheritance, encapsulation and polymorphism.", video_url="https://www.youtube.com/results?search_query=java+oop", position=3),
            Lesson(course_id=seed[1].id, title="HTML Page Structure", content="Create a semantic HTML page with headings, links, forms and images.", video_url="https://www.youtube.com/results?search_query=html+basics", position=1),
            Lesson(course_id=seed[1].id, title="CSS Layout", content="Style a page using flexbox, grid, spacing and responsive rules.", video_url="https://www.youtube.com/results?search_query=css+flexbox", position=2),
            Lesson(course_id=seed[2].id, title="Relational Databases", content="Understand tables, keys, relationships and normalization.", video_url="https://www.youtube.com/results?search_query=database+normalization", position=1),
            Lesson(course_id=seed[3].id, title="Python Basics", content="Learn variables, conditions, loops and functions.", video_url="https://www.youtube.com/results?search_query=python+basics", position=1),
        ]
        db.session.add_all(lessons)
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_database()
    admin_user = User.query.filter_by(email="admin@coursehub.com").first()
    if admin_user is None:
        admin_user = User(name="CourseHub Admin", email="admin@coursehub.com", password_hash=generate_password_hash("Admin@12345"), role="ADMIN")
        db.session.add(admin_user)
    else:
        admin_user.role = "ADMIN"
    db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
