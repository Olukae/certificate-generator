import os
import pandas as pd
import pytesseract
import cv2
import numpy as np  
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
import tempfile

# Flask setup
app = Flask(__name__)
app.config["SECRET_KEY"] = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["CERT_FOLDER"] = "certificates"

# Ensure directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["CERT_FOLDER"], exist_ok=True)

# Initialize database and login manager
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Path to Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Fonts
FONT_DIR = os.path.join(os.path.dirname(__file__), "assets", "fonts")
AVAILABLE_FONTS = {
    "Alex Brush": os.path.join(FONT_DIR, "Alex Brush.ttf"),
    "Great Vibes": os.path.join(FONT_DIR, "Great Vibes.ttf"),
    "Authentic Signature": os.path.join(FONT_DIR, "Authentic Signature.ttf"),
    "Thesignature": os.path.join(FONT_DIR, "Thesignature.ttf"),
}
 
# Database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

# Create tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Placeholder detection
PLACEHOLDER_VARIANTS = ["NAME"]

def detect_placeholder(img_path):
    """Detect a placeholder in the uploaded certificate template."""
    img = Image.open(img_path)
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

    for i, word in enumerate(data["text"]):
        if word.strip().upper() in PLACEHOLDER_VARIANTS:
            return {
                "text": word.strip(),
                "x": data["left"][i],
                "y": data["top"][i],
                "w": data["width"][i],
                "h": data["height"][i]
            }, None
    return None, "❌ No valid placeholder found. Include a placeholder like NAME in the template."

