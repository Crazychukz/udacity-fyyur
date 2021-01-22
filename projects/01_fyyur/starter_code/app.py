# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from flask_migrate import Migrate
from sqlalchemy.orm import load_only
from sqlalchemy import func
import datetime

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

# TODO: connect to a local postgresql database
migrate = Migrate(app, db)
now = datetime.datetime.now()


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(500), nullable=True)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean, default=False, nullable=True)
    seeking_description = db.Column(db.String(), nullable=True)
    shows = db.relationship('Show', backref='venue_shows', cascade="all,delete", lazy=True)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(500))
    seeking_venue = db.Column(db.Boolean, default=False, nullable=True)
    seeking_description = db.Column(db.String(), nullable=True)
    shows = db.relationship('Show', backref='artist_shows', cascade="all,delete", lazy=True)
    calender = db.relationship('ArtistCalender', backref='artist_calender', cascade="all,delete", lazy=True)


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    start_time = db.Column(db.Time, nullable=True)
    start_date = db.Column(db.Date, nullable=True)


class ArtistCalender(db.Model):
    __tablename__ = 'calender'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    date = db.Column(db.Date, nullable=True)


# ----------------------------------------------------------------------------#
# Filters.DateTime
# ----------------------------------------------------------------------------#


# updated datetime filter to fit model field
def format_datetime(date, time, format='medium'):
    obj = str(date) + ' ' + str(time)
    date = dateutil.parser.parse(obj)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    elif format == 'small':
        format = "EE MM, dd, y"

    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route('/')
def index():
    new_artists = Artist.query.order_by(Artist.id.desc()).limit(10).all()
    new_venues = Venue.query.order_by(Venue.id.desc()).limit(10).all()
    return render_template('pages/home.html', new_artists=new_artists, new_venues=new_venues)


# ----------------------------------------------------------------------------#
#  Venues
# ----------------------------------------------------------------------------#

