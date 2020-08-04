from flask import Flask, request, redirect, url_for, json, session
import flask
import wtforms
import requests
import random
import musicbrainzngs as mb
from form import SongForm
from collections import Counter
import mysql.connector
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret key'

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="lionking",
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
    session['recs'] = []
    if 'list' in request.form:
        return redirect(url_for('get_likes'))
    if 'recs' in request.form:
        return redirect(url_for('show_recs'))
    elif request.method == 'GET':
        return flask.render_template("./index.html")

@app.route('/show_recs', methods = ['GET','POST'])
def show_recs():
    if 'generate' in request.form:
        return redirect(url_for('generate_rec'))
    if request.method == 'GET':
        return flask.render_template('./recommendations.html')
    

@app.route('/generate_rec', methods = ['GET','POST'])
def generate_rec():
    if len(session.get('recs')) == 0:
        generate_recommendations('rsharma')
    recs = session.get('recs')
    if len(recs) == 0:
        recs = session['seen']
        session['seen'] = []
    song_id = random.choice(recs)
    if session.get('seen') == None:
        session['seen'] = [song_id]
    else: 
        session['seen'].append(song_id)
    recs.remove(song_id)
    session['recs'] = recs
    song_info = get_song_from_id(song_id[0])
    message = "{title} by {artist}".format(title=song_info[0], artist=song_info[1])
    return flask.render_template('./recommendations.html', message=message)



@app.route('/get_likes', methods = ['GET','POST'])
def get_likes():
    #TODO get logged in user
    if request.method == 'POST':
        #TODO validate form
        form = request.form
        if 'add' in form:
            if form['tag'] == '':
                tag = None
            else:
                tag = form['tag']
            message = add_like(form['title'],form['artist'], tag)
        elif 'tag' in form:
            message = update_tag(form['title'], form['artist'],form['tag'])
    else:
        message = ''
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
    return flask.render_template("./liked_songs.html", likes= songs, message=message)

@app.route('/remove_like', methods=['POST'])
def remove_like():
    data = json.loads(request.data)
    for d in data:
        remove_like_from_db(d[0], d[1])
    return "Removed likes"


def remove_like_from_db(title, artist):
    #TODO: get logged in user
    form = request.form
    cursor = mydb.cursor()
    sql = "SELECT SongId FROM Songs WHERE Title = %s AND Artist = %s"
    val = (title, artist)
    cursor.execute(sql, val)
    result = cursor.fetchone()
    sql = "DELETE FROM Likes WHERE SongId = %s AND Username = %s"
    val = (result[0], 'rsharma')
    cursor.execute(sql, val)
    mydb.commit()
    cursor.close()
    

def add_like(title, artist, tag):
    #TODO get logged in user
    cursor = mydb.cursor()
    sql = "SELECT * FROM Likes l, (SELECT SongId FROM Songs WHERE Title = %s AND Artist = %s) temp WHERE l.SongId = temp.SongId AND l.Username = %s"
    val = (title, artist, 'rsharma')
    cursor.execute(sql,val)
    result = cursor.fetchall()
    print(result)
    if len(result) > 0:
        return "You have already liked this song!"
    url = "{last_fm}&artist={artist}&track={title}&format=json".format(last_fm = LAST_FM, artist = artist, title = title)
    r = requests.get(url)
    resp = r.json()
    if "error" in resp:
        return "Sorry, we couldn't find that song!"
    song_metadata = get_metadata_from_resp(resp)
    song_id = add_song_to_db(song_metadata, tag)
    add_like_to_db(song_id)
    message = "Added {song} by {artist}".format(song = resp["track"]["name"], artist = resp["track"]["artist"]["name"])
    return message

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

def add_song_to_db(metadata, tag):
    cursor = mydb.cursor()
    sql = "SELECT SongId FROM Songs WHERE Title = %s AND Artist = %s"
    val = (metadata[0], metadata[1])
    cursor.execute(sql, val)
    result = cursor.fetchall()
    if len(result) > 0:
        print(result)
        return result[0][0]
    sql = "INSERT INTO Songs (Title,Artist,Duration,Tag) VALUES (%s, %s, %s, %s)"
    if tag == None:
        cursor.execute(sql, metadata)
    else:
        vals = (metadata[0], metadata[1], metadata[2], tag)
        cursor.execute(sql, vals)
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

