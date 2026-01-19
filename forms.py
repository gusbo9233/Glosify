from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, ValidationError

from models.user import User


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                "User already exists"
            )


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


class QuizForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=1, max=100)], render_kw={"placeholder": "Quiz Name"})
    submit = SubmitField("Create Quiz")


class TextImportForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=1, max=100)], render_kw={"placeholder": "Quiz Name"})
    language = StringField(validators=[InputRequired(), Length(min=1, max=50)], render_kw={"placeholder": "Language (e.g., Ukrainian, Polish)"})
    content = TextAreaField(validators=[InputRequired()], render_kw={"placeholder": "Paste any text here - song lyrics, word lists, textbook excerpts, articles...", "rows": 15})
    context = TextAreaField(validators=[], render_kw={"placeholder": "Optional: Additional context to help with accurate translations...", "rows": 3})
    submit = SubmitField("Create Quiz")


# Keep old form name for backward compatibility
SongQuizForm = TextImportForm


class WordForm(FlaskForm):
    lemma = StringField(validators=[Length(min=0, max=200)], render_kw={"placeholder": "Word (lemma) - optional"})
    translation = StringField(validators=[Length(min=0, max=200)], render_kw={"placeholder": "Translation - optional"})
    submit = SubmitField("Add Word")

    def validate(self, extra_validators=None):
        """Ensure at least one of lemma or translation is provided."""
        if not super().validate(extra_validators):
            return False

        if not self.lemma.data.strip() and not self.translation.data.strip():
            self.lemma.errors.append("At least one of lemma or translation must be provided.")
            return False

        return True


class VariantForm(FlaskForm):
    value = StringField(validators=[InputRequired(), Length(min=1, max=200)], render_kw={"placeholder": "Variant form"})
    translation = StringField(validators=[InputRequired(), Length(min=1, max=200)],
                              render_kw={"placeholder": "Translation"})
    tags = StringField(render_kw={"placeholder": "Tags (e.g., case=gen,number=sg)"})
    submit = SubmitField("Add Variant")
