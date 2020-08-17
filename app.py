#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, or_
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys
from datetime import date
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#
show = db.Table('Show',
    db.Column('venue_id', db.Integer, db.ForeignKey('Venue.id'), nullable=False),
    db.Column('artist_id', db.Integer, db.ForeignKey('Artist.id'), nullable=False),
    db.Column('start_time', db.DateTime, nullable=False),
    db.Column('id', db.Integer, primary_key=True)
)
class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120), unique=True)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, nullable=False, default=True)
    seeking_description = db.Column(db.String())
    website = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    artists = db.relationship('Artist', secondary=show,
      backref=db.backref('venues', lazy=True))


    def __reper__(self):
      return f'<id: {self.id}, description: {self.name}>'

    # TODO: implement any missing fields, as a database migration using Flask-Migrate

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120), unique=True)
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, nullable=False, default=True)
    seeking_description = db.Column(db.String)

    def __reper__(self):
      return f'<id: {self.id}, description: {self.name}>'

    # TODO: implement any missing fields, as a database migration using Flask-Migrate

# TODO Implement Show and Artist models, and complete all model relationships and properties, as a database migration.

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  data = []
  # get already inserted state/city in Venue
  places = Venue.query.with_entities(Venue.city, Venue.state).distinct().all()
  # loop to get each venue according to state/city
  # get num of upcoming shows is calculated for each revenue
  for place in places:
    num = db.session.query(func.count(show.c.id))\
      .filter(show.c.venue_id == Venue.id)\
      .filter(show.c.start_time >= date.today())\
      .label('num_upcoming_shows') 
    venues = db.session\
      .query(Venue.id, Venue.name, num)\
      .filter(Venue.state == place.state)\
      .filter(Venue.city == place.city)\
      .all()
    # build venues
    values=[]
    for venue in venues:
      values.append({'id': venue.id, 'name': venue.name, 'num_upcoming_shows': venue.num_upcoming_shows})

    # build final returned data using venues
    data.append({'city' : place.city, 'state' : place.state, "venues" : values})
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # using search term, search the venues in incase-sesitive

  # get venues count according to search
  venues_count = db.session.query(Venue.id)\
    .filter(Venue.name.ilike('%' + request.form.get('search_term') +'%')).count()
  # build venue row
  num = db.session.query(func.count(show.c.id))\
      .filter(show.c.venue_id == Venue.id)\
      .filter(show.c.start_time >= date.today())\
      .label('num_upcoming_shows')
  venues = db.session\
    .query(Venue.id, Venue.name, num)\
    .filter(Venue.name.ilike('%' + request.form.get('search_term') +'%'))\
    .all()
  venues_dict = []
  for venue in venues:
    venues_dict.append({
      "id": venue.id,
      "name": venue.name,
      "num_upcoming_shows": venue.num_upcoming_shows
    })
  response = {"count" : venues_count, "data" : venues_dict}
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # check if venue is existing, return its rows 
  # else redirect to home page with error message
  error = False
  try:
    venue = Venue.query.get(venue_id)
    upcoming_shows = db.session.query(Artist, db.cast(show.c.start_time, db.String).label('start_time'))\
      .join(show)\
      .filter(show.c.venue_id == venue_id)\
      .filter(show.c.start_time >= date.today())\
      .group_by(Artist.id).group_by(show.c.start_time)\
      .all()
    upcoming_shows_count = db.session.query(Artist)\
      .join(show)\
      .filter(show.c.venue_id == venue_id)\
      .filter(show.c.start_time >= date.today())\
      .count()
    past_shows = db.session.query(Artist, db.cast(show.c.start_time, db.String).label('start_time'))\
      .join(show)\
      .filter(show.c.venue_id == venue_id)\
      .filter(show.c.start_time < date.today())\
      .group_by(Artist.id).group_by(show.c.start_time)\
      .all()
    past_shows_count = db.session.query(Artist)\
      .join(show)\
      .filter(show.c.venue_id == venue_id)\
      .filter(show.c.start_time < date.today())\
      .count()
    upcoming_shows_dict = []
    for artist in upcoming_shows:
        upcoming_shows_dict.append({
        "artist_id": artist.Artist.id,
        "artist_name": artist.Artist.name,
        "artist_image_link": artist.Artist.image_link,
        "start_time": artist.start_time
      })
    past_shows_dict = []
    for artist in past_shows:
        past_shows_dict.append({
        "artist_id": artist.Artist.id,
        "artist_name": artist.Artist.name,
        "artist_image_link": artist.Artist.image_link,
        "start_time": artist.start_time
      })
    # build final returned data
    data = {
      "id": venue.id,
      "name": venue.name,
      "genres": venue.genres.replace('{','').replace('}','').replace('"','').split(','),
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "address": venue.address,
      "website": venue.website,
      "seeking_talent": venue.seeking_talent,
      "seeking_description": venue.seeking_description,
      "facebook_link": venue.facebook_link,
      "image_link": venue.image_link,
      "past_shows": past_shows_dict,
      "upcoming_shows": upcoming_shows_dict,
      "past_shows_count": past_shows_count,
      "upcoming_shows_count": upcoming_shows_count,
    }
  except:
    error = True
    print(sys.exc_info())
  if error:
    flash('An error occurred. Venue cannot be found.')
    return redirect(url_for('venues'))
  else:
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # insert new record of venue in the db
  # notify the user in success and fail
  error=False
  form = VenueForm(request.form)
  try:
      if form.validate_on_submit():
          seeking_talent = False
          # correct the value of seeking_talent before insertion
          if request.form.get('seeking_talent') == '' or request.form.get('seeking_talent') == 'y':
            seeking_talent = True
          venue = Venue(name=request.form['name'], 
          city=request.form['city'], 
          state=request.form['state'],
          phone=request.form['phone'], 
          address=request.form['address'], 
          genres=request.form.getlist('genres'),
          facebook_link=request.form['facebook_link'], 
          image_link=request.form['image_link'], 
          website=request.form['website'], 
          seeking_talent=seeking_talent, 
          seeking_description=request.form['seeking_description'])
          db.session.add(venue)
          db.session.commit()
      else:
          return render_template('forms/new_venue.html', form=form)
  except SQLAlchemyError as e:
      error = True
      flash(str(e._message))
  except:
      error = True
      print(sys.exc_info())
      db.session.rollback()
  finally:
      db.session.close()
  if error:
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
      return render_template('forms/new_venue.html', form=form)
  else:
      # on successful db insert, flash success
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
      return redirect(url_for('index'))
  

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # using a delete button in venue page, delete a record of that venue in the db
  # handle the error of fail
  # return back to home page in case of success
  error = False
  try:
    venue = Venue.query.get(venue_id)
    db.session.delete(venue)
    db.session.commit()
  except:
    error = True
    print(sys.exc_info())
    db.session.rollback()
  finally:
    db.session.close()
  if error:
    flash('An error occurred. Venue cannot be deleted.')
    abort(500)
  else:
    flash('Venue has been deleted successfully!!')
    return jsonify({"Success": True})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = Artist.query.with_entities(Artist.id, Artist.name).order_by('id').all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # search artists with incase-sensitive 
  # search_term is used from form
  
  # get num of artists based on search criteria
  artists_count = db.session.query(Artist.id)\
    .filter(Artist.name.ilike('%' + request.form.get('search_term') +'%')).count()
  # do search for the artists
  num = db.session.query(func.count(show.c.id))\
    .filter(show.c.artist_id == Artist.id)\
    .filter(show.c.start_time >= date.today())\
    .label('num_upcoming_shows')
  artists = db.session\
    .query(Artist.id, Artist.name, num)\
    .filter(Artist.name.ilike('%' + request.form.get('search_term') +'%'))\
    .all()
  artists_dict = []
  for artist in artists:
    artists_dict.append({
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": artist.num_upcoming_shows
    })
  response = {"count" : artists_count, "data" : artists_dict}
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # check for the artist and in case of fail, 
  # return an error message and redirect the user to Artists page
  error = False
  try:
    artist = Artist.query.get(artist_id)
    upcoming_shows = db.session.query(Venue, db.cast(show.c.start_time, db.String).label('start_time'))\
      .join(show)\
      .filter(show.c.artist_id == artist_id)\
      .filter(show.c.start_time >= date.today())\
      .group_by(Venue.id).group_by(show.c.start_time)\
      .all()
    upcoming_shows_count = db.session.query(Venue)\
      .join(show)\
      .filter(show.c.artist_id == artist_id)\
      .filter(show.c.start_time >= date.today())\
      .count()
    past_shows = db.session.query(Venue, db.cast(show.c.start_time, db.String).label('start_time'))\
      .join(show)\
      .filter(show.c.artist_id == artist_id)\
      .filter(show.c.start_time < date.today())\
      .group_by(Venue.id).group_by(show.c.start_time)\
      .all()
    past_shows_count = db.session.query(Venue)\
      .join(show)\
      .filter(show.c.artist_id == artist_id)\
      .filter(show.c.start_time < date.today())\
      .count()
    upcoming_shows_dict = []
    for venue in upcoming_shows:
        upcoming_shows_dict.append({
        "venue_id": venue.Venue.id,
        "venue_name": venue.Venue.name,
        "venue_image_link": venue.Venue.image_link,
        "start_time": venue.start_time
      })
    past_shows_dict = []
    for venue in past_shows:
        past_shows_dict.append({
        "venue_id": venue.Venue.id,
        "venue_name": venue.Venue.name,
        "venue_image_link": venue.Venue.image_link,
        "start_time": venue.start_time
      })
    # build returned data
    data = {
      "id": artist.id,
      "name": artist.name,
      "genres": artist.genres.replace('{','').replace('}','').replace('"','').split(','),
      "city": artist.city,
      "state": artist.state,
      "phone": artist.phone,
      "seeking_venue": artist.seeking_venue,
      "seeking_description": artist.seeking_description,
      "facebook_link": artist.facebook_link,
      "image_link": artist.image_link,
      "past_shows": past_shows_dict,
      "upcoming_shows": upcoming_shows_dict,
      "past_shows_count": past_shows_count,
      "upcoming_shows_count": upcoming_shows_count,
    }
  except:
    error = True
    print(sys.exc_info())
  if error:
    flash('An error occurred. Artist cannot be found.')
    return redirect(url_for('artists'))
  else:
    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  error = False
  try:
    artist = Artist.query.get(artist_id)
    # be sure to send the state/genres for the form to be built correctly
    form = ArtistForm(state=artist.state
    , genres=artist.genres.replace('{','').replace('}','').replace('"','').split(','))
  except:
      error = True
      print(sys.exc_info())
  if error:
    # handle the case of accesing not existing row
      flash('An error occurred. Artist cannot be found.')
      return redirect(url_for('artists'))
  else:
      return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  error=False
  form = ArtistForm(request.form)
  try:
      # validate the data in update too
      if form.validate_on_submit():
          seeking_venue = False
          # correct seeking_venue value before insertion
          if request.form.get('seeking_venue') == '' or request.form.get('seeking_venue') == 'y':
            seeking_venue = True
          artist = Artist.query.get(artist_id)
          artist.name=request.form['name'] 
          artist.city=request.form['city']
          artist.state=request.form['state']
          artist.phone=request.form['phone']
          artist.genres=request.form.getlist('genres') 
          artist.facebook_link=request.form['facebook_link']
          artist.image_link=request.form['image_link'] 
          artist.seeking_venue=seeking_venue
          artist.seeking_description=request.form['seeking_description']
          db.session.commit()
      else:
          return render_template('forms/edit_artist.html', form=form)
  except SQLAlchemyError as e:
      error = True
      flash(str(e._message))
  except:
      error = True
      print(sys.exc_info())
      db.session.rollback()
  finally:
      db.session.close()
  if error:
      # on unsuccessful db update, flash an error instead.
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
      return render_template('forms/edit_artist.html', form=form)
  else:
      # on successful db update, flash success
      flash('Artist ' + request.form['name'] + ' was successfully updated!')
      return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  error = False
  try:
    venue = Venue.query.get(venue_id)
    # send state and genres to the form to load data
    form = VenueForm(state=venue.state
    , genres=venue.genres.replace('{','').replace('}','').replace('"','').split(','))
  except:
    error = True
    print(sys.exc_info())
  if error:
    flash('An error occurred. Venue cannot be found.')
    return redirect(url_for('venues'))
  else:
    # populate form with values from venue with ID <venue_id>
    return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  error=False
  form = VenueForm(request.form)
  try:
      if form.validate_on_submit():
          # correct seeking_talent before update
          seeking_talent = False
          if request.form.get('seeking_talent') == '' or request.form.get('seeking_talent') == 'y':
            seeking_talent = True
          venue = Venue.query.get(venue_id)
          venue.name=request.form['name'] 
          venue.city=request.form['city']
          venue.state=request.form['state']
          venue.phone=request.form['phone']
          venue.address=request.form['address'] 
          venue.genres=request.form.getlist('genres') 
          venue.facebook_link=request.form['facebook_link']
          venue.image_link=request.form['image_link'] 
          venue.website=request.form['website'] 
          venue.seeking_talent=seeking_talent
          venue.seeking_description=request.form['seeking_description']
          db.session.commit()
      else:
          return render_template('forms/edit_venue.html', form=form)
  except SQLAlchemyError as e:
      error = True
      flash(str(e._message))
  except:
      error = True
      print(sys.exc_info())
      db.session.rollback()
  finally:
      db.session.close()
  if error:
      # on unsuccessful db update, flash an error instead.
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')
      return render_template('forms/edit_venue.html', form=form)
  else:
      # on successful db update, flash success
      flash('Venue ' + request.form['name'] + ' was successfully updated!')
      return redirect(url_for('show_venue', venue_id=venue_id))
  

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # insert form data as a new Arist record in the db
  error=False
  form = ArtistForm(request.form)
  try:
      if form.validate_on_submit():
          seeking_venue = False
          # correct seeking_venue before insertion
          if request.form.get('seeking_venue') == '' or request.form.get('seeking_venue') == 'y':
            seeking_venue = True
          artist = Artist(name=request.form['name'], 
          city=request.form['city'], 
          state=request.form['state'],
          phone=request.form['phone'], 
          genres=request.form.getlist('genres'), 
          facebook_link=request.form['facebook_link'], 
          image_link=request.form['image_link'], 
          seeking_venue=seeking_venue, 
          seeking_description=request.form['seeking_description'])
          db.session.add(artist)
          db.session.commit()
      else:
          return render_template('forms/new_artist.html', form=form)
  except SQLAlchemyError as e:
      error = True
      flash(str(e._message))
  except:
      error = True
      print(sys.exc_info())
      db.session.rollback()
  finally:
      db.session.close()
  if error:
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
      return render_template('forms/new_artist.html', form=form)
  else:
      # on successful db insert, flash success
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
      return redirect(url_for('index'))


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows
  # get the venues and for each, get the coressponding upcoming shows with artist data

  # get venues
  venues = Venue.query.all()
  data = []
  for venue in venues:
    # get upcoming shows for venue
    upcoming_shows = db.session.query(Artist, db.cast(show.c.start_time, db.String).label('start_time'))\
      .join(show)\
      .filter(show.c.venue_id == venue.id)\
      .filter(show.c.start_time >= date.today())\
      .group_by(Artist.id).group_by(show.c.start_time)\
      .all()
    num_shows = len(upcoming_shows)
    
    # build each row
    for current_show in upcoming_shows:
      show_row = {'venue_id': venue.id
      , 'venue_name': venue.name
      , 'artist_id': current_show.Artist.id
      , 'artist_name': current_show.Artist.name
      , 'artist_image_link': current_show.Artist.image_link
      , 'start_time': current_show.start_time
      , 'num_shows': num_shows}
      # build final returned data
      data.append(show_row)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  error=False
  form = ShowForm(request.form)
  try:
      if form.validate_on_submit():
          statement = show.insert().values(venue_id=request.form['venue_id']
          , artist_id=request.form['artist_id']
          , start_time=request.form['start_time'])
          db.session.execute(statement)
          db.session.commit()
      else:
          flash('An error occurred. Show could not be listed.')
          return render_template('forms/new_show.html', form=form)
  except SQLAlchemyError as e:
      error = True
      flash(str(e._message))
  except:
      error = True
      print(sys.exc_info())
      db.session.rollback()
  finally:
      db.session.close()
  if error:
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Show could not be listed.')
      return render_template('forms/new_show.html', form=form)
  else:
      # on successful db insert, flash success
      flash('Show was successfully listed!')
      return redirect(url_for('index'))

