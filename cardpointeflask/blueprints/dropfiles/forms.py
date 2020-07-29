from flask_wtf import FlaskForm
from wtforms import FileField


class DropForm(FlaskForm):
    file = FileField()
