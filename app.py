from flask import Flask, flash, render_template, session, request, redirect, jsonify, url_for
import os
import bcrypt
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from filmScoring import FilmScoring

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'static/aset'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg'}
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'movie'
app.config['MYSQL_HOST'] = 'localhost'
mysql = MySQL(app)
csrf = CSRFProtect(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM films ORDER BY scd_id")
    data = cur.fetchall()
    cur.close()
    return render_template('index.html', films=data)

@app.route('/about/<int:film_id>')
def about(film_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM films WHERE id = %s", (film_id,))
    film = cur.fetchone()
    cur.close()
    return render_template('about.html', film=film)
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        if 'poster' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['poster']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            flash('File type not allowed') 
        
        # Ensure all form fields are captured and saved correctly
        judul = request.form.get('judul')
        tahun = request.form.get('tahun')
        aktor = request.form.get('aktor')
        link = request.form.get('link')
        deskripsi = request.form.get('deskripsi')
        sinopsis = request.form.get('sinopsis')
        rating = request.form.get('rating')
        penonton = request.form.get('penonton')
        harga = request.form.get('harga')
        vote = request.form.get('vote')
        
        # Insert form data into the database
        cur = mysql.connection.cursor()
        cur.execute("""INSERT INTO films(judul, tahun, penonton, harga, rating, vote, deskripsi, sinopsis, poster, link, aktor)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (judul, tahun, penonton, harga, rating, vote, deskripsi, sinopsis, filename, link, aktor))
        mysql.connection.commit()
        flash('Film successfully added')
                # Konfigurasi database
        db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'movie'
        }
        # Bobot kriteria
        criteria_weights = {'harga': 0.10, 'tahun': 0.20, 'penonton': 0.30, 'rating': 0.30, 'vote': 0.10}
        # Memperbarui skor dalam database dan mengatur ulang scd_id
        film_scoring = FilmScoring(db_config, criteria_weights)
        film_scoring.update_scores_in_db()
        # Fetch sorted films by score and update scd_id
        cur.execute("SELECT id FROM films ORDER BY score DESC")
        sorted_films = cur.fetchall()

        scd_id = 200
        for film in sorted_films:
            cur.execute("UPDATE films SET scd_id = %s WHERE id = %s", (scd_id, film[0]))
            scd_id += 1

        mysql.connection.commit()
        cur.close()
        return redirect(request.url)
    else:
        return redirect('/admin')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (username, email,  hashed_password))
        mysql.connection.commit()
        cur.close()
        
        flash('You have successfully registered!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE name = %s", [username])
        user = cur.fetchone()
        cur.close()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['username'] = user[1]
            flash('You have successfully logged in!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Login Unsuccessful. Please check your username and password', 'danger')
            return redirect(url_for('register'))  # Mengarahkan ke halaman pendaftaran
    return render_template('login.html')
@app.route('/admin')
def admin():
    if 'username' not in session:
        return redirect(url_for('login'))
    else: 
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM films order by scd_id")
        data = cur.fetchall()
        cur.close()
        return render_template('admin.html', films=data)

@app.route('/nilai')
def nilai():
    if 'username' not in session:
        return redirect(url_for('login'))
    else:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM films ORDER BY scd_id")
        data = cur.fetchall()
        cur.close()
        return render_template('nilai.html', films=data)

@app.route('/input')
def input():
    if 'username' not in session:
        return redirect(url_for('login'))
    else:
        return render_template('input.html')
        
@app.route('/logout')
def logout():
    # Hapus session 'username'
    session.pop('username', None)
    # Redirect ke halaman login
    return redirect(url_for('login'))
if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