@app.route('/shows/search', methods=['POST'])
def search_shows():
  # using search term, search the shows in incase-sesitive
  # actually we search in names of both venues and articles to get any match
  data = []
    # get upcoming shows based on search_term
  shows = db.session.query(Artist.id, Artist.name, Artist.image_link, Venue.id, Venue.name, db.cast(show.c.start_time, db.String).label('start_time'))\
    .join(show, Venue.id == show.c.venue_id)\
    .filter(show.c.artist_id == Artist.id)\
    .filter(or_(Venue.name.ilike('%' + request.form.get('search_term') +'%'),\
    Artist.name.ilike('%' + request.form.get('search_term') +'%')))\
    .group_by(Artist.id).group_by(Venue.id).group_by(show.c.start_time)\
    .all() 
      
  num_shows = len(shows)
    
  # build each row
  for current_show in shows:
    show_row = {'venue_id': current_show[3] # venue id
    , 'venue_name': current_show[4] # venue name
    , 'artist_id': current_show[0] # artist id
    , 'artist_name': current_show[1] # artist name
    , 'artist_image_link': current_show[2] # artist image_link
    , 'start_time': current_show.start_time
    }
    # build final returned data
    data.append(show_row)
  # add num_shows and data to the response
  response = {"count" : num_shows, "data" : data}  
  return render_template('pages/show.html', results=response, search_term=request.form.get('search_term', ''))

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

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run(debug=True)

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
