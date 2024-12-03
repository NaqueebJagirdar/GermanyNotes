from datetime import datetime

import click
from flask import Flask, redirect, render_template, request, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///notes.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

migrate = Migrate(app, db)


# Define the Note model
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    edited_date = db.Column(db.DateTime, onupdate=datetime.utcnow)
    status = db.Column(db.String(50), default="In-Query")
    editor_name = db.Column(db.String(100), nullable=True)
    modifier_name = db.Column(db.String(100), nullable=True)


# Routes
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/add-notes", methods=["GET", "POST"])
def add_notes():
    categories = [
        "WSE Results Statistics",
        "Sales Gate Process",
        "WSE SV Statistics",
        "WSE KPI's",
        "WSE Consultants",
        "Survey (Sales → WSE)",
        "WSE Resource Budget",
        "WSE Effort Estimation",
        "WSE Workload",
    ]

    # Count "In-Query" notes for each category
    inquery_counts = {}
    for category in categories:
        inquery_counts[category] = Note.query.filter_by(
            category=category, status="In-Query"
        ).count()

    # Handle form submission for adding a new note
    if request.method == "POST":
        category = request.form.get("category")
        title = request.form.get("title")
        content = request.form.get("content")
        if category and title and content:
            new_note = Note(
                category=category, title=title, content=content, status="In-Query"
            )
            db.session.add(new_note)
            db.session.commit()
            return redirect(url_for("view_notes"))

    return render_template(
        "add_notes.html", categories=categories, inquery_counts=inquery_counts
    )