# Certificate generation (Updated for larger fonts)
def generate_certificate(template_path, name, placeholder, font_choice="Great Vibes"):
    """Generate a certificate image with the given name. Removes ONLY the placeholder via OpenCV inpainting.
    FIXED: Better font sizing for visibility."""
    cert_img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(cert_img)
    font_path = AVAILABLE_FONTS.get(font_choice, AVAILABLE_FONTS["Great Vibes"])

    if placeholder:
        x, y, w, h = placeholder["x"], placeholder["y"], placeholder["w"], placeholder["h"]
        
        # Step 1: Remove ONLY the placeholder using OpenCV inpainting
        img_cv = cv2.cvtColor(np.array(cert_img), cv2.COLOR_RGB2BGR)
        
        # Create mask for JUST the placeholder area
        mask = np.zeros(img_cv.shape[:2], dtype=np.uint8)
        cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
        
        # Inpaint: Fill the masked area using surrounding pixels
        img_inpainted = cv2.inpaint(img_cv, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
        
        # Convert back to PIL
        cert_img = Image.fromarray(cv2.cvtColor(img_inpainted, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(cert_img)
        
        # Step 2: FIXED FONT SIZE - Same size for ALL names
        # Use placeholder height to determine ONE consistent size
        # DO NOT reduce size based on name length
        
        fixed_font_size = max(55, int(h * 1.5))  # Fixed size based on placeholder
        fixed_font_size = min(fixed_font_size, 85)  # Cap at 85pt
        
        try:
            font = ImageFont.truetype(font_path, fixed_font_size)
            bbox = font.getbbox(name)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except Exception:
            # Fallback if font loading fails
            font = ImageFont.truetype(font_path, 55)
            bbox = font.getbbox(name)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        
        # Auto-contrast text color based on background
        try:
            sample_x = min(max(x + w//2, 0), cert_img.width - 1)
            sample_y = min(max(y + h//2, 0), cert_img.height - 1)
            avg_brightness = sum(cert_img.getpixel((sample_x, sample_y))) // 3
            text_fill = "white" if avg_brightness < 128 else "black"
        except:
            text_fill = "black"  # Safe default
        
        # Center text in placeholder area
        text_x = x + (w - text_w) / 2
        text_y = y + (h - text_h) / 2
        
        # Ensure text stays within image bounds
        text_x = max(0, min(text_x, cert_img.width - text_w))
        text_y = max(0, min(text_y, cert_img.height - text_h))
        
        draw.text((text_x, text_y), name, fill=text_fill, font=font)
    
    else:
        # Fallback: Center text if no placeholder detected
        W, H = cert_img.size
        
        # Start with a large font and scale down if needed
        font_size = 120  # Increased from 80
        font = None
        
        while font_size >= 40:
            try:
                font = ImageFont.truetype(font_path, font_size)
                bbox = font.getbbox(name)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                
                # Allow 80% of image width for text
                if text_w <= W * 0.8:
                    break
                font_size -= 5
            except:
                font_size -= 5
        
        if not font:
            font = ImageFont.truetype(font_path, 60)
            bbox = font.getbbox(name)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        
        text_x = (W - text_w) / 2
        text_y = (H - text_h) / 2
        draw.text((text_x, text_y), name, fill="black", font=font)

    return cert_img

# Routes (unchanged)
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if User.query.filter_by(username=username).first():
            flash("Username already exists")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash("Invalid username or password")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        template_file = request.files.get("template")
        csv_file = request.files.get("csv_file")
        manual_names = request.form.get("manual_names")
        font_choice = request.form.get("font_choice", "Great Vibes")

        if not template_file:
            flash("Please upload a certificate template.")
            return redirect(url_for("dashboard"))

        # Save template
        filename = secure_filename(template_file.filename)
        template_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        template_file.save(template_path)

        # Detect placeholder
        placeholder, error = detect_placeholder(template_path)
        if error:
            flash(error)
            return redirect(url_for("dashboard"))

        # Collect names
        names = []
        if csv_file and csv_file.filename != "":
            try:
                df = pd.read_csv(csv_file)
                if "name" in df.columns:
                    names.extend(df["name"].dropna().tolist())
            except Exception:
                flash("Error reading CSV file.")
                return redirect(url_for("dashboard"))

        if manual_names:
            if "," in manual_names:
                names.extend([n.strip() for n in manual_names.split(",") if n.strip()])
            else:
                names.extend([n.strip() for n in manual_names.split("\n") if n.strip()])

        if not names:
            flash("No names provided.")
            return redirect(url_for("dashboard"))

        # Generate certificates
        for name in names:
            out_filename = f"{name.strip().replace(' ', '_')}.png"
            out_path = os.path.join(app.config["CERT_FOLDER"], out_filename)

            if os.path.exists(out_path):
                continue  # skip existing

            cert_img = generate_certificate(template_path, name, placeholder, font_choice)
            cert_img.save(out_path)

            new_cert = Certificate(filename=out_filename, user_id=current_user.id)
            db.session.add(new_cert)

        db.session.commit()
        flash("Certificates generated successfully!")

    # Show only existing certificate files
    all_files = set(os.listdir(app.config["CERT_FOLDER"]))
    certs = Certificate.query.filter_by(user_id=current_user.id).all()
    certs = [c for c in certs if c.filename in all_files]

    return render_template("dashboard.html", certs=certs, fonts=AVAILABLE_FONTS.keys())

@app.route("/clear_all_files")
@login_required
def clear_all_files():
    certs = Certificate.query.filter_by(user_id=current_user.id).all()
    files_cleared = 0
    for cert in certs:
        file_path = os.path.join(app.config["CERT_FOLDER"], cert.filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                files_cleared += 1
            except Exception:
                continue
        db.session.delete(cert)
    db.session.commit()
    flash(f"Cleared {files_cleared} certificate file(s) and database records.")
    return redirect(url_for("dashboard"))

@app.route("/download/<filename>")
@login_required
def download(filename):
    file_path = os.path.join(app.config["CERT_FOLDER"], filename)
    if not os.path.exists(file_path):
        flash(f"File '{filename}' not found. It may have been deleted.")
        return redirect(url_for("dashboard"))
    return send_from_directory(app.config["CERT_FOLDER"], filename, as_attachment=True)

@app.route("/download_all")
@login_required
def download_all():
    certs = Certificate.query.filter_by(user_id=current_user.id).all()
    if not certs:
        flash("No certificates available to download.")
        return redirect(url_for("dashboard"))

    pdf_path = os.path.join(app.config["CERT_FOLDER"], f"{current_user.username}_certificates.pdf")
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=0)

    for cert in certs:
        img_path = os.path.join(app.config["CERT_FOLDER"], cert.filename)
        if not os.path.exists(img_path):
            continue
        with Image.open(img_path) as im:
            orig_w, orig_h = im.size
            needs_rotate = orig_w > orig_h
            if needs_rotate:
                im_rot = im.rotate(90, expand=True)
                w, h = im_rot.size
                fd, temp_path = tempfile.mkstemp(suffix='.png')
                im_rot.save(temp_path)
                os.close(fd)
                image_to_use = temp_path
            else:
                w, h = orig_w, orig_h
                image_to_use = img_path
            # Compute scaling to fit A4 portrait (210x297 mm)
            scale_w = 210 / w
            scale_h = 297 / h
            scale = min(scale_w, scale_h)
            target_w = w * scale
            target_h = h * scale
            x = (210 - target_w) / 2
            y = (297 - target_h) / 2
            pdf.add_page()
            pdf.image(image_to_use, x=x, y=y, w=target_w, h=target_h)
            if needs_rotate:
                os.unlink(temp_path)

    pdf.output(pdf_path)
    return send_file(pdf_path, as_attachment=True)

# Run the app
if __name__ == "__main__":
    app.run(debug=True)