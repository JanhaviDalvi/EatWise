from flask import Flask, render_template, redirect, flash, url_for, request
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from bson import ObjectId
from datetime import datetime
from bson import ObjectId
import config
from forms import RegistrationForm, LoginForm
from word2vec_rec import get_recs

mongodb_uri = config.MONGODB_URI
secret_key = config.SECRET_KEY

# app configurations
app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# MongoDB stuff
client = MongoClient(mongodb_uri)
db = client['recipe_db']


# User class that satisfies the requirements of Flask-Login. The User class should inherit from UserMixin, which provides default implementations for the required methods.
class User(UserMixin):
	def __init__(self, user_id, username, email):
		self.id = user_id
		self.username = username
		self.email = email

	# This method is required by Flask-Login's UserMixin class. It returns the string representation of the user's ID, which is used for user authentication and session management.
	def get_id(self):
		return str(self.id)

#  user loader function that Flask-Login will use to load the user from the database based on the user ID
@login_manager.user_loader
def load_user(user_id):
	# Query the database to find the user by ID
	user = db.user.find_one({'_id': ObjectId(user_id)})
	# Return the user object
	return User(user['_id'], user['username'], user['email'])


@app.route("/", methods=['GET', 'POST'])
@login_required
def home():
	return render_template('index.html')

@app.route('/recipe_details')
@login_required
def recipe_details():    
	recipe_name = request.args.get('recipe')
	ingredients = request.args.get('ingredients')
	score = request.args.get('score')
	url = request.args.get('url')
	return render_template('recipe_details.html', recipe_name=recipe_name, ingredients=ingredients, score=score, url=url)


@app.route('/add_to_fav')
@login_required
def add_to_fav():    
	author_id = current_user.get_id()
	new_entry = {
		'recipe_name': request.args.get('recipe'),
		'ingredients': request.args.get('ingredients'),
		'score': request.args.get('score'),
		'url': request.args.get('url'),
		'author_id': ObjectId(author_id)
	}
	print(new_entry)
	db.favourite.insert_one(new_entry)
	flash("Recipe has been added to favourite!", "success")
	return redirect(url_for("recipe_details", recipe=new_entry['recipe_name'], ingredients=new_entry['ingredients'], score=new_entry['score'], url=new_entry['url']))


@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
	if request.method == 'POST':
		searchbar_data = request.form.get('search_bar')
		number_results = int(request.form.get('numberOfResults'))
		print(number_results)
		result_df = get_recs(searchbar_data, number_results)
		result_dict = result_df.to_dict()
		print(result_dict)
		return render_template('search.html', recipe=result_dict['recipe'], ingredients=result_dict['ingredients'], score=result_dict['score'], url=result_dict['url'])

	return render_template('search.html')

@app.route("/register_user", methods=['GET', 'POST'])
def register():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	
	registration_form = RegistrationForm(db)  # Passing the database object to the form
	
	if registration_form.validate_on_submit():
		# Encrypting the password
		hashed_pw = bcrypt.generate_password_hash(registration_form.password.data).decode('utf-8')
		
		# Creating a new user entry
		new_user_entry = {
			'email': registration_form.email.data,
			'username': registration_form.username.data,
			'password': hashed_pw
		}
		new_user = db.user.insert_one(new_user_entry)  # Inserting into the 'user' collection
		new_user_id = new_user.inserted_id
		user_obj = User(new_user_id, new_user_entry['username'], new_user_entry['email'])
		login_user(user_obj)
		flash(f"Account has been created for '{registration_form.username.data}'!", "success")
		return redirect(url_for('home'))
	
	return render_template('register.html', form=registration_form)


@app.route("/login_user", methods=['GET', 'POST'])
def login():
	if current_user.is_authenticated:
		return redirect(url_for('home'))
	login_form = LoginForm()
	if login_form.validate_on_submit():
		user = db.user.find_one({'username': login_form.username.data})
		if user and bcrypt.check_password_hash(user['password'], login_form.password.data):
			# Create a User object from the retrieved data
			user_obj = User(user['_id'], user['username'], user['email'])
			login_user(user_obj, remember=login_form.remember.data)  # Login the user
			flash('You have been logged in!', 'success')
			return redirect(url_for('home'))
		else:
			flash('Login Failed. Please check username and password', 'danger')
	return render_template('login.html', form=login_form)

@app.route("/logout_user")
@login_required
def logout():
	logout_user()  
	flash('Logged out!', 'success')
	return redirect(url_for('login'))

if __name__ == '__main__':
	app.run(debug=True)