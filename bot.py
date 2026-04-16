import os
import base64
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "ultra_premium_key_99"

# --- Upload Configuration ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Vercel-এ ফোল্ডার তৈরি করা যায় না, তাই এটি try-except এ রাখা হয়েছে যেন ইরোর না দেয়
try:
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except:
    pass

# --- MongoDB Setup ---
# আপনার দেওয়া লিঙ্কটিই রাখা হয়েছে
MONGO_URI = "mongodb+srv://roxiw19528:roxiw19528@cluster0.vl508y4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['movie_v53']
movies_col = db['movie']
settings_col = db['settings']
cat_col = db['categories']

# --- ডিফল্ট সেটিংস লোড ---
def get_settings():
    settings = settings_col.find_one()
    if not settings:
        default = {
            "site_name": "PREMIUM-FILM", 
            "logo_url": "", 
            "notice_text": "Welcome to Premium Movie Hub",
            "notice_bg": "#ff0000", 
            "notice_color": "#ffffff", 
            "thumb_width": "280", 
            "thumb_height": "160",
            "thumb_margin": "10", 
            "tg_token": "", 
            "tg_chat_id": "", 
            "post_limit": 5, 
            "ad_banner": "", 
            "ad_popunder": "", 
            "ad_social": "",
            "admin_user": "admin", # ডিফল্ট ইউজার
            "admin_pass": "admin"  # ডিফল্ট পাসওয়ার্ড
        }
        settings_col.insert_one(default)
        return default
    return settings

