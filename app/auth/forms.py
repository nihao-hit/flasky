from flask_wtf import FlaskForm
from wtforms import StringField,PasswordField,BooleanField,SubmitField
from wtforms.validators import DataRequired,Length,Email,Regexp,EqualTo
from wtforms import ValidationError
from ..models import User

#实现注册时检查邮箱，用户名是否已被使用
class RegistrationForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),
                                            Email()])
    username = StringField('Username',validators=[DataRequired(),Length(1,64),
                            Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,
                            'Usernames must have only letters,numbers,dots or \
                            underscores')])
    password = PasswordField('Password',validators=[DataRequired(),
                            EqualTo('password2',message='Password must match.')])
    password2 = PasswordField('Confirm password',validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')
    
    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

#为什么不实现检查邮箱，密码是否正确
class LoginForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),
                                            Email()])
    password = PasswordField('Password',validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log in')


class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),
                                            Email()])
    submit = SubmitField('Reset Password')


class PasswordResetForm(FlaskForm):
    password = PasswordField('New password',validators=[DataRequired(),
                            EqualTo('password2',message='Passwords must match.')])
    password2 = PasswordField('Confirm password',validators=[DataRequired()])
    submit = SubmitField('Reset password')


class ChangeEmailForm(FlaskForm):
    email = StringField('New email',validators=[DataRequired(),Length(1,64),
                                                Email()])
    password = PasswordField('Password',validators=[DataRequired()])
    submit = SubmitField('Update email address')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

#为什么不实现检查用户，密码是否正确
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password',validators=[DataRequired()])
    password = PasswordField('New password',validators=[DataRequired(),
                            EqualTo('password2','Password must match.')])
    password2 = PasswordField('Confirm new password',validators=[DataRequired()])
    submit = SubmitField('Update Password')