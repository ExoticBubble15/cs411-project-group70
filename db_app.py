from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import hashlib
import os

#flask setup
app = Flask(__name__)

#db configuration
DATABASE_URL = "sqlite:///users.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

#user schema
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    salt = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

#create db
Base.metadata.create_all(engine)

#helper functions
#hash pwds
def hash_pwd(pwd, salt):
    return hashlib.sha256((pwd + salt).encode()).hexdigest()
#generate salt
def gen_salt():
    return os.urandom(16).hex()

#create routes

#LOGIN ROUTE

@app.route('/')
def home():
    return "<h1>Welcome to the User Login and Registration API!</h1>"
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    #if either field is left blank, return BAD REQUEST response 
    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    session = Session()
    try:
        #if user already exists, return CONFLICT response
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return jsonify({"error": "Invalid username or password."}), 401

        hashed_pwd = hash_pwd(password, user.salt)
        if hashed_pwd == user.hashed_pwd:
            return jsonify({"message": "Login successful."}), 200
        else:
            return jsonify({"error": "Invalid username or password."}), 401
    finally:
        session.close()


#CREATE-ACCOUNT ROUTE
@app.route('/create-account', methods=['POST'])
def create_account():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    #if either field is left blank, return BAD REQUEST response 
    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    session = Session()
    try:
        #if user already exists, return CONFLICT response
        if session.query(User).filter_by(username=username).first():
            return jsonify({"error": "Username already exists."}), 409
        salt = gen_salt()
        hashed_pwd = hash_pwd(password, salt)
        new_user = User(username = username, salt=salt,  hashed_password= hashed_pwd)
        session.add(new_user)
        session.commit()
        #if committed, return CREATED response
        return jsonify({"message": "Account created successfully!"}), 201
    finally:
        session.close()


if __name__ == '__main__':
    app.run(debug=True)

