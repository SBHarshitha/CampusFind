from flask import Flask, request, send_from_directory
from werkzeug.utils import secure_filename
from markupsafe import escape
import sqlite3
import os
import uuid

app = Flask(__name__)

# ---------------- CONFIGURATION ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "campusfind.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect(DATABASE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL,
            image TEXT
        )
    """)

    # Add the image column to an existing database if necessary.
    columns = [
        column[1]
        for column in conn.execute(
            "PRAGMA table_info(reports)"
        ).fetchall()
    ]

    if "image" not in columns:
        conn.execute(
            "ALTER TABLE reports ADD COLUMN image TEXT"
        )

    conn.commit()
    conn.close()


def get_reports(search="", status="All"):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT id, item, category, location, status, image
        FROM reports
        WHERE (
            item LIKE ?
            OR category LIKE ?
            OR location LIKE ?
        )
    """

    keyword = f"%{search}%"
    params = [keyword, keyword, keyword]

    if status in ["Lost", "Found"]:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id DESC"

    reports = conn.execute(query, params).fetchall()
    conn.close()

    return reports


init_db()


# ---------------- IMAGE UPLOAD ROUTE ----------------

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


# ---------------- MAIN WEBSITE ----------------

@app.route("/", methods=["GET", "POST"])
def home():
    message = ""

    if request.method == "POST":

        item = request.form.get("item", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        status = request.form.get("status", "")

        uploaded_image = request.files.get("image")
        image_filename = None

        # Validate the report details.
        if (
            not item
            or not category
            or not location
            or status not in ["Lost", "Found"]
        ):
            message = "Please fill in all report details."

        else:
            # Save the photo, if one was selected.
            if uploaded_image and uploaded_image.filename:

                original_filename = secure_filename(
                    uploaded_image.filename
                )

                if (
                    not original_filename
                    or "." not in original_filename
                    or original_filename.rsplit(".", 1)[1].lower()
                    not in ALLOWED_EXTENSIONS
                ):
                    message = (
                        "Invalid photo format. "
                        "Use PNG, JPG, JPEG, GIF, or WEBP."
                    )

                else:
                    extension = original_filename.rsplit(
                        ".", 1
                    )[1].lower()

                    # Unique filename prevents accidental overwriting.
                    image_filename = (
                        f"{uuid.uuid4().hex}.{extension}"
                    )

                    image_path = os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        image_filename
                    )

                    uploaded_image.save(image_path)

            # Save the report in SQLite.
            if not message:
                try:
                    conn = sqlite3.connect(DATABASE)

                    conn.execute("""
                        INSERT INTO reports
                        (item, category, location, status, image)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        item,
                        category,
                        location,
                        status,
                        image_filename
                    ))

                    conn.commit()
                    conn.close()

                    message = "Report saved successfully!"

                except sqlite3.Error:
                    message = (
                        "Could not save the report. "
                        "Please check the VS Code terminal."
                    )

    # Get search and filter settings.
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "All")

    if status_filter not in ["All", "Lost", "Found"]:
        status_filter = "All"

    reports = get_reports(search, status_filter)

    # Build the saved reports section.
    report_html = ""

    for report in reports:

        image_html = ""

        if report["image"]:
            image_html = f"""
                <img
                    src="/uploads/{escape(report['image'])}"
                    alt="Photo of {escape(report['item'])}"
                    class="item-photo"
                >
            """

        report_html += f"""
            <div class="report-card">

                {image_html}

                <h3>{escape(report['item'])}</h3>

                <p>
                    <strong>Category:</strong>
                    {escape(report['category'])}
                </p>

                <p>
                    <strong>Location:</strong>
                    {escape(report['location'])}
                </p>

                <p>
                    <strong>Status:</strong>
                    <span class="status-badge">
                        {escape(report['status'])}
                    </span>
                </p>

                <p>
                    <small>Report ID: {report['id']}</small>
                </p>

            </div>
        """

    # Display the website.
    return f"""
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">

        <title>CampusFind - Lost and Found</title>

        <link rel="stylesheet" href="/static/style.css">

        <style>
            .main-container {{
                max-width: 1000px;
                margin: 30px auto;
                padding: 20px;
            }}

            .form-section, .search-section {{
                background: white;
                padding: 24px;
                margin-bottom: 25px;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
            }}

            .form-section input,
            .form-section select,
            .search-section input,
            .search-section select {{
                box-sizing: border-box;
                width: 100%;
                padding: 12px;
                margin: 8px 0 16px;
                border: 1px solid #ccc;
                border-radius: 8px;
            }}

            button {{
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }}

            .report-grid {{
                display: grid;
                grid-template-columns: repeat(
                    auto-fit, minmax(240px, 1fr)
                );
                gap: 20px;
            }}

            .report-card {{
                background: white;
                padding: 18px;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
                overflow-wrap: anywhere;
            }}

            .item-photo {{
                display: block;
                width: 100%;
                max-width: 300px;
                height: 200px;
                object-fit: contain;
                margin: 0 auto 15px;
                border-radius: 10px;
                background: #f3f0ff;
            }}

            .status-badge {{
                font-weight: bold;
            }}

            .success-message {{
                padding: 12px;
                color: #166534;
                background: #dcfce7;
                border-radius: 8px;
            }}

            .empty-message {{
                background: white;
                padding: 20px;
                border-radius: 10px;
            }}

            @media (max-width: 600px) {{
                .main-container {{
                    margin: 10px auto;
                    padding: 12px;
                }}
            }}
        </style>
    </head>

    <body>

        <div class="main-container">

            <header>
                <h1>🎓 CampusFind</h1>
                <h2>Lost something? Let's help you find it!</h2>
                <p>
                    Report lost items and help reunite
                    people with their belongings.
                </p>
            </header>

            <section class="form-section">
                <h2>📝 Submit a Report</h2>

                <form method="POST"
                      enctype="multipart/form-data">

                    <label for="item">Item Name:</label>

                    <input
                        id="item"
                        type="text"
                        name="item"
                        placeholder="e.g. Black wallet"
                        required
                    >

                    <label for="category">Category:</label>

                    <input
                        id="category"
                        type="text"
                        name="category"
                        placeholder="e.g. Accessories"
                        required
                    >

                    <label for="location">Location:</label>

                    <input
                        id="location"
                        type="text"
                        name="location"
                        placeholder="Where was it lost or found?"
                        required
                    >

                    <label for="status">Report Type:</label>

                    <select id="status" name="status">
                        <option value="Lost">Lost</option>
                        <option value="Found">Found</option>
                    </select>

                    <label for="image">Upload Item Photo:</label>

                    <input
                        id="image"
                        type="file"
                        name="image"
                        accept=".png,.jpg,.jpeg,.gif,.webp"
                    >

                    <p>
                        Maximum photo size: 5 MB.
                        A photo is optional.
                    </p>

                    <button type="submit">
                        Submit Report
                    </button>

                </form>

                {f'<p class="success-message">{escape(message)}</p>' if message else ''}
            </section>

            <section class="search-section">
                <h2>🔍 Search and Filter Reports</h2>

                <form method="GET">

                    <label for="search">Search reports:</label>

                    <input
                        id="search"
                        type="text"
                        name="search"
                        placeholder="Search item, category, or location"
                        value="{escape(search)}"
                    >

                    <label for="status-filter">Filter by status:</label>

                    <select id="status-filter" name="status">

                        <option value="All"
                            {"selected" if status_filter == "All" else ""}>
                            All Items
                        </option>

                        <option value="Lost"
                            {"selected" if status_filter == "Lost" else ""}>
                            Lost Only
                        </option>

                        <option value="Found"
                            {"selected" if status_filter == "Found" else ""}>
                            Found Only
                        </option>

                    </select>

                    <button type="submit">Search</button>

                    <a href="/">Show All</a>

                </form>
            </section>

            <section class="reports-section">
                <h2>📋 Lost and Found Reports</h2>

                <div class="report-grid">
                    {
                        report_html
                        if report_html
                        else '<p class="empty-message">No matching reports found.</p>'
                    }
                </div>
            </section>

        </div>

    </body>
    </html>
    """


# ---------------- START WEBSITE ----------------

if __name__ == "__main__":
    app.run(debug=True)