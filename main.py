import os
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
import sqlite3
from deepface import DeepFace

app = Flask(__name__)

# Configure the upload folder and allowed file extensions
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Database setup function to create the table if it doesn't exist
def create_db():
    conn = sqlite3.connect('mini.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS forms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    crime_name TEXT,
                    crime_date TEXT,
                    prison_date TEXT,
                    year INTEGER,
                    summary TEXT,
                    image_path TEXT)''')
    conn.commit()
    conn.close()

# Function to save form data into the database
def save_to_db(name, crime_name, crime_date, prison_date, year, summary, image_path):
    conn = sqlite3.connect('mini.db')
    c = conn.cursor()
    c.execute("INSERT INTO forms (name, crime_name, crime_date, prison_date, year, summary, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)", 
              (name, crime_name, crime_date, prison_date, year, summary, image_path))
    conn.commit()
    conn.close()

# Route to display the form
@app.route('/')
def index():
    return render_template('mini.html')

# Route to handle image upload and face analysis
@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'Image is missing'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # Check the database for matching faces
        conn = sqlite3.connect('mini.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, image_path FROM forms")
        database_images = cursor.fetchall()
        conn.close()

        for record in database_images:
            db_name, db_image_path = record
            if db_image_path != filepath:  # Avoid comparing the uploaded image with itself
                result = DeepFace.verify(img1_path=filepath, img2_path=db_image_path, model_name='Facenet')
                if result["verified"]:
                    conn = sqlite3.connect('mini.db')
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM forms WHERE name = ?", (db_name,))
                    matched_entry = cursor.fetchone()
                    conn.close()

                    return jsonify({
                        'match': True,
                        'details': {
                            'name': matched_entry[1],
                            'crime_name': matched_entry[2],
                            'crime_date': matched_entry[3],
                            'prison_date': matched_entry[4],
                            'year': matched_entry[5],
                            'summary': matched_entry[6]
                        }
                    })
        return jsonify({'match': False, 'message': 'No match found in the database'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route to handle form submission
@app.route('/submit', methods=['POST'])
def submit_form():
    if 'image' not in request.files:
        return "No file part"
    image = request.files['image']
    
    if image.filename == '':
        return "No selected file"
    
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save the image to the uploads folder
        image.save(image_path)

        # Collect other form data
        name = request.form['name']
        crime_name = request.form['crime_name']
        crime_date = request.form['crime_date']
        prison_date = request.form['prison_date']
        year = request.form['year']
        summary = request.form['summary']

        # Save the data into the database
        save_to_db(name, crime_name, crime_date, prison_date, year, summary, image_path)

        return "Data saved successfully!"

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])



# Create the database (if not already created)
create_db()

if __name__ == '__main__':
    app.run(debug=True)
