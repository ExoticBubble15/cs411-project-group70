from flask import Flask, request, jsonify, session 
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
# from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__) 
app.config['SQLALCHEMY_DATABASE_URI'] =
db = SQLAlchemy(app)

class User (): 
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password


@app.route('/signup', methods= ['POST'])
def signup ():
    data = request.get_json()
    username = data['username']
    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'User already exists'}), 409

    password = generate_password_hash(data['password']) 
    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()      
    return jsonify({'message': 'Account created successfully'}), 201
@app.route('/login', methods= ['POST'])
def login ():
    data = request.get_json()
    username = data['username']
    password = data['password']
  
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    if check_password_hash(user.password, password):
        return jsonify({'message': 'Login successful'}), 200
    else:
        return jsonify({'message': 'Invalid username or password'}), 401
