import os
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "ULTRA_SECURE_FILM_KEY"

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- MongoDB Setup ---
# এখানে আপনার মঙ্গোডিবি ইউআরএল বসান
MONGO_URI = "mongodb+srv://roxiw19528:roxiw19528@cluster0.vl508y4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['movie_v5_final']
movies_col = db['movies']
settings_col = db['settings']
cat_col = db['categories']

# --- ডিফল্ট সেটিংস ও এডমিন ডাটা ---
def get_settings():
    settings = settings_col.find_one()
    if not settings:
        default = {
            "site_name": "PREMIUM-CINEMA", "logo_url": "", "notice_text": "Welcome to our Premium Movie Portal",
            "notice_bg": "#ff0000", "notice_color": "#ffffff", "thumb_width": "280", "thumb_height": "160",
            "thumb_margin": "10", "tg_token": "", "tg_chat_id": "", "post_limit": 6, 
            "ad_banner": "", "ad_popunder": "", "ad_social": "",
            "admin_user": "admin", "admin_pass": "admin"
        }
        settings_col.insert_one(default)
        return default
    return settings

# --- CSS Design (Modern Dark Premium) ---
BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    :root { --primary: #ff0000; --bg: #050505; --card: #121212; --sidebar: #111; --text: #fff; }
    body { background: var(--bg); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; overflow-x: hidden; }
    
    /* Rainbow Logo */
    @keyframes rainbow { 0%{color:#f00} 25%{color:#ff0} 50%{color:#0f0} 75%{color:#0ff} 100%{color:#f00} }
    .logo { font-size: 26px; font-weight: 800; animation: rainbow 5s infinite; text-decoration: none; padding: 15px; display: block; text-align: center; }

    .notice-bar { padding: 10px; text-align: center; font-size: 14px; font-weight: bold; position: sticky; top: 0; z-index: 1001; }
    .container { width: 95%; max-width: 1400px; margin: auto; padding-bottom: 50px; }

    /* Sidebar Navigation */
    .sidebar { width: 260px; height: 100vh; background: var(--sidebar); position: fixed; left: -260px; top: 0; transition: 0.4s; z-index: 2000; border-right: 1px solid #222; }
    .sidebar.active { left: 0; }
    .sidebar-header { padding: 20px; border-bottom: 1px solid #222; font-weight: bold; font-size: 20px; color: var(--primary); text-align:center; }
    .sidebar a { display: block; padding: 15px 20px; color: #ccc; text-decoration: none; border-bottom: 1px solid #1a1a1a; transition: 0.3s; }
    .sidebar a:hover { background: #222; color: var(--primary); padding-left: 30px; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1999; }
    .overlay.active { display: block; }
    .menu-btn { cursor: pointer; font-size: 25px; color: #fff; position: fixed; top: 50px; left: 15px; z-index: 1002; background: var(--primary); width: 45px; height: 45px; line-height: 45px; text-align: center; border-radius: 50%; box-shadow: 0 0 15px rgba(255,0,0,0.5); }

    /* Movie Cards */
    .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 20px; }
    .movie-card { background: var(--card); border-radius: 12px; overflow: hidden; text-decoration: none; color: #fff; border: 1px solid #222; transition: 0.4s; text-align:center; }
    .movie-card:hover { transform: translateY(-8px); border-color: var(--primary); }
    .movie-card img { width: 100%; object-fit: cover; }
    .movie-info { padding: 10px; font-weight: 600; }

    /* Admin Panel Elements */
    .admin-card { background: #111; padding: 20px; border-radius: 15px; margin-bottom: 25px; border: 1px solid #333; }
    input, textarea, select { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #333; background: #000; color: #fff; box-sizing: border-box; font-family: inherit; }
    .btn { background: var(--primary); color: #fff; border: none; padding: 12px 25px; cursor: pointer; border-radius: 8px; font-weight: bold; width: 100%; transition: 0.3s; }
    .btn:hover { background: #b30000; }
    
    /* HTML Preview Box */
    #preview-container { margin-top: 15px; padding: 10px; background: #000; border: 2px dashed #444; min-height: 100px; border-radius: 10px; }

    @media (max-width: 768px) { .movie-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; } .sidebar { width: 220px; } }
</style>
"""

# --- NAV COMPONENT ---
NAV_SIDEBAR = """
<div class="menu-btn" onclick="toggleSidebar()">☰</div>
<div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
<div class="sidebar" id="sidebar">
    <div class="sidebar-header">MENU</div>
    {% if session.admin %}
    <a href="/admin">📊 Movie Dashboard</a>
    <a href="/admin/category">📂 Categories</a>
    <a href="/admin/settings">⚙️ Site Settings</a>
    <a href="/admin/ads">💰 Ad Management</a>
    <a href="/admin/auth">🔐 Admin Security</a>
    <a href="/logout" style="color:red;">🚪 Logout</a>
    {% else %}
    <a href="/">🏠 Home</a>
    {% for c in all_categories %}
    <a href="/category/{{c.name}}">📁 {{c.name}}</a>
    {% endfor %}
    <a href="/login">🔑 Admin Login</a>
    {% endif %}
</div>
<script>
    function toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('active');
        document.getElementById('overlay').classList.toggle('active');
    }
</script>
"""

# --- PAGE TEMPLATES ---

HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ settings.site_name }}</title>
    """ + BASE_CSS + """
</head>
<body>
    <div class="notice-bar" style="background:{{ settings.notice_bg }}; color:{{ settings.notice_color }};">
        <marquee>{{ settings.notice_text }}</marquee>
    </div>
    """ + NAV_SIDEBAR + """
    <header class="container">
        <a href="/" class="logo">{{ settings.site_name }}</a>
        <form action="/" method="GET" style="text-align:center;">
            <input type="text" name="search" placeholder="Search movies..." style="width:80%; max-width:500px; border-radius:30px; border:1px solid var(--primary); text-align:center;">
        </form>
    </header>

    <div class="container">
        <div style="text-align:center;">{{ settings.ad_banner | safe }}</div>

        {% for cat in categories %}
        <div class="cat-section">
            <div style="display:flex; justify-content:space-between; align-items:center; border-left:5px solid red; padding-left:15px; margin:20px 0;">
                <h2 style="margin:0;">{{ cat }}</h2>
                <a href="/category/{{cat}}" style="color:red; text-decoration:none; font-weight:bold;">SEE ALL →</a>
            </div>
            <div class="movie-grid">
                {% for movie in movie_data[cat] %}
                <a href="/movie/{{ movie._id }}" class="movie-card">
                    <img src="{{ movie.thumb }}" style="width:{{settings.thumb_width}}px; height:{{settings.thumb_height}}px; padding:{{settings.thumb_margin}}px">
                    <div class="movie-info">{{ movie.name }}<br><small style="color:red;">{{ movie.lang }}</small></div>
                </a>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        <div style="text-align:center; margin-top:20px;">{{ settings.ad_social | safe }}</div>
    </div>
</body>
</html>
"""

# --- ADMIN TEMPLATES ---

ADMIN_WRAPPER = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin - {{ settings.site_name }}</title>
    """ + BASE_CSS + """
</head>
<body>
    """ + NAV_SIDEBAR + """
    <div class="container" style="margin-top:80px;">
        <h1 style="text-align:center; color:red;">ADMIN DASHBOARD</h1>
        {{ content | safe }}
    </div>
</body>
</html>
"""

SAVE_MOVIE_HTML = """
<div class="admin-card">
    <h3>{% if edit_movie %}Edit Movie{% else %}Add New Movie{% endif %}</h3>
    <form action="/admin/save-movie" method="POST" enctype="multipart/form-data">
        <input type="hidden" name="movie_id" value="{{ edit_movie._id if edit_movie else '' }}">
        <input type="text" name="name" value="{{ edit_movie.name if edit_movie else '' }}" placeholder="Movie Name" required>
        
        <label>Thumbnail System:</label>
        <select name="thumb_type" onchange="toggleThumb(this.value)">
            <option value="url">External URL</option>
            <option value="file">Upload from Gallery</option>
        </select>
        <input type="text" id="thumb_url" name="thumb_url" value="{{ edit_movie.thumb if edit_movie else '' }}" placeholder="Thumbnail URL">
        <input type="file" id="thumb_file" name="thumb_file" style="display:none;">

        <select name="cat" required>
            <option value="">Select Category</option>
            {% for c in all_categories %}
            <option value="{{c.name}}" {% if edit_movie and edit_movie.cat == c.name %}selected{% endif %}>{{c.name}}</option>
            {% endfor %}
        </select>
        <input type="text" name="lang" value="{{ edit_movie.lang if edit_movie else '' }}" placeholder="Language">
        
        <label>HTML Player Code (Real-time Preview):</label>
        <textarea id="html_code" name="html_code" rows="6" oninput="updatePreview(this.value)" placeholder="Paste your HTML embed/player code here">{{ edit_movie.html_code if edit_movie else '' }}</textarea>
        
        <div id="preview-container">
            <small style="color:#888;">Live Preview:</small>
            <div id="html-preview"></div>
        </div>
        
        <button type="submit" class="btn" style="margin-top:20px;">Save & Post Movie</button>
    </form>
</div>

<script>
    function toggleThumb(val) {
        document.getElementById('thumb_url').style.display = (val=='url'?'block':'none');
        document.getElementById('thumb_file').style.display = (val=='file'?'block':'none');
    }
    function updatePreview(val) {
        document.getElementById('html-preview').innerHTML = val;
    }
    // Initial Preview
    window.onload = function() { updatePreview(document.getElementById('html_code').value); };
</script>
"""

# --- BACKEND LOGIC ---

@app.route('/')
def home():
    settings = get_settings()
    search = request.args.get('search')
    all_cats = list(cat_col.find().sort("name", 1))
    movie_data = {}
    categories = [c['name'] for c in all_cats]
    for cat in categories:
        query = {"cat": cat}
        if search: query["name"] = {"$regex": search, "$options": "i"}
        movie_data[cat] = list(movies_col.find(query).sort("name", 1).limit(int(settings['post_limit'])))
    return render_template_string(HOME_HTML, settings=settings, categories=categories, movie_data=movie_data, all_categories=all_cats)

@app.route('/movie/<id>')
def details(id):
    settings = get_settings()
    movie = movies_col.find_one({"_id": ObjectId(id)})
    if not movie: return "Movie Not Found"
    all_cats = list(cat_col.find().sort("name", 1))
    
    DETAIL_PAGE = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ movie.name }}</title>
        """ + BASE_CSS + """
    </head>
    <body>
        """ + NAV_SIDEBAR + """
        <div class="container" style="text-align:center; padding-top:80px;">
            <h1>{{ movie.name }}</h1>
            <div style="margin:20px 0;">{{ settings.ad_banner | safe }}</div>
            <div style="background:#000; padding:15px; border-radius:15px; border:1px solid #333; min-height:300px;">
                {{ movie.html_code | safe }}
            </div>
            <p>Language: {{ movie.lang }} | Category: {{ movie.cat }}</p>
            <div style="margin:20px 0;">{{ settings.ad_social | safe }}</div>
        </div>
        {{ settings.ad_popunder | safe }}
    </body>
    </html>
    """
    return render_template_string(DETAIL_PAGE, movie=movie, settings=settings, all_categories=all_cats)

@app.route('/category/<name>')
def category_page(name):
    settings = get_settings()
    movies = list(movies_col.find({"cat": name}).sort("name", 1))
    all_cats = list(cat_col.find().sort("name", 1))
    return render_template_string(HOME_HTML, settings=settings, categories=[name], movie_data={name: movies}, all_categories=all_cats)

# --- ADMIN ACTIONS ---

@app.route('/admin')
def admin_dash():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    all_cats = list(cat_col.find())
    edit_id = request.args.get('edit_id')
    edit_movie = movies_col.find_one({"_id": ObjectId(edit_id)}) if edit_id else None
    
    search = request.args.get('search')
    query = {"name": {"$regex": search, "$options": "i"}} if search else {}
    movies_list = list(movies_col.find(query).sort("_id", -1))
    
    content = render_template_string(SAVE_MOVIE_HTML, all_categories=all_cats, edit_movie=edit_movie)
    content += '<div class="admin-card"><h3>Movie List</h3><form method="GET"><input type="text" name="search" placeholder="Search..."></form><table width="100%">'
    for m in movies_list:
        content += f"<tr style='border-bottom:1px solid #222;'><td>{m['name']}</td><td><a href='/admin?edit_id={m['_id']}'>Edit</a> | <a href='/delete/{m['_id']}' style='color:red;'>Delete</a></td></tr>"
    content += "</table></div>"
    
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_categories=all_cats)

@app.route('/admin/save-movie', methods=['POST'])
def save_movie():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    movie_id = request.form.get('movie_id')
    
    thumb = request.form.get('thumb_url')
    if 'thumb_file' in request.files:
        file = request.files['thumb_file']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            thumb = '/static/uploads/' + filename
            
    data = {
        "name": request.form['name'], "thumb": thumb,
        "lang": request.form['lang'], "cat": request.form['cat'], "html_code": request.form['html_code']
    }
    
    if movie_id:
        movies_col.update_one({"_id": ObjectId(movie_id)}, {"$set": data})
    else:
        new_m = movies_col.insert_one(data)
        if settings['tg_token'] and settings['tg_chat_id']:
            url = request.host_url + "movie/" + str(new_m.inserted_id)
            msg = f"🎬 *New Movie:* {data['name']}\n🌍 *Lang:* {data['lang']}\n🔗 [Watch Now]({url})"
            requests.post(f"https://api.telegram.org/bot{settings['tg_token']}/sendPhoto", data={"chat_id": settings['tg_chat_id'], "photo": data['thumb'], "caption": msg, "parse_mode": "Markdown"})
    return redirect('/admin')

@app.route('/admin/category', methods=['GET', 'POST'])
def admin_cat():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    if request.method == 'POST':
        cat_col.insert_one({"name": request.form['cat_name']})
        return redirect('/admin/category')
    
    all_cats = list(cat_col.find().sort("name", 1))
    content = f"""<div class="admin-card"><h3>Categories</h3><form method="POST"><input name="cat_name" placeholder="New Cat Name"><button class="btn">Add</button></form>
    <table width="100%">"""
    for c in all_cats:
        content += f"<tr><td>{c['name']}</td><td><a href='/admin/cat/del/{c['_id']}'>Delete</a></td></tr>"
    content += "</table></div>"
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_categories=all_cats)

@app.route('/admin/cat/del/<id>')
def del_cat(id):
    cat_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin/category')

@app.route('/admin/auth', methods=['GET', 'POST'])
def admin_auth():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    if request.method == 'POST':
        new_user = request.form['admin_user']
        new_pass = request.form['admin_pass']
        settings_col.update_one({}, {"$set": {"admin_user": new_user, "admin_pass": new_pass}})
        flash("Admin Login Updated!")
        return redirect('/admin/auth')
    
    content = f"""<div class="admin-card"><h3>Security Settings</h3><form method="POST">
    New Username: <input name="admin_user" value="{settings['admin_user']}">
    New Password: <input name="admin_pass" value="{settings['admin_pass']}">
    <button class="btn">Update Admin Access</button></form></div>"""
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_categories=list(cat_col.find()))

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    if request.method == 'POST':
        settings_col.update_one({}, {"$set": request.form.to_dict()})
        return redirect('/admin/settings')
    
    content = f"""<div class="admin-card"><h3>Site Config</h3><form method="POST">
    Name: <input name="site_name" value="{settings['site_name']}">
    Logo URL: <input name="logo_url" value="{settings['logo_url']}">
    Notice: <input name="notice_text" value="{settings['notice_text']}">
    Notice BG: <input type="color" name="notice_bg" value="{settings['notice_bg']}">
    Thumb Width: <input name="thumb_width" value="{settings['thumb_width']}">
    Thumb Height: <input name="thumb_height" value="{settings['thumb_height']}">
    Post Limit: <input name="post_limit" value="{settings['post_limit']}">
    <button class="btn">Save</button></form></div>"""
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_categories=list(cat_col.find()))

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    if request.method == 'POST':
        settings_col.update_one({}, {"$set": request.form.to_dict()})
        return redirect('/admin/ads')
    content = f"""<div class="admin-card"><h3>Ads</h3><form method="POST">
    Banner: <textarea name="ad_banner">{settings['ad_banner']}</textarea>
    Popunder: <textarea name="ad_popunder">{settings['ad_popunder']}</textarea>
    Social Bar: <textarea name="ad_social">{settings['ad_social']}</textarea>
    <button class="btn">Update Ads</button></form></div>"""
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_categories=list(cat_col.find()))

@app.route('/delete/<id>')
def del_movie(id):
    if not session.get('admin'): return redirect('/login')
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

@app.route('/login', methods=['GET', 'POST'])
def login():
    settings = get_settings()
    if request.method == 'POST':
        if request.form['user'] == settings['admin_user'] and request.form['pass'] == settings['admin_pass']:
            session['admin'] = True
            return redirect('/admin')
    return render_template_string("""<body style="background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
    <form method="POST" style="background:#111;padding:40px;border-radius:15px;width:300px;">
    <h2 style="text-align:center;">ADMIN ACCESS</h2>
    <input type="text" name="user" placeholder="Username" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;">
    <input type="password" name="pass" placeholder="Password" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;">
    <button style="width:100%;padding:10px;background:red;color:#fff;border:none;cursor:pointer;">LOGIN</button></form></body>""")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
