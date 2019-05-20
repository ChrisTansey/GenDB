from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, PasswordField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class AddProjectForm(FlaskForm):
    title = TextAreaField('Project Title', validators=[DataRequired(),
                                                       Length(max=100)])
    desc = TextAreaField('Project Description', validators=[Length(max=500)])
    submit = SubmitField('Add Project')


class SetupForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    full_name = StringField('Full Name', validators=[DataRequired()])
    submit = SubmitField('Register User')


class ChangePasswordForm(FlaskForm):
    current = PasswordField('Current Password', validators=[DataRequired()])
    new_1 = PasswordField('New Password', validators=[DataRequired()])
    new_2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('new_1')])
    submit = SubmitField('Change Password')


class UploadIndividualsForm(FlaskForm):
    file = FileField('Individuals File', validators=[FileRequired()])
    submit = SubmitField('Upload')