# --- CSS Design (Premium Sidebar & Responsive Grid) ---
BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    :root { --primary: #e50914; --dark: #080808; --card: #121212; --text: #ffffff; --sidebar: #111; }
    body { background: var(--dark); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; overflow-x: hidden; }
    
    /* Rainbow Logo Animation */
    @keyframes rainbow { 0%{color:#ff0000} 15%{color:#ff8800} 30%{color:#ffff00} 45%{color:#00ff00} 60%{color:#00ffff} 75%{color:#0000ff} 90%{color:#8800ff} 100%{color:#ff0000} }
    .logo { font-size: 26px; font-weight: 800; animation: rainbow 4s infinite; text-decoration: none; display: flex; align-items: center; justify-content: center; padding: 15px; }

    .notice-bar { padding: 10px; text-align: center; font-size: 14px; font-weight: bold; }
    .container { width: 95%; max-width: 1400px; margin: auto; }

    /* Sidebar Navigation */
    .sidebar { position: fixed; left: -280px; top: 0; height: 100%; width: 280px; background: var(--sidebar); transition: 0.3s; z-index: 1001; border-right: 1px solid #333; }
    .sidebar.active { left: 0; }
    .sidebar-header { padding: 20px; border-bottom: 1px solid #333; font-weight: bold; color: var(--primary); font-size: 20px; text-align: center; }
    .sidebar a { display: block; padding: 15px 20px; color: white; text-decoration: none; border-bottom: 1px solid #222; transition: 0.3s; }
    .sidebar a:hover { background: var(--primary); padding-left: 30px; }
    
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; }
    .overlay.active { display: block; }
    
    .menu-trigger { cursor: pointer; font-size: 28px; color: #fff; padding: 10px; position: fixed; top: 40px; left: 15px; z-index: 999; background: var(--primary); border-radius: 5px; width: 45px; height: 45px; display: flex; align-items: center; justify-content: center; }

    /* Movie Grid (Auto Desktop/Mobile) */
    .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }
    .movie-card { background: var(--card); border-radius: 8px; overflow: hidden; text-decoration: none; color: #fff; transition: 0.3s; border: 1px solid #222; position: relative; }
    .movie-card:hover { transform: translateY(-5px); border-color: var(--primary); }
    .movie-card img { width: 100%; object-fit: cover; }
    
    /* Movie Badge Badge Style */
    .movie-badge { position: absolute; top: 10px; left: 10px; background: var(--primary); color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; z-index: 2; box-shadow: 0 0 5px rgba(0,0,0,0.5); }

    .movie-info { padding: 10px; text-align: center; font-size: 14px; }

    /* Slider */
    .slider { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding: 10px 0; scrollbar-width: none; }
    .slider::-webkit-scrollbar { display: none; }
    .slide-item { flex: 0 0 85%; scroll-snap-align: start; position: relative; border-radius: 15px; overflow: hidden; height: 280px; }
    .slide-item img { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.6); }

    /* Admin UI */
    .admin-section { display: none; padding: 20px; }
    .admin-section.active { display: block; }
    .input-group { background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333; }
    input, textarea, select { width: 100%; padding: 12px; margin: 8px 0; border-radius: 5px; border: 1px solid #333; background: #000; color: #fff; box-sizing: border-box; }
    .btn { background: var(--primary); color: #fff; border: none; padding: 12px 25px; cursor: pointer; border-radius: 5px; font-weight: bold; width: 100%; }
    
    #html-preview { background: #000; border: 1px dashed #555; padding: 10px; margin-top: 10px; min-height: 100px; border-radius: 5px; }

    @media (max-width: 600px) { .movie-grid { grid-template-columns: repeat(2, 1fr); } .slide-item { flex: 0 0 95%; } }
</style>
"""

# --- SIDEBAR COMPONENT ---
SIDEBAR_HTML = """
<div class="menu-trigger" onclick="toggleSidebar()">☰</div>
<div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
<div class="sidebar" id="sidebar">
    <div class="sidebar-header">MENU</div>
    <a href="/">🏠 Home</a>
    {% if session.admin %}
    <a href="javascript:void(0)" onclick="showSection('add_movie')">➕ Add Movie</a>
    <a href="javascript:void(0)" onclick="showSection('movie_list')">🎬 Manage Movies</a>
    <a href="javascript:void(0)" onclick="showSection('cat_manage')">📂 Categories</a>
    <a href="javascript:void(0)" onclick="showSection('site_settings')">⚙️ Site Settings</a>
    <a href="javascript:void(0)" onclick="showSection('ad_settings')">💰 Ad Settings</a>
    <a href="javascript:void(0)" onclick="showSection('tg_settings')">📢 Telegram Settings</a>
    <a href="javascript:void(0)" onclick="showSection('security')">🔐 Security</a>
    <a href="/logout" style="color:red;">🚪 Logout</a>
    {% else %}
    {% for c in all_categories %}<a href="/category/{{c.name}}">📁 {{c.name}}</a>{% endfor %}
    <a href="/login">🔑 Admin Login</a>
    {% endif %}
</div>
<script>
    function toggleSidebar() {
        document.getElementById('sidebar').classList.toggle('active');
        document.getElementById('overlay').classList.toggle('active');
    }
    function showSection(id) {
        document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        toggleSidebar();
    }
</script>
"""

# --- USER TEMPLATES ---

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
    
    """ + SIDEBAR_HTML + """

    <header class="container">
        <a href="/" class="logo">
            {% if settings.logo_url %}<img src="{{settings.logo_url}}" width="40" style="margin-right:10px;">{% endif %}
            {{ settings.site_name }}
        </a>
    </header>

    <div class="container">
        <form action="/" method="GET" style="text-align:center; margin-bottom:20px;">
            <input type="text" name="search" placeholder="Search movies..." style="width:80%; max-width:400px; border-radius: 20px;">
        </form>

        {% if slider_movies and not is_cat %}
        <div class="slider">
            {% for sm in slider_movies %}
            <div class="slide-item">
                <a href="/movie/{{sm._id}}">
                    <img src="{{sm.thumb}}">
                    <div style="position:absolute; bottom:20px; left:20px;"><h2>{{sm.name}}</h2></div>
                </a>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="ads">{{ settings.ad_banner | safe }}</div>

        {% for cat in categories %}
        <div class="cat-section">
            <div style="display:flex; justify-content:space-between; border-left:4px solid red; padding-left:10px; margin-bottom:15px;">
                <h3 style="margin:0;">{{ cat }}</h3>
                <a href="/category/{{cat}}" style="color:red; text-decoration:none; font-weight:bold;">SEE ALL →</a>
            </div>
            <div class="movie-grid">
                {% for movie in movie_data[cat] %}
                <a href="/movie/{{ movie._id }}" class="movie-card">
                    {% if movie.badge %}<div class="movie-badge">{{ movie.badge }}</div>{% endif %}
                    <img src="{{ movie.thumb }}" style="width:{{settings.thumb_width}}px; height:{{settings.thumb_height}}px; padding:{{settings.thumb_margin}}px">
                    <div class="movie-info"><strong>{{ movie.name }}</strong><br><span style="color:#888;">{{ movie.lang }}</span></div>
                </a>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        
        <div class="ads">{{ settings.ad_social | safe }}</div>
    </div>
    {{ settings.ad_popunder | safe }}
</body>
</html>
"""

DETAIL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ movie.name }}</title>
    """ + BASE_CSS + """
</head>
<body>
    """ + SIDEBAR_HTML + """
    <header class="container"><a href="/" class="logo">{{ settings.site_name }}</a></header>
    <div class="container" style="text-align:center; padding-top:20px;">
        <h1>{{ movie.name }}</h1>
        <div class="ads">{{ settings.ad_banner | safe }}</div>
        
        <!-- মুভি থাম্বনেল প্রদর্শন -->
        <div style="margin-bottom:20px;">
            <img src="{{ movie.thumb }}" style="max-width:100%; height:auto; border-radius:10px; border:1px solid #333; max-height:450px; object-fit:cover;">
        </div>

        <div style="background:#000; padding:15px; border-radius:10px; margin:20px 0; border:1px solid #333;">
            {{ movie.html_code | safe }}
        </div>
        
        <p>Category: {{ movie.cat }} | Language: {{ movie.lang }} {% if movie.badge %}| Quality: {{ movie.badge }}{% endif %}</p>
        <div class="ads">{{ settings.ad_social | safe }}</div>
    </div>
</body>
</html>
"""

# --- ADMIN TEMPLATE ---

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    """ + BASE_CSS + """
</head>
<body style="background:#000;">
    """ + SIDEBAR_HTML + """
    <div class="container" style="padding-top:80px;">
        <h1 style="text-align:center; color:red; text-shadow:0 0 10px red;">ADMIN DASHBOARD</h1>
        
        <!-- Add/Edit Movie -->
        <div id="add_movie" class="admin-section active">
            <div class="input-group">
                <h3>{% if edit_movie %}Edit Movie{% else %}Add New Movie{% endif %}</h3>
                <form action="/admin/save-movie" method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="movie_id" value="{{ edit_movie._id if edit_movie else '' }}">
                    <input type="text" name="name" value="{{ edit_movie.name if edit_movie else '' }}" placeholder="Movie Name" required>
                    
                    <input type="text" name="badge" value="{{ edit_movie.badge if edit_movie else '' }}" placeholder="Movie Badge (e.g. HD, 4K, Dual Audio)">

                    <label>Thumbnail System:</label>
                    <input type="text" name="thumb_url" value="{{ edit_movie.thumb if edit_movie else '' }}" placeholder="Image URL">
                    <p style="text-align:center; margin:5px;">OR Upload from Gallery</p>
                    <input type="file" name="thumb_file">

                    <select name="cat">
                        <option value="">Select Category</option>
                        {% for c in all_categories %}<option value="{{c.name}}" {% if edit_movie and edit_movie.cat == c.name %}selected{% endif %}>{{c.name}}</option>{% endfor %}
                    </select>
                    <input type="text" name="lang" value="{{ edit_movie.lang if edit_movie else '' }}" placeholder="Language (e.g. Hindi)">
                    
                    <label>Player HTML Code (Live Preview Below):</label>
                    <textarea name="html_code" id="hcode" rows="6" oninput="document.getElementById('html-preview').innerHTML = this.value" placeholder="Paste Embed Code">{{ edit_movie.html_code if edit_movie else '' }}</textarea>
                    <div id="html-preview">Preview will appear here...</div>
                    
                    <button type="submit" class="btn" style="margin-top:15px;">Save & Post Movie</button>
                </form>
            </div>
        </div>

        <!-- Movie List -->
        <div id="movie_list" class="admin-section">
            <div class="input-group">
                <h3>Manage Movies</h3>
                <form method="GET" action="/admin"><input type="text" name="search" placeholder="Search..."></form>
                <div style="overflow-x:auto;">
                    <table width="100%" style="border-collapse:collapse;">
                        <tr style="background:#222;"><th>Name</th><th>Action</th></tr>
                        {% for m in movies %}
                        <tr style="border-bottom:1px solid #333; text-align:center;">
                            <td>{{m.name}}</td>
                            <td><a href="/admin?edit_id={{m._id}}" style="color:cyan;">Edit</a> | <a href="/delete/{{m._id}}" style="color:red;" onclick="return confirm('Delete?')">Delete</a></td>
                        </tr>
                        {% endfor %}
                    </table>
                </div>
            </div>
        </div>

        <!-- Category Manage -->
        <div id="cat_manage" class="admin-section">
            <div class="input-group">
                <h3>Manage Categories</h3>
                <form action="/admin/add-cat" method="POST">
                    <input type="text" name="cat_name" placeholder="New Category Name" required>
                    <button type="submit" class="btn">Add Category</button>
                </form>
                <table width="100%" style="margin-top:15px;">
                    {% for c in all_categories %}
                    <tr><td>{{c.name}}</td><td><a href="/admin/del-cat/{{c._id}}" style="color:red;">Delete</a></td></tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <!-- Site Settings -->
        <div id="site_settings" class="admin-section">
            <form action="/admin/settings" method="POST" class="input-group">
                <h3>General Settings</h3>
                Site Name: <input type="text" name="site_name" value="{{ settings.site_name }}">
                Logo URL: <input type="text" name="logo_url" value="{{ settings.logo_url }}">
                Notice Text: <input type="text" name="notice_text" value="{{ settings.notice_text }}">
                Notice BG: <input type="color" name="notice_bg" value="{{ settings.notice_bg }}" style="height:40px;">
                Notice Color: <input type="color" name="notice_color" value="{{ settings.notice_color }}" style="height:40px;">
                Thumb Width: <input type="number" name="thumb_width" value="{{ settings.thumb_width }}">
                Thumb Height: <input type="number" name="thumb_height" value="{{ settings.thumb_height }}">
                Post Limit: <input type="number" name="post_limit" value="{{ settings.post_limit }}">
                <button type="submit" class="btn">Update Site</button>
            </form>
        </div>

        <!-- Ads -->
        <div id="ad_settings" class="admin-section">
            <form action="/admin/settings" method="POST" class="input-group">
                <h3>Ad Codes</h3>
                Banner: <textarea name="ad_banner" rows="4">{{ settings.ad_banner }}</textarea>
                Popunder: <textarea name="ad_popunder" rows="4">{{ settings.ad_popunder }}</textarea>
                Social: <textarea name="ad_social" rows="4">{{ settings.ad_social }}</textarea>
                <button type="submit" class="btn">Save Ads</button>
            </form>
        </div>

        <!-- Telegram -->
        <div id="tg_settings" class="admin-section">
            <form action="/admin/settings" method="POST" class="input-group">
                <h3>Telegram Bot</h3>
                Bot Token: <input type="text" name="tg_token" value="{{ settings.tg_token }}">
                Channel ID: <input type="text" name="tg_chat_id" value="{{ settings.tg_chat_id }}">
                <button type="submit" class="btn">Update Telegram</button>
            </form>
        </div>

        <!-- Security -->
        <div id="security" class="admin-section">
            <form action="/admin/update-auth" method="POST" class="input-group">
                <h3>Admin Security</h3>
                New Username: <input type="text" name="admin_user" value="{{ settings.admin_user }}" required>
                New Password: <input type="text" name="admin_pass" value="{{ settings.admin_pass }}" required>
                <button type="submit" class="btn">Update Credentials</button>
            </form>
        </div>

    </div>
    {% if edit_movie %}<script>showSection('add_movie');</script>{% endif %}
</body>
</html>
"""

# --- BACKEND LOGIC ---

@app.route('/')
def home():
    settings = get_settings()
    search = request.args.get('search')
    all_cats = list(cat_col.find().sort("name", 1))
    cat_names = [c['name'] for c in all_cats]
    
    movie_data = {}
    for cat in cat_names:
        query = {"cat": cat}
        if search: query["name"] = {"$regex": search, "$options": "i"}
        movie_data[cat] = list(movies_col.find(query).sort("_id", -1).limit(int(settings['post_limit'])))
    
    slider_movies = list(movies_col.find().sort("_id", -1).limit(5))
    return render_template_string(HOME_HTML, settings=settings, categories=cat_names, movie_data=movie_data, slider_movies=slider_movies, all_categories=all_cats, is_cat=False)

@app.route('/movie/<id>')
def details(id):
    settings = get_settings()
    movie = movies_col.find_one({"_id": ObjectId(id)})
    all_cats = list(cat_col.find().sort("name", 1))
    return render_template_string(DETAIL_HTML, movie=movie, settings=settings, all_categories=all_cats)

@app.route('/category/<name>')
def category_page(name):
    settings = get_settings()
    movies = list(movies_col.find({"cat": name}).sort("_id", -1))
    all_cats = list(cat_col.find().sort("name", 1))
    return render_template_string(HOME_HTML, settings=settings, categories=[name], movie_data={name: movies}, slider_movies=[], all_categories=all_cats, is_cat=True)

@app.route('/login', methods=['GET', 'POST'])
def login():
    s = get_settings()
    if request.method == 'POST':
        if request.form['user'] == s['admin_user'] and request.form['pass'] == s['admin_pass']:
            session['admin'] = True
            return redirect('/admin')
    return render_template_string("""<body style="background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
    <form method="POST" style="background:#111;padding:40px;border-radius:10px;width:300px;border:1px solid #333;">
    <h2 style="text-align:center;color:red;">ADMIN LOGIN</h2>
    <input type="text" name="user" placeholder="Username" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;">
    <input type="password" name="pass" placeholder="Password" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;">
    <button style="width:100%;padding:10px;background:red;color:#fff;border:none;cursor:pointer;font-weight:bold;">Login</button></form></body>""")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin')
def admin():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    all_cats = list(cat_col.find().sort("name", 1))
    edit_id = request.args.get('edit_id')
    edit_movie = movies_col.find_one({"_id": ObjectId(edit_id)}) if edit_id else None
    
    search = request.args.get('search')
    query = {"name": {"$regex": search, "$options": "i"}} if search else {}
    movies_list = list(movies_col.find(query).sort("_id", -1))
    
    return render_template_string(ADMIN_HTML, settings=settings, all_categories=all_cats, movies=movies_list, edit_movie=edit_movie)

@app.route('/admin/save-movie', methods=['POST'])
def save_movie():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    movie_id = request.form.get('movie_id')
    
    # Thumbnail logic
    thumb = request.form.get('thumb_url')
    if 'thumb_file' in request.files:
        file = request.files['thumb_file']
        if file.filename != '':
            encoded_string = base64.b64encode(file.read()).decode('utf-8')
            thumb = f"data:{file.content_type};base64,{encoded_string}"
        
    data = {
        "name": request.form['name'], 
        "thumb": thumb,
        "badge": request.form.get('badge', ''), # ব্যাজ সেভ করা হচ্ছে
        "lang": request.form['lang'], 
        "cat": request.form['cat'], 
        "html_code": request.form['html_code']
    }
    
    if movie_id:
        movies_col.update_one({"_id": ObjectId(movie_id)}, {"$set": data})
    else:
        new_mov = movies_col.insert_one(data)
        if settings['tg_token'] and settings['tg_chat_id']:
            url = request.host_url + "movie/" + str(new_mov.inserted_id)
            msg = f"🎬 *New Movie Posted!*\n\n⭐ *Name:* {data['name']}\n🌍 *Lang:* {data['lang']}\n📂 *Cat:* {data['cat']}\n🔗 [Watch Now]({url})"
            requests.post(f"https://api.telegram.org/bot{settings['tg_token']}/sendPhoto", 
                          data={"chat_id": settings['tg_chat_id'], "photo": data['thumb'], "caption": msg, "parse_mode": "Markdown"})

    return redirect('/admin')

@app.route('/admin/add-cat', methods=['POST'])
def add_cat():
    if not session.get('admin'): return redirect('/login')
    cat_col.insert_one({"name": request.form['cat_name']})
    return redirect('/admin')

@app.route('/admin/del-cat/<id>')
def del_cat(id):
    if not session.get('admin'): return redirect('/login')
    cat_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('admin'): return redirect('/login')
    settings_col.update_one({}, {"$set": request.form.to_dict()})
    return redirect('/admin')

@app.route('/admin/update-auth', methods=['POST'])
def update_auth():
    if not session.get('admin'): return redirect('/login')
    settings_col.update_one({}, {"$set": {
        "admin_user": request.form['admin_user'],
        "admin_pass": request.form['admin_pass']
    }})
    flash("Security Updated!")
    return redirect('/admin')

@app.route('/delete/<id>')
def delete_movie(id):
    if not session.get('admin'): return redirect('/login')
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
