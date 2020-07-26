from flask import Flask, request, redirect, url_for
import flask
import wtforms
import requests
import musicbrainzngs as mb
from form import SongForm
import mysql.connector
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret key'

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  database="song_recommender"
)
mb.set_useragent(
    "song-recommender",
    "0.1",
    "https://github.com/rohinisharma/Song-Recommender",
)
API_KEY = "f3cf3efb1ef7e50dad9926b3c9d4263e"
LAST_FM= "http://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={api}&autocorrect=1".format(api = API_KEY)



@app.route('/', methods = ['GET','POST'])
def index():
    if 'add' in request.form:
        return flask.render_template("./add_song.html")
    if 'list' in request.form:
        return redirect(url_for('get_likes'))
    elif request.method == 'GET':
        return flask.render_template("./index.html")

@app.route('/add_like', methods = ['POST'])
def add_like():
    #TODO validate form
    form = request.form
    url = "{last_fm}&artist={artist}&track={title}&format=json".format(last_fm = LAST_FM, artist = form["artist"], title = form["title"])
    r = requests.get(url)
    resp = r.json()
    if "error" in resp:
        message = "Sorry, we couldn't find that song!"
    else:
        song_metadata = get_metadata_from_resp(resp)
        song_id = add_song_to_db(song_metadata)
        add_like_to_db(song_id)
        message = "Added {song} by {artist}".format(song = resp["track"]["name"], artist = resp["track"]["artist"]["name"])
    return flask.render_template("./add_song.html", message=message)


@app.route('/get_likes', methods = ['GET'])
def get_likes():
    #TODO get logged in user
    cursor = mydb.cursor()
    sql = "SELECT SongId FROM Likes WHERE Username = %s"
    val = ('rsharma',)
    cursor.execute(sql,val)
    result = cursor.fetchall()
    songs = []
    for r in result: 
        sql = "SELECT * FROM Songs WHERE SongId = %s"
        cursor.execute(sql,r)
        result = cursor.fetchone()
        songs.append(result)
    cursor.close()
    return flask.render_template("./liked_songs.html", likes= songs)

def add_user(metadata):
    cursor = mydb.cursor()
    #Adds a user to the DB
    sql = "INSERT INTO Users (firstName,lastName) VALUES (%s, %s)"
    cursor.execute(sql, metadata)
    user_id = cursor.lastrowid
    mydb.commit()
    cursor.close()
    return user_id

def get_metadata_from_resp(resp):
    name = resp["track"]["name"]
    artist = resp["track"]["artist"]["name"]
    if "duration" not in resp['track'] or resp["track"]["duration"] == "0":
        duration = None 
    else:
        duration = resp["track"]["duration"]
    if len(resp["track"]["toptags"]["tag"]) < 1:
        tag = None
    else:
        tag = resp["track"]["toptags"]["tag"][0]["name"]
    return (name, artist, duration, tag)

def add_song_to_db(metadata):
    cursor = mydb.cursor()
    sql = "SELECT SongId FROM Songs WHERE Title = %s AND Artist = %s"
    val = (metadata[0], metadata[1])
    cursor.execute(sql, val)
    result = cursor.fetchall()
    if len(result) > 0:
        print(result)
        return result[0][0]
    sql = "INSERT INTO Songs (Title,Artist,Duration,Tag) VALUES (%s, %s, %s, %s)"
    cursor.execute(sql, metadata)
    song_id = cursor.lastrowid
    mydb.commit()
    cursor.close()
    return song_id

def add_like_to_db(song_id):
    cursor = mydb.cursor()
    sql = "INSERT IGNORE INTO Likes (SongId, Username) VALUES (%s,%s)"
    val = (song_id, "rsharma")
    cursor.execute(sql, val)
    mydb.commit()
    cursor.close()

if __name__ == '__main__':
    app.run(debug=True)
