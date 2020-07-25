from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired

class SongForm(FlaskForm):
    title = StringField('Title', [DataRequired()])
    artist = StringField('Artist', [DataRequired()])
