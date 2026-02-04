Certificate Generator System

A Flask-based backend application that automatically generates personalized certificates from uploaded templates and participant data using OCR-based placeholder detection.

This system allows authenticated users to upload certificate templates, detect placeholder text (e.g. NAME), and bulk-generate certificates with participant names rendered cleanly and consistently.

Key Features

User authentication (Register / Login / Logout)

Upload certificate templates (image-based)

OCR-based placeholder detection using Tesseract

Automatic removal of placeholder text via OpenCV inpainting

Bulk certificate generation from:

CSV file input

Manual name input

Consistent font sizing and auto-centering of names

Automatic text color adjustment based on background brightness

Download individual certificates

Download all certificates as a single PDF

Per-user certificate storage and isolation

How It Works (High Level)

User uploads a certificate template containing a placeholder like NAME

Tesseract OCR detects the placeholder position

Placeholder text is removed using OpenCV inpainting

Participant names are rendered at the detected position using selected fonts

Certificates are generated in bulk and saved per user

Users can download certificates individually or as a combined PDF

Tech Stack

Backend: Python, Flask

Database: SQLite, SQLAlchemy

Authentication: Flask-Login

OCR: Tesseract (pytesseract)

Image Processing: OpenCV, Pillow

PDF Generation: FPDF

Frontend: Jinja2 templates (Flask)

Project Structure
Cert_Genn/
│
├── app.py              # Main Flask application
├── templates/          # HTML templates
├── assets/             # Static files (CSS, fonts, images)
├── screenshots/        # Application screenshots (optional)
├── .gitignore
├── README.md

Setup & Running Locally
Prerequisites

Python 3.x

Tesseract OCR installed

Virtual environment recommended

Steps
git clone <repo-url>
cd Cert_Genn
pip install -r requirements.txt
python app.py


Access the app at:

http://127.0.0.1:5000

Notes

This project currently runs locally

Database and generated files are excluded from version control

Deployment can be done using Docker or a cloud platform (future improvement)

Future Improvements

Cloud deployment (AWS / Render / Railway)

Support for PDF template uploads

Admin role for bulk management

Better OCR fallback handling

UI improvements

Why This Project Matters

This project demonstrates:

Real-world backend problem solving

File handling and automation

OCR integration

Image manipulation

Authentication and user isolation

Clean backend logic beyond CRUD apps

Author

Kae
Backend Developer