def update_tag(title, artist, new_tag):
    #TODO update tag not globally
    cursor = mydb.cursor()
    sql = "SELECT Tag FROM Songs WHERE Title = %s AND Artist = %s"
    val = (title, artist)
    cursor.execute(sql, val)
    result = cursor.fetchone()
    if result == None:
        return "Sorry, you haven't liked that song!" 
    sql = "UPDATE Songs SET Tag = %s WHERE Title = %s AND Artist = %s"
    val = (new_tag, title, artist)
    cursor.execute(sql,val)
    mydb.commit()
    cursor.close()
    message = "Changed tag for {title} by {artist} from {old} to {new}".format(title=title, artist=artist, old=result[0], new=new_tag)
    return message

def get_song_from_id(id_):
   cursor = mydb.cursor() 
   sql = "SELECT Title, Artist FROM Songs WHERE SongId = %s"
   val = (id_,)
   cursor.execute(sql,val)
   result = cursor.fetchone() 
   cursor.close()
   return result

def generate_recommendations(user_id):
    print('hello')
    cursor = mydb.cursor()
    sql = "SELECT u.Username, COUNT(SongId) FROM Likes l, Users u WHERE l.Username = %s AND SongId IN (SELECT SongId FROM Likes WHERE Likes.Username = u.Username AND Likes.Username <> %s) GROUP BY u.Username ORDER BY COUNT(SongId) DESC LIMIT 10;"
    val = (user_id, user_id)
    cursor.execute(sql,val)
    result = cursor.fetchall()
    if len(result) == 0:
        top_tag = get_top_tag(user_id)
        sql = "SELECT SongId FROM Songs WHERE tag = %s AND SongId NOT IN (SELECT SongId FROM Likes WHERE Username = %s) LIMIT 5"
        val = (top_tag,user_id)
        cursor.execute(sql,val)
        result = cursor.fetchall()
        session['recs'] = result
        return
    scores = {}
    for user in result:
        scores[user[0]] = generate_similarity_score(user_id, user[0], user[1])
    most_similar = get_top_three(scores)
    recs = []
    for u in most_similar:
        other_user = u[0]
        sql = "SELECT SongId FROM Likes l WHERE l.Username = %s AND l.SongId NOT IN (SELECT SongId FROM Likes WHERE Likes.Username = %s)"
        val = (other_user, user_id)
        cursor.execute(sql, val)
        result = cursor.fetchall()
        recs += result
    cursor.close()
    session['recs'] = recs

def generate_similarity_score(current_user, other_user, num_similar_songs):
    score = (num_similar_songs / get_total_num_likes(current_user)) * 100
    if get_top_tag(current_user) == get_top_tag(other_user):
        score += 5
    if get_top_artist(current_user) == get_top_artist(other_user):
        score += 10


def get_top_three(scores):
    count = Counter(scores)
    return count.most_common(3)

def get_top_tag(user):
    cursor = mydb.cursor()
    sql = "SELECT tag, COUNT(tag) FROM (SELECT SongId FROM Likes WHERE Username = %s) temp JOIN Songs ON temp.SongId = Songs.SongId GROUP BY tag ORDER BY COUNT(tag) DESC LIMIT 1"
    val = (user,)
    cursor.execute(sql, val)
    result = cursor.fetchone()
    return result[0]

def get_top_artist(user):
    cursor = mydb.cursor()
    sql = "SELECT Artist, COUNT(Artist) FROM (SELECT SongId FROM Likes WHERE Username = %s) temp JOIN Songs ON temp.SongId = Songs.SongId GROUP BY Artist ORDER BY COUNT(Artist) DESC LIMIT 1"

    val = (user,)
    cursor.execute(sql, val)
    result = cursor.fetchone()
    return result[0]

def get_total_num_likes(user):
    cursor = mydb.cursor()
    sql = "SELECT COUNT(SongId) FROM Likes WHERE Username = %s"
    val = (user,)
    cursor.execute(sql, val)
    result = cursor.fetchone()
    return result[0]
 

if __name__ == '__main__':
    app.run(debug=True)
