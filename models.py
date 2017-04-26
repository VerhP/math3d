from datetime import datetime

from app import db, bcrypt

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    first_name = db.Column(db.String())
    last_name = db.Column(db.String())
    pw_hash = db.Column(db.String())
    posts = db.relationship("Graph", backref="user", lazy="dynamic")
    
    def __init__(self, username, email, first_name, last_name, password):
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    
    def check_password(password):
        return bcrypt.check_password_hash(self.pw_hash, password)

class Graph(db.Model):
    __tablename__ = "graphs"
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    title = db.Column(db.String())
    serialized_string = db.Column(db.String())
    
    def __init__(self, serialized_string):
        self.created_at = datetime.utcnow()
        self.serialized_string = serialized_string
        