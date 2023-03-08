from flask import Flask, render_template, redirect, url_for, request, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy.exc import IntegrityError
from wtforms import StringField, SubmitField, FloatField, IntegerField
from wtforms.validators import DataRequired, InputRequired, NumberRange
import requests

API_KEY = "Your Api Key"

moviedb_endpoint = "https://api.themoviedb.org/3/search/movie"
MOVIE_DB_INFO_URL = "https://api.themoviedb.org/3/movie"
MOVIE_DB_IMAGE_URL = "https://image.tmdb.org/t/p/w300_and_h450_bestv2"

# create the app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'Your secret Key'
Bootstrap(app)

# create the extension
db = SQLAlchemy()

# configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../new-Movies-collection.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize the app with the extension
db.init_app(app)


# Define Models
class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True)
    year = db.Column(db.String(250))
    description = db.Column(db.String(500))
    rating = db.Column(db.Float)
    ranking = db.Column(db.Integer)
    review = db.Column(db.String(250))
    img_url = db.Column(db.String(500))

    # Optional: this will allow each Movie object to be identified by its title when printed.
    def __repr__(self):
        return f'<Movie {self.title}>'


# Create db with all columns
with app.app_context():
    db.create_all()


class RateMovieForm(FlaskForm):
    your_rating = FloatField("Your Rating out of 10 e.g 7.5", validators=[InputRequired(message="Enter your rating!"),
                                                                          NumberRange(min=0, max=10,
                                                                                      message='Rating must be between '
                                                                                              '1 and 10')])
    your_review = StringField("Your Review", validators=[DataRequired(message="Missing review!")])
    # your_ranking = IntegerField(label="Enter your movie's ranking", validators=[DataRequired(message="Missing
    # ranking!"), NumberRange(min=1, max=100, message='Ranking must be between 1 and 100')])

    update = SubmitField("Done")


class AddMovieForm(FlaskForm):
    movie_title = StringField(label="Movie Title", validators=[DataRequired(message="Add a valid movie title")])
    add_movie = SubmitField(label="Add Movie")


@app.route("/")
def home():
    # Query the Movie table and order the results by rating in descending order
    all_movies = Movie.query.order_by(-Movie.rating).all()
    print(all_movies)
    for i, movie in enumerate(all_movies):
        movie.ranking = i + 1
    db.session.commit()
    return render_template("index.html", all_movies=all_movies, len=len)


# Update rating
@app.route("/edit/<int:movie_id>", methods=["GET", "POST"])
def update_rating(movie_id):
    form = RateMovieForm()
    movie = db.session.get(Movie, movie_id)
    print(movie)
    if form.validate_on_submit():
        movie.rating = form.your_rating.data
        movie.review = form.your_review.data
        db.session.commit()
        print(f"Movie {movie.title} Rating updated successfully!")

        flash(message=f"movie '{movie.title}' updated successfully!", category="success")
        return redirect(url_for("home"))
    else:
        form.your_rating.render_kw = {"placeholder": f"{movie.rating}"}
        form.your_review.render_kw = {"placeholder": f"{movie.review}"}

    return render_template("edit.html", movie=movie, form=form)


# Delete items
@app.route("/delete/id=<int:movie_id>")
def delete(movie_id):
    # Delete the movie with the specified id
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()

    # Query the remaining movies and update their ids
    movies = Movie.query.order_by(Movie.id).all()
    for i, movie in enumerate(movies, start=1):
        movie.id = i
        db.session.add(movie)
    db.session.commit()

    flash(message=f"{movie.title} deleted successfully!", category="success")
    return redirect(url_for("home"))


# Add items
@app.route("/add", methods=["GET", "POST"])
def add():
    form = AddMovieForm()
    if form.validate_on_submit():
        movie_params = {
            "api_key": API_KEY,
            "query": form.movie_title.data,
        }

        response = requests.get(url=moviedb_endpoint, params=movie_params)
        films = response.json()["results"]
        return render_template("select.html", films=films, len=len)

    return render_template("add.html", form=form)


@app.route("/find", methods=["GET", "POST"])
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        movie_api_url = f"{MOVIE_DB_INFO_URL}/{movie_api_id}"
        response = requests.get(movie_api_url, params={"api_key": API_KEY, "language": "en-US"})
        data = response.json()
        try:
            # Check if a movie with the same title and year already exists in the database
            existing_movie = Movie.query.filter_by(title=data["title"], year=data["release_date"].split("-")[0]).first()
            if existing_movie:
                flash(message=f"{existing_movie.title} already exists in the database!", category="warning")
                return redirect(url_for("home"))

            # If no movie with the same title and year exists, add it to the database
            new_movie = Movie(
                title=data["title"],
                year=data["release_date"].split("-")[0],
                img_url=f"{MOVIE_DB_IMAGE_URL}/{data['poster_path']}",
                description=data["overview"],
                rating=float(data["vote_average"]),
            )
            db.session.add(new_movie)
            db.session.commit()
            flash(message=f"{new_movie.title} added successfully!", category="success")
            return redirect(url_for("home"))
        except IntegrityError:
            db.session.rollback()
            flash(message="Error adding movie to database", category="danger")
            return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=True)