@app.route('/venues')
def venues():
    states_city = db.session.query(Venue).options(load_only("city", "state")).all()
    data = []
    for i in states_city:
        obj = {
            "city": i.city,
            "state": i.state,
            "venues": []
        }
        if obj not in data:
            data.append(obj)
    for k in data:
        k['venues'] = Venue.query.filter_by(state=k['state'], city=k['city']).all()

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    res = db.session.query(Venue).filter(func.lower(Venue.name).contains(search_term.lower()))
    response = {
        "count": res.count(),
        "data": res
    }
    return render_template('pages/search_venues.html', results=response, search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = Venue.query.get(venue_id)
    data.past_shows = Show.query.filter_by(venue_id=venue_id).filter(Show.start_date <= now.date()).order_by(
        Show.start_date).all()
    data.past_shows_count = len(data.past_shows)
    data.upcoming_shows = Show.query.filter_by(venue_id=venue_id).filter(Show.start_date >= now.date()).order_by(
        Show.start_date).all()
    data.upcoming_shows_count = len(data.upcoming_shows)
    for i in data.past_shows:
        i.artist_name = Artist.query.get(i.artist_id).name
        i.artist_image_link = Artist.query.get(i.artist_id).image_link

    for k in data.upcoming_shows:
        k.artist_name = Artist.query.get(k.artist_id).name
        k.artist_image_link = Artist.query.get(k.artist_id).image_link
    data.genres = data.genres.split(",")
    return render_template('pages/show_venue.html', venue=data)


# ----------------------------------------------------------------------------#
#  Create Venue
# ----------------------------------------------------------------------------#


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    try:
        name = request.form.get('name', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        genres = request.form.getlist('genres')
        image_link = request.form.get('image_link', '')
        facebook_link = request.form.get('facebook_link', '')
        new_venue = Venue(
            name=name,
            city=city,
            state=state,
            phone=phone,
            genres=",".join(genres),
            address=address,
            image_link=image_link,
            facebook_link=facebook_link
        )
        db.session.add(new_venue)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except:
        flash('An error occurred. Venue could not be listed.')
        db.session.rollback()
    finally:
        db.session.close()
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        Venue.query.filter_by(id=venue_id).delete()
        db.session.commit()
        flash('Venue deleted!')
    except:
        db.session.rollback()
    finally:
        db.session.close()
    return jsonify({'success': True})


# ----------------------------------------------------------------------------#
#  Artists
# ----------------------------------------------------------------------------#


@app.route('/artists')
def artists():
    data = Artist.query.order_by('id').all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    res = db.session.query(Artist).filter(func.lower(Artist.name).contains(search_term.lower()))
    response = {
        "count": res.count(),
        "data": res
    }
    return render_template('pages/search_artists.html', results=response, search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.get(artist_id)
    artist.genres = artist.genres.split(',')
    artist.upcoming_shows = Show.query.filter_by(artist_id=artist_id).filter(Show.start_date >= now.date()).order_by(
        Show.start_date).all()
    artist.upcoming_shows_count = len(artist.upcoming_shows)
    artist.past_shows = Show.query.filter_by(artist_id=artist_id).filter(Show.start_date <= now.date()).order_by(
        Show.start_date).all()
    artist.past_shows_count = len(artist.past_shows)
    for v in artist.upcoming_shows:
        v.venue_image_link = Venue.query.get(v.venue_id).image_link
        v.venue_name = Venue.query.get(v.venue_id).name

    for i in artist.past_shows:
        i.venue_image_link = Venue.query.get(i.venue_id).image_link
        i.venue_name = Venue.query.get(i.venue_id).name

    return render_template('pages/show_artist.html', artist=artist)


# ----------------------------------------------------------------------------#
#  Update
# ----------------------------------------------------------------------------#


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    form = ArtistForm(obj=artist)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    try:
        name = request.form.get('name', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        phone = request.form.get('phone', '')
        genres = request.form.getlist('genres')
        image_link = request.form.get('image_link', '')
        facebook_link = request.form.get('facebook_link', '')
        website = request.form.get('website', '')
        seeking_venue = request.form.get('seeking_venue', '')
        seeking_description = request.form.get('seeking_description', '')
        artist = Artist.query.get(artist_id)
        artist.name = name
        artist.city = city
        artist.state = state
        artist.genres = ','.join(genres)
        artist.image_link = image_link
        artist.facebook_link = facebook_link
        artist.phone = phone
        artist.website = website
        artist.seeking_description = seeking_description
        artist.seeking_venue = eval(seeking_venue)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully updated!')
    except:
        flash('An error occurred. Artist could not be updated.')
        db.session.rollback()
    finally:
        db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/artists/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    try:
        Artist.query.filter_by(id=artist_id).delete()
        db.session.commit()
        flash('Artist was successfully deleted!')
    except:
        db.session.rollback()
        flash('Unable was delete artist!')
    finally:
        db.session.close()
    return jsonify({'success': True})


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    form = VenueForm(obj=venue)
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        name = request.form.get('name', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        address = request.form.get('address', '')
        phone = request.form.get('phone', '')
        image_link = request.form.get('image_link', '')
        facebook_link = request.form.get('facebook_link', '')
        website = request.form.get('website', '')
        genres = request.form.getlist('genres')
        seeking_talent = request.form.get('seeking_talent', '')
        seeking_description = request.form.get('seeking_description', '')
        venue.name = name
        venue.city = city
        venue.state = state
        venue.address = address
        venue.phone = phone
        venue.genres = ",".join(genres)
        venue.image_link = image_link
        venue.facebook_link = facebook_link
        venue.website = website
        venue.seeking_description = seeking_description
        venue.seeking_talent = eval(seeking_talent)
        db.session.commit()
        flash('Venue ' + request.form['name'] + ' was successfully updated!')
    except:
        flash('An error occurred. Venue could not be updated.')
        db.session.rollback()
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))


#  ----------------------------------------------------------------#
#  Create Artist
#  ----------------------------------------------------------------#


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    try:
        name = request.form.get('name', '')
        city = request.form.get('city', '')
        state = request.form.get('state', '')
        phone = request.form.get('phone', '')
        genres = request.form.getlist('genres')
        image_link = request.form.get('image_link', '')
        facebook_link = request.form.get('facebook_link', '')
        new_artist = Artist(
            name=name,
            city=city,
            state=state,
            phone=phone,
            genres=",".join(genres),
            image_link=image_link,
            facebook_link=facebook_link
        )
        db.session.add(new_artist)
        db.session.commit()
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except:
        flash('An error occurred. Artist could not be listed.')
        db.session.rollback()
    finally:
        db.session.close()

    return render_template('pages/home.html')


# ----------------------------------------------------------------------------#
#  Shows
# ----------------------------------------------------------------------------#

@app.route('/shows')
def shows():
    data = Show.query.order_by(Show.start_date).all()
    for i in data:
        i.artist_name = Artist.query.get(i.artist_id).name
        i.artist_image_link = Artist.query.get(i.artist_id).image_link
        i.venue_name = Venue.query.get(i.venue_id).name
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    not_available = False
    try:
        venue_id = request.form.get('venue_id', '')
        artist_id = request.form.get('artist_id', '')
        start_date = request.form.get('start_date', '')
        start_time = request.form.get('start_time', '')
        # We check if an artist has dates in their calender, then check is the artist is available on the selected
        # show date

        # We assume any artist with an empty calender is available on all dates

        artist_cal = ArtistCalender.query.filter_by(artist_id=artist_id).all()
        artist_cal_2 = ArtistCalender.query.filter_by(date=start_date, artist_id=artist_id).all()
        if len(artist_cal) == 0 or len(artist_cal) > 0 and len(artist_cal_2) > 0:
            new_show = Show(
                venue_id=venue_id,
                artist_id=artist_id,
                start_time=start_time,
                start_date=start_date
            )
            db.session.add(new_show)
            db.session.commit()
            flash('Show was successfully listed!')
        else:
            not_available = True

    except:
        flash('Show not successfully listed!')
        db.session.rollback()
    finally:
        db.session.close()
    if not_available:
        flash('Artist is not available on the selected date!')
        form = ShowForm()
        return render_template('forms/new_show.html', form=form)
    else:
        return render_template('pages/home.html')


# ----------------------------------------------------------------------------#
# Calender ( Create and Show Artist Availability )
# ----------------------------------------------------------------------------#


@app.route('/artists/<int:artist_id>/calender')
def show_calender(artist_id):
    # Returns dates an artist is available for booking and also provision to add new dates
    artist = Artist.query.get(artist_id)
    calender = ArtistCalender.query.filter_by(artist_id=artist_id).all()
    return render_template('forms/artist_calender.html', artist=artist, calender=calender)


@app.route('/create_calender', methods=['POST'])
def create_artist_calender():
    # Adds new date to an Artist's calender
    try:
        artist_id = request.get_json()['artist_id']
        dates = request.get_json()['dates']
        for i in dates:
            date_obj = datetime.datetime.strptime(i, '%Y-%m-%dT%H:%M:%S.000Z').date() + datetime.timedelta(days=1)
            artist_cal = ArtistCalender.query.filter_by(date=date_obj, artist_id=artist_id).all()
            if len(artist_cal) == 0:
                new_date = ArtistCalender(
                    artist_id=artist_id,
                    date=date_obj
                )
                db.session.add(new_date)

        db.session.commit()
        flash('Calender data was successfully listed!')
    except:
        flash('An error occurred')
        db.session.rollback()
    finally:
        db.session.close()

    return jsonify({'message': 'Calender Added'})


@app.route('/del_calender/<cal_id>', methods=['DELETE'])
def del_calender(cal_id):
    try:
        ArtistCalender.query.filter_by(id=cal_id).delete()
        db.session.commit()
    except:
        db.session.rollback()
    finally:
        db.session.close()
    return jsonify({'success': True})


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
