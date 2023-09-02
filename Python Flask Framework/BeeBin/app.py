# Import required modules
import os
import shutil
import mimetypes
from uuid import uuid4
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, url_for, redirect, send_from_directory

# Initialize Flask app
app = Flask(__name__)

# Define the upload folder and its size limit
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Helper function to convert file sizes from bytes (B) to kilobytes (KB), megabytes (MB), gigabytes (GB), or terabytes (TB)
def human_readable_size(size, decimal_places=2):
    # Iterate over a list of units of measurement
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        # If size is less than 1024, stop iterating
        if size < 1024.0:
            break
        # Divide size by 1024 to convert to the next unit of measurement
        size /= 1024.0
    # Return a formatted string with the size and unit of measurement
    return f"{size:.{decimal_places}f} {unit}"

# Helper function for time since upload
def time_ago(time):
    # Get the current time
    now = datetime.now()
    # Calculate the difference between the current time and the input time
    diff = now - time
    
    # Check if the difference is less than 1 second
    if diff.total_seconds() < 1:
        return "now"
    # Check if the difference is less than 60 seconds
    elif diff.total_seconds() < 60:
        return f"{int(diff.total_seconds())} seconds ago"
    # Check if the difference is less than 3600 seconds (1 hour)
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)} minutes ago"
    # Check if the difference is less than 86400 seconds (1 day)
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)} hours ago"
    # Check if the difference is less than 604800 seconds (7 days)
    elif diff.total_seconds() < 604800:
        return f"{int(diff.total_seconds() / 86400)} days ago"
    # If the difference is greater than or equal to 604800 seconds, return the date and time of the input time
    else:
        return time.strftime('%Y-%m-%d %H:%M:%S')


# Define the main route which generates a unique bin ID and renders the index.html template
@app.route('/')
def index():
    bin_id = str(uuid4())[:8]
    return render_template("index.html", bin_id=bin_id)

# Define a dynamic route for each bin ID, supports both GET and POST methods
@app.route('/<bin_id>', methods=['GET', 'POST'])
def file_bin(bin_id):
    if request.method == 'POST':  # Handle POST requests for file uploads
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:  # Save the uploaded file
            filename = os.path.join(app.config['UPLOAD_FOLDER'], bin_id, file.filename)
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            file.save(filename)
            return redirect(url_for('file_bin', bin_id=bin_id))

    # Handle GET requests to show the list of uploaded files
    files = []
    bin_folder = os.path.join(app.config['UPLOAD_FOLDER'], bin_id)
    if os.path.exists(bin_folder):
        for filename in os.listdir(bin_folder):
            file_path = os.path.join(bin_folder, filename)
            uploaded_time = datetime.fromtimestamp(os.path.getctime(file_path))
            file_info = {
                "filename": filename,
                "content_type": mimetypes.guess_type(filename)[0] or "Unknown",
                "size": human_readable_size(os.path.getsize(file_path)),
                "uploaded_time": time_ago(uploaded_time)
            }
            files.append(file_info)

    return render_template("bin.html", bin_id=bin_id, files=files)

# Define a route for serving uploaded files
@app.route("/uploads/<bin_id>/<filename>")
def uploaded_file(bin_id, filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], bin_id), filename)

# Define a route to handle file deletion
@app.route("/delete/<bin_id>/<filename>", methods=['GET'])
def delete_file(bin_id, filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], bin_id, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('file_bin', bin_id=bin_id))

# Define a route to handle the takedown of an entire bin
@app.route("/bin/<bin_id>/takedown", methods=['POST'])
def takedown_bin(bin_id):
    bin_folder = os.path.join(app.config['UPLOAD_FOLDER'], bin_id)
    if os.path.exists(bin_folder):
        shutil.rmtree(bin_folder)  # Deletes the folder and its contents
    return redirect(url_for('index'))

# Main entry point for the Flask application
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)