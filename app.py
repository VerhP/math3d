# MIT License
#
# Copyright (c) 2017 Luming Chen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import datetime
import json
from flask import (Flask, render_template, redirect, request, abort, url_for,
                   make_response, abort, jsonify)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_sslify import SSLify

app = Flask(__name__)

CSRFProtect().init_app(app)

# Configurations
# Using environmental variables for secret key and database url
# Secret key is used to sign cookies, so it's secure to keep it hidden
app.config.update(
    SECRET_KEY=os.environ["SECRET_KEY"],
    SQLALCHEMY_DATABASE_URI=os.environ["DATABASE_URL"],
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Redirect to HTTPS if on Heroku
if "DYNO" in os.environ:
    sslify = SSLify(app)

# Must import after db is defined, not pretty
from models import User, Graph, Metadata

@app.after_request
def add_csrf_to_cookie(response):
    """Adds csrf_token to cookie

    Add to cookies with every response.
    """
    return_response = make_response(response)
    return_response.set_cookie("csrf_token", generate_csrf())
    return return_response

# Pages
@app.route('/')
def index(data="{}"):
    return render_template("index.html", graph=data)

@app.route('/register')
def register():
    errormessage = request.args.get("errormessage", default="")
    return render_template("register.html", errormessage=errormessage)

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/graph/<graph_hash>')
def get_graph(graph_hash):
    meta = Metadata.query.filter_by(short_url=graph_hash).first()
    if meta:
        # Increment times accessed
        meta.times_accessed += 1
        db.session.commit()

        # Serialize meta object after the times accessed
        # field has been incremented
        data = json.dumps(meta.graph.serialize())
        return index(data)
    return redirect(url_for("index"))

# Handlers for Client-Side Requests
@app.route('/api/graph/save', methods=["POST"])
def save_graph():
    # Angular sends json data by default
    title = request.json.get("title")
    settings = request.json.get("settings")
    username = request.cookies.get("username")

    new_graph = Graph(settings)
    db.session.add(new_graph)
    db.session.commit()
    
    new_meta = Metadata(title, new_graph.id, username)
    new_meta.generate_hash()
    db.session.add(new_meta)
    db.session.commit()

    return jsonify({
        "url": new_graph.meta.short_url,
        "result": "Success",
    })

@app.route('/api/graph/get')
def get_graphs():
    username = request.cookies.get("username")
    graph_objs = User.query.filter_by(username=username).first().graphs
    graphs = [graph.graph.serialize() for graph in graph_objs]
    
    return jsonify(graphs)

@app.route('/api/graph/load', methods=["POST"])
def load_graph():
    short_url = request.json.get("short_url")
    meta = Metadata.query.filter_by(short_url=short_url).first()
    
    # Increment times accessed
    meta.times_accessed += 1
    db.session.commit()
    
    settings = json.dumps(meta.graph.serialize().get("settings"))
    return jsonify({
        "result": "Success",
        "settings": settings
    })

@app.route('/api/login/validate', methods=["POST"])
def validate():
    username = request.form.get("username")
    password = request.form.get("password")

    if "" in [username, password]:
        return redirect(url_for("login"))

    if validate_password(username, password):
        response = redirect(url_for("index"))
        return add_logged_in_cookie(response, username)
    else:
        return redirect(url_for("index"))

@app.route('/api/login/username_exists', methods=["POST"])
def check_username():
    """Checks if the given username already exists

    Javascript side sends post request to this address.
    """
    username = request.form.get("username")
    if username:
        if User.query.filter_by(username=username).first():
            return False
        else:
            return True

@app.route('/api/register/submit', methods=["POST"])
def submit():
    username = request.form.get("username")
    name = request.form.get("name", default="")
    email = request.form.get("email")
    password = request.form.get("password")

    # Quick way to check if any of these is empty
    # Should implement javascript password checker to prevent this
    if "" in [username, email, password]:
        errormessage = "Username, email, and password are required."
        return redirect(url_for("register", errormessage=errormessage))

    new_user = User(username, email, name, password)
    db.session.add(new_user)
    db.session.commit()

    response = redirect(url_for("index"))

    return add_logged_in_cookie(response, username)

# Helper Functions
def validate_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user:
        return user.check_password(password)
    else:
        return False

def add_logged_in_cookie(response, username):
    return_response = make_response(response)
    expiry_date = datetime.datetime.now()
    expiry_date += datetime.timedelta(days=30)
    return_response.set_cookie("username", username, expires=expiry_date)
    return return_response