class Colleague(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Absent")
    role = db.Column(db.String(50), nullable=True)


@app.cli.command("seed-attendance")
def seed_attendance():
    """Seed the database with initial colleagues for attendance."""
    colleagues = [
        Colleague(name="John Doe", status="Present"),
        Colleague(name="Jane Smith", status="Absent"),
        Colleague(name="Naqueeb Jagirdar", status="Present"),
        Colleague(name="Sarah Connor", status="Present"),
        Colleague(name="James Bond", status="Absent"),
    ]
    db.session.bulk_save_objects(colleagues)
    db.session.commit()
    print("Attendance data seeded.")


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    # Initialize selected_date variable
    selected_date = None

    if request.method == "POST":
        # Check if the form contains a selected date
        selected_date = request.form.get("attendance_date")

        if selected_date:
            # Parse the selected date from the form (user's input)
            date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
        elif request.form.get("clear_date"):  # Handle the "Clear Date" action
            date_obj = None  # Clear the date if "Clear Date" is triggered
        else:
            # Default to today's date if no date is selected or cleared
            date_obj = datetime.now()

    else:
        # Default to today's date if it's a GET request
        date_obj = datetime.now()

    # If date_obj is still None (after clear action), set it to today's date
    if not date_obj:
        date_obj = datetime.now()

    # Get date in the required formats
    date_dd_mm_yyyy = date_obj.strftime("%d-%m-%Y")  # Format: 01-12-2024
    date_words = date_obj.strftime("%d %B %Y")  # Format: 01 December 2024
    today_date = datetime.today().strftime("%Y-%m-%d")

    # Fetch all colleagues from the database
    colleagues = Colleague.query.all()  # Dynamically fetch all colleague data

    # Calculate present and total counts dynamically
    total_colleagues = len(colleagues)  # Total number of colleagues in the database
    present_colleagues = sum(
        1 for colleague in colleagues if colleague.status == "Present"
    )  # Count of colleagues marked as 'Present'

    # Pass the calculated and fetched data to the template
    return render_template(
        "attendance.html",
        date_dd_mm_yyyy=date_dd_mm_yyyy,
        date_words=date_words,
        colleagues=colleagues,
        present_colleagues=present_colleagues,  # Dynamic count of present colleagues
        total_colleagues=total_colleagues,  # Dynamic total count of colleagues
        today_date=today_date,
        selected_date=selected_date,  # Pass the selected date to the template
    )


@app.route("/add-colleague", methods=["POST"])
def add_colleague():
    name = request.form.get("name")
    if name:
        new_colleague = Colleague(name=name, status="Absent")
        db.session.add(new_colleague)
        db.session.commit()
    return redirect(url_for("attendance"))


@app.route("/edit-colleague/<int:colleague_id>", methods=["POST"])
def edit_colleague(colleague_id):
    name = request.form.get("name")
    colleague = Colleague.query.get_or_404(colleague_id)
    if name:
        colleague.name = name
        db.session.commit()
    return redirect(url_for("attendance"))


@app.route("/delete-colleague/<int:colleague_id>", methods=["POST"])
def delete_colleague(colleague_id):
    colleague = Colleague.query.get_or_404(colleague_id)
    db.session.delete(colleague)
    db.session.commit()
    return redirect(url_for("attendance"))


@app.route("/update-status/<int:colleague_id>", methods=["POST"])
def update_status(colleague_id):
    status = request.form.get("status")
    colleague = Colleague.query.get_or_404(colleague_id)
    if status in ["Present", "Absent"]:
        colleague.status = status
        db.session.commit()
    return redirect(url_for("attendance"))


@app.route("/save-roles", methods=["POST"])
def save_roles():
    roles = request.json.get("roles", {})
    for colleague_id, role in roles.items():
        colleague = Colleague.query.get(int(colleague_id))
        if colleague:
            colleague.role = role  # Save role
            db.session.commit()
    return {"message": "Roles saved successfully"}, 200


@app.route("/clear-roles", methods=["POST"])
def clear_roles():
    colleagues = Colleague.query.all()
    for colleague in colleagues:
        colleague.role = None  # Clear role
        db.session.commit()
    return {"message": "Roles cleared successfully"}, 200


@app.route("/view-notes", methods=["GET"])
def view_notes():
    categories = Note.query.with_entities(Note.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template("view_notes.html", categories=categories)


@app.route("/add-category-notes/<category>", methods=["GET", "POST"])
def add_category_notes(category):
    # Fetch the current editor
    editor = Colleague.query.filter_by(role="Editor", status="Present").first()
    editor_name = editor.name if editor else "No Editor Assigned"
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        if title and content:
            new_note = Note(
                category=category, title=title, content=content, editor_name=editor_name
            )
            db.session.add(new_note)
            db.session.commit()
    notes = Note.query.filter_by(category=category).all()
    completed_count = Note.query.filter_by(
        category=category, status="Completed"
    ).count()
    inquery_count = Note.query.filter_by(category=category, status="In-Query").count()
    return render_template(
        "add_category_notes.html",
        category=category,
        notes=notes,
        editor_name=editor_name,
        completed_count=completed_count,
        inquery_count=inquery_count,
    )


@app.route("/delete-note/<int:note_id>/<category>", methods=["POST"])
def delete_note(note_id, category):
    note = Note.query.get(note_id)
    if note:
        db.session.delete(note)
        db.session.commit()
    return redirect(url_for("add_category_notes", category=category))


@app.route("/view-notes/<category>")
def view_category_notes(category):
    notes = Note.query.filter_by(category=category).all()
    return render_template("category_notes.html", category=category, notes=notes)


@app.route("/modify_note/<int:note_id>/<category>", methods=["POST"])
def modify_note(note_id, category):
    # Get the note object by ID
    note = Note.query.get(note_id)

    # Check if the note exists
    if not note:
        # Handle error if note doesn't exist (optional)
        return redirect(url_for("notes_view", category=category))

    # Get form data
    title = request.form.get("title")
    content = request.form.get("content")
    modifier_name = request.form.get("modifier_name")

    # Update the note
    note.title = title
    note.content = content
    note.modifier_name = modifier_name  # Update the modifier_name field

    # Commit changes to the database
    db.session.commit()

    # Redirect to the notes view after saving
    return redirect(url_for("add_category_notes", category=category))


@app.cli.command("update-notes-dates")
def update_notes_dates():
    """Update notes with missing created_date and edited_date."""
    from datetime import datetime

    notes = Note.query.all()
    for note in notes:
        updated = False
        if note.created_date is None:
            note.created_date = datetime.utcnow()
            updated = True
        if note.edited_date is None:
            note.edited_date = datetime.utcnow()
            updated = True
        if updated:
            db.session.add(note)
    db.session.commit()
    click.echo("Updated notes with missing created_date and edited_date.")


@app.route("/update-note-status/<int:note_id>/<category>", methods=["POST"])
def update_note_status(note_id, category):
    note = Note.query.get_or_404(note_id)
    status = request.form.get("status")
    if status in ["In-Query", "Completed"]:
        note.status = status
        db.session.commit()
    return redirect(url_for("add_category_notes", category=category))


# New route to list categories with count of "In-Query" notes
@app.route("/categories")
def list_categories():
    # Get distinct categories
    categories = Note.query.with_entities(Note.category).distinct().all()
    categories = [c[0] for c in categories]

    category_note_counts = {}
    for category in categories:
        in_query_count = Note.query.filter_by(
            category=category, status="In-Query"
        ).count()
        category_note_counts[category] = in_query_count

    return render_template(
        "categories.html",
        categories=categories,
        category_note_counts=category_note_counts,
    )


if __name__ == "__main__":
    app.run(debug=True)
