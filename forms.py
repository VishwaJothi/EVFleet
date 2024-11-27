# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), EqualTo('confirm_password', message='Passwords must match.')])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('fleet_manager', 'Fleet Manager'), ('driver', 'Driver')], validators=[DataRequired()])
    submit = SubmitField('Create Account')
