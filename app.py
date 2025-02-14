from flask import Flask, render_template, request, redirect
from flask_cors import CORS
import mysql.connector
import hashlib

app = Flask(__name__)
CORS(app)

auth = False
service = ""

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/login")
def login():
    return render_template("login.html", pw_error="", email_error="")

@app.route("/about")
def about():
    return render_template("about.html", auth=auth)

@app.route("/provider")
def provider():
    if auth:
        return render_template("provider.html")
    else:
        return redirect("/")

@app.route("/", methods=["GET", "POST"])
def index():
    global auth, service
    if request.method == "GET":
        return render_template("index.html", auth=auth, service=service)
    elif request.method == "POST":
        pwHash = hashlib.sha256(request.form["password"].encode()).hexdigest()

        if len(request.form) == 2:
            # Login
            cursor.execute(f"SELECT hash, service FROM users WHERE email='{request.form["email"]}'")
            row = cursor.fetchone()
            if row is None:
                return render_template("login.html", pw_error="", email_error="Email does not exists.")
            storedHash, service = row
            if (pwHash == storedHash):
                auth = True
                return render_template("index.html", auth=auth, service=service)
            else:
                return render_template("login.html", pw_error="Invalid Password.", email_error="")
            
        else:
            # Signup
            cursor.execute(f"""INSERT INTO users VALUES(
                '{request.form["username"]}', 
                '{request.form["email"]}', 
                '{pwHash}', 
                '{request.form["service"]}')
            """)
            mydb.commit()
            return render_template("index.html")

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

    # Allow Flask to be accessible from other devices on the same network
    app.run(host="0.0.0.0", port=5000)
    mydb.close()
