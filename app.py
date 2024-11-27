from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import random
import pickle
import pandas as pd
import numpy as np 
import os
import requests
from dotenv import load_dotenv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users1.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load the pre-trained model
model = pickle.load(open('evmod', 'rb'))

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(150), nullable=True)
    otp = db.Column(db.Integer, nullable=True)
    
# Function to export data to CSV
def export_users_to_csv():
    # Query all users from the User table
    users = User.query.all()
    
    # Convert the query results into a list of dictionaries
    user_data = []
    for user in users:
        user_data.append({
            'id': user.id,
            'email': user.email,
            'password': user.password,
            'role': user.role,
            'username': user.username,
            'otp': user.otp
        })
    
    # Create a DataFrame from the list of dictionaries
    df = pd.DataFrame(user_data)
    print(df)

    # Write the DataFrame to a CSV file
    df.to_csv('users1.csv', index=False)
    print("Data exported successfully to 'users_data.csv'.")

# Registration form
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('fleet_manager', 'Fleet Manager'), ('driver', 'Driver')], validators=[DataRequired()])
    submit = SubmitField('Register')

# Login form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Password reset request form
class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send OTP')

# Reset password form
class ResetPasswordForm(FlaskForm):
    otp = IntegerField('OTP', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Reset Password')

# Load environment variables from .env file
load_dotenv()

# Function to send email using Sendinblue
def send_email(to_email, subject, content):
    url = "https://api.sendinblue.com/v3/smtp/email"
    
    # Retrieve the Sendinblue API key from environment variable
    api_key = os.getenv("SENDINBLUE_API_KEY")
    
    # If the API key is not found, raise an error
    if not api_key:
        raise ValueError("Sendinblue API key not found in environment variables.")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key  # Use the API key from environment variables
    }

    data = {
        "sender": {"email": "sahanats4@gmail.com"},  # Replace with your sender email
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": content
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # Generate a new OTP
            otp = random.randint(100000, 999999)
            user.otp = otp  # Update with the new OTP
            db.session.commit()

            # Send OTP to user's email
            send_email(user.email, 'Your OTP Code', f'Your OTP code is: {otp}')

            flash('OTP sent to your email.', 'success')
            return redirect(url_for('reset_password', email=user.email))
        else:
            flash('Email not found.', 'danger')

    return render_template('forgot_password.html', form=form)


@app.route('/reset_password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    form = ResetPasswordForm()  # Create a form for new password input
    user = User.query.filter_by(email=email).first()

    if form.validate_on_submit():
        if user.otp == int(form.otp.data):  # Check OTP
            user.password = generate_password_hash(form.new_password.data)
            user.otp = None  # Clear OTP
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP.', 'danger')

    return render_template('reset_password.html', form=form)

@login_manager.user_loader
def load_user(user_id):
    from flask_sqlalchemy import SQLAlchemy

    # Assuming db is the SQLAlchemy instance
    session = db.session
    return session.get(User, int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        # Check if the email already exists
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email address already exists. Please choose a different one.', 'danger')
            return render_template('register.html', form=form)

        # Check if passwords match
        if form.password.data != form.confirm_password.data:
            flash('Passwords do not match. Please try again.', 'danger')
            form.password.data = ''  # Clear password field
            form.confirm_password.data = ''  # Clear confirm password field
            return render_template('register.html', form=form)

        # Create new user with hashed password and username
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(email=form.email.data, password=hashed_password, role=form.role.data, username=form.username.data)
        db.session.add(new_user)
        db.session.commit()
        
        # Immediately update CSV after adding the new user
        export_users_to_csv()  # This will update the 'users.csv' file
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            if user.role == 'fleet_manager':
                return redirect(url_for('fleet_manager_page'))
            elif user.role == 'driver':
                return redirect(url_for('driver_page'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/fleet_manager_page', methods=['GET', 'POST'])
@login_required
def fleet_manager_page():
    try:
        # Read the CSV file containing vehicle data
        vehicle_data = pd.read_csv('merged_updated.csv')  # Path to your CSV
    except FileNotFoundError:
        vehicle_data = None  # Handle file not found error
        flash('Vehicle data CSV not found.', 'danger')

    if vehicle_data is not None:
        # Ensure all datetime columns are serialized to string (e.g., ISO format)
        for column in vehicle_data.select_dtypes(include=['datetime']).columns:
            vehicle_data[column] = vehicle_data[column].dt.isoformat()

        # 1. Find the index of the last day for each driver (dvr)
        vehicle_data['Date'] = pd.to_datetime(vehicle_data['Date'])  # Ensure the 'Date' column is in datetime format
        last_day_indices = vehicle_data.loc[vehicle_data.groupby(['dvr'])['Date'].idxmax()]

        # Reset the index for the last day data
        status_dvr_last_date = last_day_indices.reset_index(drop=True)
        
        # Group by Driver and Find the Maximum Speed for Each Driver
        max_speed_by_driver = vehicle_data.groupby('dvr')['Speed (km/h)'].max().reset_index()

        # Filter for Overspeeding Drivers (Speed > 100 km/h)
        overspeeding_drivers = max_speed_by_driver[max_speed_by_driver['Speed (km/h)'] > 100]

        # Prepare the overspeeding driver data (Driver Name and Max Speed)
        overspeeding_driver_info = overspeeding_drivers[['dvr', 'Speed (km/h)']].to_dict(orient='records')

        # 2. Calculate the status counts for "Working Condition" and "Charging Status" from the filtered data
        status_counts_working = status_dvr_last_date['Working Condition'].value_counts().to_dict()
        status_counts_charging = status_dvr_last_date['Charging Status'].value_counts().to_dict()

        # 3. Prepare the data for Maintenance Cost by Manufacturer
        maintenance_by_manufacturer = vehicle_data.groupby('Make')['Maintenance Cost ($)'].sum().to_dict()

        # 4. Prepare the data for Maintenance Cost by Month
        vehicle_data['Month'] = vehicle_data['Date'].dt.to_period('M')  # Extract month and year
        vehicle_data['Month'] = vehicle_data['Month'].astype(str)  # Convert Period to string

        maintenance_by_month = vehicle_data.groupby('Month')['Maintenance Cost ($)'].sum().to_dict()

        # 5. Prepare other data to be passed to the template
        # Here, we create the vehicle_models dictionary to store the model counts
        vehicle_models = vehicle_data['Make'].value_counts().to_dict()  # This stores the count of each vehicle model

        # Model data - For each model, gather its vehicle data in a dictionary format (for last day's data)
        model_data = {make: vehicle_data[vehicle_data['Make'] == make].to_dict(orient='records') for make in vehicle_data['Make'].unique()}

        # Prediction Section (Car Range Prediction)
        prediction_text = None

    try:
        # Read the CSV file containing vehicle data
        vehicle_data = pd.read_csv('merged_updated.csv')  # Path to your CSV
    except FileNotFoundError:
        vehicle_data = None  # Handle file not found error
        flash('Vehicle data CSV not found.', 'danger')

    # Initialize data for the templates (like maintenance stats, models, etc.)
    prediction_text = None

    if vehicle_data is not None:
        # Ensure all datetime columns are serialized to string (e.g., ISO format)
        for column in vehicle_data.select_dtypes(include=['datetime']).columns:
            vehicle_data[column] = vehicle_data[column].dt.isoformat()
        
        # Check if the form is submitted via POST
        if request.method == 'POST':
            try:
                # Get car model and battery level from the form
                car_model = int(request.form['carModel'])
                battery_level = int(request.form['batteryLevel'])

                # Define the feature sets for each car model
                Tesla1 = [4.4,233,485,366,493,82,4694,1849,1443,2875,2232,388,561,0,0,1,0,0,1,0,0]
                Tesla2 = [3.3,261,460,377,660,82,4694,1849,1443,2875,2232,388,561,0,0,0,1,0,1,0,0]
                BMW = [5.7,190,470,250,430,83.9,4783,1852,1448,2856,2605,555,470,1,0,0,0,0,0,0,1]
                Volkswagen = [7.9,160,450,150,310,82,4261,1809,1568,2771,2300,447,385,0,0,0,0,1,0,0,1]
                Polestar = [7.4,160,425,170,330,78,4607,1800,1479,2735,2490,496,405,0,1,0,0,0,0,1,0]

                # Choose the feature set based on the selected car model
                if car_model == 1:
                    features = Tesla1
                elif car_model == 2:
                    features = Tesla2
                elif car_model == 3:
                    features = BMW
                elif car_model == 4:
                    features = Volkswagen
                elif car_model == 5:
                    features = Polestar
                else:
                    prediction_text = "Invalid car model selected."
                    return jsonify({'prediction_text': prediction_text})

                # Insert the battery level at the beginning of the feature set (index 0)
                features.insert(0, battery_level)

                # Prepare the final feature vector for prediction
                final_features = [np.array(features)]
                
                # Log or print the features before prediction
                print(f"Features being passed to the model: {final_features}")
                
                # Predict the range using the model
                prediction = model.predict(final_features)

                # Convert prediction to an integer
                predicted_range = int(prediction[0])

                # Create the response JSON
                prediction_text = f"Estimated car range: {predicted_range} km"
                return jsonify({'prediction_text': prediction_text})

            except Exception as e:
                # Return error response if something goes wrong
                return jsonify({'prediction_text': f"Error: {str(e)}"})

        # If the request is a GET request, render the page with the vehicle data
        return render_template(
            'fleet_manager.html',
            username=current_user.username,
            vehicles=vehicle_data.to_dict(orient='records'),
            vehicle_models=vehicle_models,
            status_counts_working=status_counts_working,
            status_counts_charging=status_counts_charging,
            maintenance_by_manufacturer=maintenance_by_manufacturer,
            maintenance_by_month=maintenance_by_month,
            model_data=model_data,
            prediction_text=prediction_text,
            overspeeding_driver_info=overspeeding_driver_info
        )
    else:
        # If vehicle data is not available, render the page with empty data
        return render_template(
            'fleet_manager.html',
            username=current_user.username,
            vehicles=[],
            vehicle_models={},
            status_counts_working={},
            status_counts_charging={},
            maintenance_by_manufacturer={},
            maintenance_by_month={},
            model_data={},
            prediction_text=None,
            overspeeding_driver_info=[]
        )

@app.route('/driver_page', methods=['GET', 'POST'])
@login_required
def driver_page():
    # Fetch the notification from session if it exists
    driver_notification = session.get('driver_notification', None)
    
    # Clear the notification after it's been shown
    if driver_notification:
        session.pop('driver_notification', None)  # Clear the notification
        
    prediction_text = None
    if request.method == 'POST':
        try:
            # Get the form data (battery level and car model)
            car_model = int(request.form['carModel'])
            battery_level = int(request.form['batteryLevel'])
            
            # Define the feature sets for each car model
            Tesla1 = [4.4,233,485,366,493,82,4694,1849,1443,2875,2232,388,561,0,0,1,0,0,1,0,0]
            Tesla2 = [3.3,261,460,377,660,82,4694,1849,1443,2875,2232,388,561,0,0,0,1,0,1,0,0]
            BMW = [5.7,190,470,250,430,83.9,4783,1852,1448,2856,2605,555,470,1,0,0,0,0,0,0,1]
            Volkswagen = [7.9,160,450,150,310,82,4261,1809,1568,2771,2300,447,385,0,0,0,0,1,0,0,1]
            Polestar = [7.4,160,425,170,330,78,4607,1800,1479,2735,2490,496,405,0,1,0,0,0,0,1,0]

            # Choose the feature set based on the selected car model
            if car_model == 1:
                features = Tesla1
            elif car_model == 2:
                features = Tesla2
            elif car_model == 3:
                features = BMW
            elif car_model == 4:
                features = Volkswagen
            elif car_model == 5:
                features = Polestar
            else:
                prediction_text = "Invalid car model selected."
                return jsonify({'prediction_text': prediction_text})

            # Insert the battery level at the beginning of the feature set (index 0)
            features.insert(0, battery_level)

            # Prepare the final feature vector for prediction
            final_features = [np.array(features)]
            
            # Predict the range using the model
            prediction = model.predict(final_features)

            # Convert prediction to an integer
            predicted_range = int(prediction[0])

            # Create the response JSON
            prediction_text = f"Estimated car range: {predicted_range} km"
            return jsonify({'prediction_text': prediction_text})

        except Exception as e:
            # Return error response if something goes wrong
            return jsonify({'prediction_text': f"Error: {str(e)}"})

    return render_template(
        'driver.html',
        username=current_user.username,
        overspeeding_message=driver_notification,
        prediction_text=prediction_text
    )


        
@app.route('/send_notification', methods=['POST'])
@login_required
def send_notification():
    data = request.get_json()
    driver_name = data.get('driver')
    
    # Store the notification message in the session
    session['driver_notification'] = f"Notification sent to {driver_name}: You have been flagged for overspeeding!"

    # Return a success response
    return jsonify({'success': True, 'message': 'Notification sent!'}), 200


@app.route('/')
def home():
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():  # Make sure the app context is available for database queries
        db.create_all()  # Create database tables
        # export_users_to_csv()  # Export users to CSV
app.run(debug=True)