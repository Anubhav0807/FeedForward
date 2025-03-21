from flask import Flask, render_template, redirect, request, session
from flask_cors import CORS
import mysql.connector
import hashlib

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.secret_key = "yerav_machine"
CORS(app)

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
    
    if request.method == "GET":
        return render_template("provider.html")
    elif request.method == "POST":
        cursor.execute(f"""INSERT INTO available_food(
            email, food_name, mess_name, amount, food_type, location
            ) VALUES (
            '{session["email"]}',
            '{request.form["food-name"]}',
            '{request.form["mess-name"]}',
             {request.form["amount"]},
            '{request.form["food-type"]}',
            '{request.form["location"]}')
        """)
        mydb.commit()

        foodImage = request.files["food-image"]
        if foodImage:
            fileExtension = '.' + foodImage.filename.split('.')[-1]
            filePath = app.config["UPLOAD_FOLDER"] + '/' + str(cursor.lastrowid) + fileExtension
            foodImage.save(filePath)
            cursor.execute(f"INSERT INTO food_images VALUES({cursor.lastrowid}, '{filePath}')")
            mydb.commit()
        
        return render_template("provider.html")

@app.route("/receiver")
def receiver():
    if not (session["auth"] and session["service"] == "receiver"):
        return redirect("/login")

    cursor.execute("SELECT food_name, mess_name, amount, food_type, location FROM available_food")
    output = cursor.fetchall()
    cursor.execute("SELECT af.id, fi.img_url FROM available_food af LEFT JOIN food_images fi ON af.id = fi.id")
    img_urls = [row[1] if row[1] else "static/images/logo.png" for row in cursor.fetchall()]
    
    return render_template("receiver.html", zipped_data=zip(output, img_urls))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", auth=session["auth"], service=session["service"])
    
    elif request.method == "POST":
        email = request.form["email"]
        pwHash = hashlib.sha256(request.form["password"].encode()).hexdigest()

        if len(request.form) == 2:
            # Login
            cursor.execute(f"SELECT hash, service FROM users WHERE email='{email}'")
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
                cursor.execute(f"""INSERT INTO users VALUES(
                    '{request.form["username"]}', 
                    '{request.form["email"]}', 
                    '{pwHash}', 
                    '{request.form["service"]}')
                """)
                mydb.commit()
                session["auth"] = True
                session["email"] = request.form["email"]
                session["service"] = request.form["service"]
                return render_template("index.html", auth=session["auth"], service=session["service"])
            except mysql.connector.errors.IntegrityError:
                return render_template("signup.html", email_error="Email Already Exists.")

# To run the server on your local network
if __name__ == "__main__":
    
    # Establish a connection with MySQL RDBMS
    mydb = mysql.connector.connect(
        host="localhost",
        user="root",
        password="".join(i[0] for i in "the india's grand entrance road".split())
    )
    cursor = mydb.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS feed_forward")
    cursor.execute("USE feed_forward")
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
            img_url VARCHAR(32),
            FOREIGN KEY (id) REFERENCES available_food(id) ON DELETE CASCADE
        )
    """)

    # Allow Flask to be accessible from other devices on the same network
    app.run(host="0.0.0.0", port=5000, debug=True)
    mydb.close()
