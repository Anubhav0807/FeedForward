from flask import Flask, render_template, redirect, request, session, g
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import mysql.connector
import hashlib
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET")

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

def initialize_db():
    cursor = get_cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            username VARCHAR(32),
            email VARCHAR(32) PRIMARY KEY,
            hash CHAR(64),
            service ENUM('provider', 'receiver')
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS available_food(
            id INT PRIMARY KEY AUTO_INCREMENT,
            email VARCHAR(32),
            food_name VARCHAR(16),
            mess_name VARCHAR(16),
            amount INT,
            food_type VARCHAR(16),
            location VARCHAR(64),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_images(
            id INT PRIMARY KEY,
            img_url VARCHAR(256),
            FOREIGN KEY (id) REFERENCES available_food(id) ON DELETE CASCADE
        )
    """)

def get_db():
    if "db" not in g:
        g.db = mysql.connector.connect(
            host=os.getenv("HOST"),
            user=os.getenv("USER"),
            password=os.getenv("PASSWORD"),
            database=os.getenv("DATABASE")
        )
        initialize_db()
    return g.db

def get_cursor():
    return get_db().cursor()

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.before_request
def set_default_auth():
    session.setdefault("auth", False)
    session.setdefault("email", None)
    session.setdefault("service", None)

@app.route("/signup")
def signup():
    return render_template("signup.html", email_error="")

@app.route("/login")
def login():
    return render_template("login.html", pw_error="", email_error="")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/subscribe")
def subscribe():
    return render_template("subscribe.html", auth=session["auth"])

@app.route("/about")
def about():
    return render_template("about.html", auth=session["auth"])

@app.route("/provider", methods=["GET", "POST"])
def provider():
    if not (session["auth"] and session["service"] == "provider"):
        return redirect("/login")

    cursor = get_cursor()

    if request.method == "GET":
        return render_template("provider.html")
    
    # POST method
    cursor.execute("""
        INSERT INTO available_food(email, food_name, mess_name, amount, food_type, location)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        session["email"],
        request.form["food-name"],
        request.form["mess-name"],
        int(request.form["amount"]),
        request.form["food-type"],
        request.form["location"]
    ))
    get_db().commit()
    food_id = cursor.lastrowid

    foodImage = request.files["food-image"]
    if foodImage:
        upload_result = cloudinary.uploader.upload(foodImage, public_id=str(food_id))
        image_url = upload_result['secure_url']
        cursor.execute("INSERT INTO food_images VALUES (%s, %s)", (food_id, image_url))
        get_db().commit()

    return render_template("provider.html")

@app.route("/receiver")
def receiver():
    if not (session["auth"] and session["service"] == "receiver"):
        return redirect("/login")

    cursor = get_cursor()
    cursor.execute("SELECT food_name, mess_name, amount, food_type, location FROM available_food")
    output = cursor.fetchall()
    cursor.execute("SELECT af.id, fi.img_url FROM available_food af LEFT JOIN food_images fi ON af.id = fi.id")
    img_urls = [row[1] if row[1] else "static/images/logo.png" for row in cursor.fetchall()]
    
    return render_template("receiver.html", zipped_data=zip(output, img_urls))

@app.route("/", methods=["GET", "POST"])
def index():
    cursor = get_cursor()
    if request.method == "GET":
        return render_template("index.html", auth=session["auth"], service=session["service"])
    
    email = request.form["email"]
    pwHash = hashlib.sha256(request.form["password"].encode()).hexdigest()

    if len(request.form) == 2:
        # Login
        cursor.execute("SELECT hash, service FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        if row is None:
            return render_template("login.html", pw_error="", email_error="Email does not exist.")
        
        storedHash, service = row
        if pwHash == storedHash:
            session["auth"] = True
            session["email"] = email
            session["service"] = service
            return render_template("index.html", auth=session["auth"], service=session["service"])
        else:
            return render_template("login.html", pw_error="Invalid Password.", email_error="")
    
    else:
        # Signup
        try:
            cursor.execute("INSERT INTO users VALUES (%s, %s, %s, %s)", (
                request.form["username"],
                email,
                pwHash,
                request.form["service"]
            ))
            get_db().commit()
            session["auth"] = True
            session["email"] = email
            session["service"] = request.form["service"]
            return render_template("index.html", auth=session["auth"], service=session["service"])
        except mysql.connector.errors.IntegrityError:
            return render_template("signup.html", email_error="Email Already Exists.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
