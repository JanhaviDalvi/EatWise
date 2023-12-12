from flask import Flask, render_template, redirect, flash, url_for, request
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from bson import ObjectId
from bson import ObjectId
import config
from forms import RegistrationForm, LoginForm
from word2vec_rec import get_recs
from ingredient_parser import ingredient_parser
from ingredient_translator import trans


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


@app.route('/view_favourite')
@login_required
def view_favourite():    
	author_id = current_user.get_id()
	favorite_recipes = db.favourite.find({'author_id': ObjectId(author_id)})
	
	# Pass the fetched recipes to the template for rendering
	return render_template('view_favourite.html', favorite_recipes=favorite_recipes)

@app.route('/add_to_list')
@login_required
def add_to_list():    
	author_id = current_user.get_id()
	recipe_name = request.args.get('recipe')
	score = request.args.get('score')
	ingredients = request.args.get('ingredients')
	url = request.args.get('url')
	ingredients_list = ingredients.split(',')
	parsed_ingredients = ingredient_parser(ingredients_list)
	
	# Check if the entry already exists for the author_id, recipe_name, and parsed_ingredients
	existing_entry = db.list.find_one({
		'author_id': ObjectId(author_id),
		'recipe_name': recipe_name,
		'ingredients_list': parsed_ingredients,
		'url': url
	})

	if existing_entry:
		flash("Ingredients already added!", "warning")
	else:
		new_entry = {
			'recipe_name': recipe_name,
			'ingredients_list': parsed_ingredients,
			'url': url,
			'author_id': ObjectId(author_id)
		}
		db.list.insert_one(new_entry)
		flash("Ingredients have been saved in shopping list.", "success")
	return redirect(url_for("recipe_details", recipe=recipe_name, ingredients=ingredients, score=score, url=url))

@app.route('/add_to_fav')
@login_required
def add_to_fav():    
	author_id = current_user.get_id()
	recipe_name = request.args.get('recipe')
	ingredients = request.args.get('ingredients')
	score = request.args.get('score')
	url = request.args.get('url')

	# Check if the recipe already exists for the author_id
	existing_recipe = db.favourite.find_one({
		'author_id': ObjectId(author_id),
		'recipe_name': recipe_name,
		'ingredients': ingredients,
		'score': score,
		'url': url
	})

	if existing_recipe:
		flash("Recipe already exists in favorites!", "warning")
	else:
		new_entry = {
			'recipe_name': recipe_name,
			'ingredients': ingredients,
			'score': score,
			'url': url,
			'author_id': ObjectId(author_id)
		}
		db.favourite.insert_one(new_entry)
		flash("Recipe has been added to favorites!", "success")

	# Redirect back to the recipe details page
	return redirect(url_for("recipe_details", recipe=recipe_name, ingredients=ingredients, score=score, url=url))


@app.route("/search", methods=['GET', 'POST'])
@login_required
def search():
	if request.method == 'POST':
		searchbar_data = request.form.get('search_bar')
		number_results = int(request.form.get('numberOfResults'))
		translated_ingredients = trans(searchbar_data)
		result_df = get_recs(translated_ingredients, number_results)
		result_dict = result_df.to_dict()
		print(result_dict)
		return render_template('search.html', recipe=result_dict['recipe'], ingredients=result_dict['ingredients'], score=result_dict['score'], url=result_dict['url'], searchbar_ingredients=translated_ingredients)

	return render_template('search.html')


@app.route("/shopping_list", methods=['GET', 'POST'])
@login_required
def shopping_list():
	author_id = current_user.get_id()
	shopping_lists = db.list.find({'author_id': ObjectId(author_id)})
	return render_template('shopping_list.html', shopping_lists=shopping_lists)


@app.route("/edit_shopping_list/<list_id>", methods=['GET', 'POST'])
@login_required
def edit_shopping_list(list_id):
	# Convert the list_id to ObjectId type
	list_id_object = ObjectId(list_id)
	# Fetch the shopping list based on the list_id
	shopping_list = db.list.find_one({'_id': list_id_object})
	recipe_name = shopping_list.get('recipe_name')
	ingredients_list = shopping_list.get('ingredients_list')
	ingredients_string = ', '.join(ingredients_list)
	return render_template('custom_list.html', recipe_name=recipe_name, ingredients_string=ingredients_string)


@app.route("/custom_list", methods=['GET', 'POST'])
@login_required
def custom_list():
	author_id = current_user.get_id()
	if request.method == 'POST':
		list_name = request.form.get('listName')
		ingredients = request.form.get('ingredients')
		ingredients_list = ingredients.split(", ")
		print(list_name, ingredients_list)
		# Check if the entry already exists for the author_id, recipe_name, and parsed_ingredients
		existing_entry = db.list.find_one({
			'author_id': ObjectId(author_id),
			'recipe_name': list_name,
			'ingredients_list': ingredients_list,
		})

		if existing_entry:
			flash("List already added!", "warning")
		else:
			new_entry = {
				'recipe_name': list_name,
				'ingredients_list': ingredients_list,
				'author_id': ObjectId(author_id)
			}
			db.list.insert_one(new_entry)
			flash("New list have been created", "success")
			return redirect(url_for(shopping_list))
	return render_template('custom_list.html')

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