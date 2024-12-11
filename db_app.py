from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import hashlib
import os
import sqlite3
import requests
import logging
from memory import Memory

#logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#flask setup
app = Flask(__name__)

#db configuration
DATABASE_URL = "sqlite:///users.db"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

#memory
#stores the most recent 10 successful api responses
memory = Memory(10) 

#user schema
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    salt = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    favorite_brew_1 = Column(JSON)
    favorite_brew_2 = Column(JSON)
    favorite_brew_3 = Column(JSON)
    favorite_brew_4 = Column(JSON)
    favorite_brew_5 = Column(JSON)

#create db
Base.metadata.create_all(engine)

#helper functions
#hashes a password according to a salt
def hash_pwd(pwd, salt):
    return hashlib.sha256((pwd + salt).encode()).hexdigest()
#generates a salt
def gen_salt():
    return os.urandom(16).hex()

#home page for front end (if we get there)
@app.route('/', methods=['POST','GET'])
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        return f"<h1>Welcome, {username}!</h1><p>Password received securely.</p>"

    
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>User Brew System</title>
        <style>
            body {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                font-family: Arial, sans-serif;
                background-color: #f3f3f3;
            }
            form {
                display: flex;
                flex-direction: column;
                   align-items: center; 
                padding: 20px;
                border: 1px solid #ccc;
                border-radius: 20px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                background: #fff;
            }
            h1 {
                text-align: center;
            }
            label {
                font-weight: bold;
                 align-self: flex-start;
            }
            input[type="text"], input[type="password"] {
               
                width: 70%;
                padding: 8px;
                margin: 8px 0;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            input[type="submit"] {
              
                width: 80%;
                padding: 10px;
                border: none;
                border-radius: 5px;
                background-color: #007BFF;
                color: white;
                font-size: 16px;
                cursor: pointer;
            }
            input[type="submit"]:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
        <div>
            <h1>Welcome to the User Brew system!</h1>
            <form method="POST">
                <label for="username">Username:</label><br>
                <input type="text" id="username" name="username"><br><br>
                
                <label for="password">Password:</label><br>
                <input type="password" id="password" name="password"><br><br>
                
                <input type="submit" value="Submit">
            </form>
        </div>
    </body>
    </html>
    """

   



##########################################
# requirement: secure password storage 
##########################################

@app.route('/login', methods=['POST'])
def login():
    """
    verifys the users password with the hashed password associated to 
    to the username in the database 

    expected JSON input:
        - username (str): the username of the account/user in the database
        - password (str): the password to be matched with the hashed password
    
    returns:
        JSON response indicating the status of logging in or any errors with inputs
    """
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
            return jsonify({"error": "Invalid username."}), 401

        hashed_pwd = hash_pwd(password, user.salt)
        if hashed_pwd == user.hashed_password :
            return jsonify({"message": "Login successful."}), 200
        else:
            return jsonify({"error": "Invalid password."}), 401
    except:
        return jsonify({"error": "error interacting with the db"}), 400
    finally:
        session.close()

@app.route('/create-account', methods=['POST'])
def create_account():
    """
    creates a new account in the database
    generates a salt and uses it to hash the password

    expected JSON input:
        - username (str): the username of the account/user
        - password (str): the password that will be salted/hashed
    
    returns:
        JSON response indicating successful account creation or any errors with inputs
    """
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
    except:
        return jsonify({"error": "error interacting with the db"}), 400
    finally:
        session.close()


@app.route('/update-password', methods=['POST'])
def update_password():
    """
    updates the password of an account after verifying that the
    user remembers the previous password

    expected JSON input:
        - username (str): the username of the account/user
        - oldPassword (str): the password used to log in
        - newPassword (str): what the password will be changed to
    
    returns:
        JSON response indicating the status of updating the password or errors with inputs
    """
    data = request.json
    username = data.get('username')
    oldPassword = data.get('oldPassword')
    newPassword = data.get('newPassword')
    if not username or not oldPassword or not newPassword:
        return jsonify({"error": "Username, old password, and new password are required."}), 400
    
    session = Session()
    try:
        user = session.query(User).filter_by(username=username).first()

        if user == None: #user doesnt exist
            return jsonify({"error": "username does not exist"}), 400
        
        hash_old_pwd = hash_pwd(oldPassword, user.salt)
        hash_new_pwd = hash_pwd(newPassword, user.salt)

        if hash_old_pwd != user.hashed_password: #old password does not match password in db
            return jsonify({"error": "incorrect old password"}), 400

        if hash_old_pwd == hash_new_pwd: #old and new password are equal
            return jsonify({"error": "new password must not be the same as old password"}), 400

        #user exists, old password is correct, and new password is unique -> change password
        user.hashed_password = hash_pwd(newPassword, user.salt)
        session.commit()
        return jsonify({"message": "password updated successfully"}), 200
    except:
        return jsonify({"error": "error interacting with the db"}), 400
    finally:
        session.close()

@app.route('/delete-user', methods=['DELETE'])
def delete_user():
    """
    deletes the account/user after verifying the username and password is correct

    expected JSON input:
        - username (str): the username of the account/user
        - password (str): the password of the account/user
    
    returns:
        JSON response indicating the status of the deletion or errors with inputs
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    session = Session()
    try:
        user = session.query(User).filter_by(username=username).first()

        if user == None: #user doesnt exist
            return jsonify({"error": "username does not exist"}), 400
        
        if hash_pwd(password, user.salt) != user.hashed_password: #password does not match password in db
            return jsonify({"error": "incorrect password"}), 400

        #user exists and password is correct -> delete user
        user = session.query(User).filter_by(username=username).delete()
        session.commit()
        return jsonify({"message": "user successfully deleted"}), 200
    except:
        return jsonify({"error": "error interacting with the db"}), 400
    finally:
        session.close()

##########################################
# requirement: functionality 
##########################################

@app.route('/api-check', methods=['GET'])
def api_check():
    """
    health check route to verify the api is running

    returns:
        JSON response indicating that the api is running
    """
    logging.info("API HEALTH GETTING CHECKED")
    return jsonify({"message": "api is running!"}), 200

@app.route('/db-check', methods=['GET'])
def db_check():
    """
    health check route to verify that the database is connected

    returns:
        JSON response indicating the status of the database
    """
    try:
        connection = sqlite3.connect(DATABASE_URL)
        return jsonify({"message": "db is connected!"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": f'{e}'}), 500


@app.route('/clear-favorite/<int:position>', methods=['PUT'])
def clear_favorite(position = int):
    """
    clears a specified favorite brew position for a user

    path parameter
        - position (int) : the position # of the favorite brew column of the user
            that will get reset

    expected JSON input:
        - username (str) : the username in the database who will have its favorite brewery removed

    returns:
        JSON response idicating a successful clearing of the favorite or errors with input/parameter
    """
    if not (1 <= position <= 5) :
        return jsonify({"error": "position must be within [1,5]"}), 500

    data = request.json
    username = data.get('username')
    if not username:
        return jsonify({"error": "username is required."}), 400

    session = Session()
    try:
        user = session.query(User).filter_by(username=username).first()
        
        match position:
            case 1:
                user.favorite_brew_1 = None
            case 2:
                user.favorite_brew_2 = None
            case 3:
                user.favorite_brew_3 = None
            case 4:
                user.favorite_brew_4 = None
            case 5:
                user.favorite_brew_5 = None
        session.commit()
        return jsonify({"message": f'successfully cleared favorite brewery {position}'}), 200
    except:
        return jsonify({"error": "error interacting with the db"}), 400
    finally:
        session.close()

@app.route('/get-brewery/<id>', methods=['GET'])
def get_brewery(id: str):
    """
    gets the details of a specific brewery by its id

    path parameter
        - id (string): the id of the brewery

    returns:
        JSON response of the details of the brewery (if valid id) or errors with input/parameter
    """
    try:
        response = requests.get(f'https://api.openbrewerydb.org/v1/breweries/{id}').json()
        if "message" in response: #invalid id
            return jsonify({"error": f'{id}, invalid id'}), 400
        memory.add(response)
        return response, 200
    except:
        return jsonify({"error": "error getting brewery from API"})

@app.route('/add-favorite/<int:position>', methods=['PUT'])
def add_favorite(position: int):
    """
    adds the most recent singular brewery from memory at a position for the user in the database

    path parameter:
        - position (int) : the position # of the favorite brew column that will be updated

    expected JSON input:
        - username (str) : the username in the database who will have a favorite brewery added/updated 

    returns:
        JSON response idicating a successful adding of the brewery to the favorite or errors with input/parameter
    """
    if not (1 <= position <= 5) :
        return jsonify({"error": "position must be within [1,5] inclusive"}), 500

    brewery = memory.getRecent()
    if brewery == None:
        return jsonify({"error": "there is no singular brewery in memory"})

    data = request.json
    username = data.get('username')
    if not username:
        return jsonify({"error": "username is required."}), 400

    session = Session()
    try:
        user = session.query(User).filter_by(username=username).first()

        match position:
            case 1:
                user.favorite_brew_1 = brewery
            case 2:
                user.favorite_brew_2 = brewery
            case 3:
                user.favorite_brew_3 = brewery
            case 4:
                user.favorite_brew_4 = brewery
            case 5:
                user.favorite_brew_5 = brewery
        session.commit()
        return jsonify({"message": f'successfully updated favorite brewery {position}'}), 200
    except:
        return jsonify({"error": "error interacting with the db"}), 400
    finally:
        session.close()

@app.route('/list-breweries', methods=['GET'])
def list_breweries():
    """"
    gets a list of breweries according to a variety of queries
    
    queries:
        - see https://www.openbrewerydb.org/documentation#list-breweries for information

    returns:
        JSON response containing a list of breweries according to the queries
    """
    queries = {
        "by_city" : request.args.get('by_city'),
        "by_country" : request.args.get('by_country'),
        "by_dist" : request.args.get('by_dist'),
        "by_ids" : request.args.get('by_ids'),
        "by_name" : request.args.get('by_name'),
        "by_state" : request.args.get('by_state'),
        "by_postal" : request.args.get('by_postal'),
        "by_type" : request.args.get('by_type'),
        "page" : request.args.get('page'),
        "per_page" : request.args.get('per_page'),
        "sort" : request.args.get('sort')
    }

    query_string = "?"
    for key in queries:
        if queries[key] != None:
            query_string += f'{key}={queries[key]}&'
    
    try:
        response = requests.get(f'https://api.openbrewerydb.org/v1/breweries{query_string}').json()
        memory.add(response)
        return response, 200
    except:
        return jsonify({"error": "error getting a list of breweries from API"})

@app.route('/view-favorites', methods=['GET'])
def view_favorites():
    """
    gets the users favorite breweries

    expected JSON input:
        - username (str) : the user in the database whos favorite breweries will be returned

    returns:
        JSON response containing the users favorite breweries or errors with parameters
    """
    data = request.json
    username = data.get('username')
    if not username:
        return jsonify({"error": "username required"}), 400
    
    session = Session()
    try:
        user = session.query(User).filter_by(username=username).first()
        
        user_dict = vars(user)
        favorite_brews_dict = {}

        for key in user_dict:
            if "favorite_brew" in key:
                favorite_brews_dict[key] = user_dict[key]
        
        return jsonify({user.username: favorite_brews_dict}), 200
    except:
        return jsonify({"error": "error interacting or traversing with the db"}), 400
    finally:
        session.close()

@app.route('/get-random', methods=['GET'])
def get_random():
    """
    gets a completely random brewery

    returns:
        JSON response that contains the details of a random brewery or an error with the API
    """
    try:
        response = requests.get("https://api.openbrewerydb.org/v1/breweries/random").json()
        # response = response.json()
        memory.add(response)
        return response, 200
    except:
        return jsonify({"error": "unable to get random brewery from API"})

@app.route('/view-memory', methods=['GET'])
def view_memory():
    """
    returns:
        JSON response that shows the memory (most recent api calls)
    """
    return jsonify({"memory": memory.stringRep()})



if __name__ == '__main__':
    app.run(debug=True)