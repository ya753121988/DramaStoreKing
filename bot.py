import os
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import requests

app = Flask(__name__)
app.secret_key = "ultra_premium_key_99"

# --- MongoDB Setup ---
# এখানে আপনার MongoDB URL বসান
MONGO_URI = "mongodb+srv://admin:admin@cluster0.mongodb.net/movie_db?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client['movie_v3']
movies_col = db['movies']
settings_col = db['settings']
cat_col = db['categories']

# --- ডিফল্ট সেটিংস লোড ---
def get_settings():
    settings = settings_col.find_one()
    if not settings:
        default = {
            "site_name": "PREMIUM-FILM", "logo_url": "", "notice_text": "Welcome to Premium Movie Hub",
            "notice_bg": "#ff0000", "notice_color": "#ffffff", "thumb_width": "280", "thumb_height": "160",
            "thumb_margin": "10", "tg_token": "", "tg_chat_id": "", "post_limit": 5, 
            "ad_banner": "", "ad_popunder": "", "ad_social": ""
        }
        settings_col.insert_one(default)
        return default
    return settings

# --- CSS Design (User & Admin) ---
BASE_CSS = """
<style>
    :root { --primary: #e50914; --dark: #080808; --card: #121212; --text: #ffffff; }
    body { background: var(--dark); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; }
    
    /* Rainbow Logo */
    @keyframes rainbow { 0%{color:#ff0000} 15%{color:#ff8800} 30%{color:#ffff00} 45%{color:#00ff00} 60%{color:#00ffff} 75%{color:#0000ff} 90%{color:#8800ff} 100%{color:#ff0000} }
    .logo { font-size: 26px; font-weight: 800; animation: rainbow 4s infinite; text-decoration: none; display: flex; align-items: center; justify-content: center; padding: 15px; }

    .notice-bar { padding: 10px; text-align: center; font-size: 14px; font-weight: bold; }
    .container { width: 95%; max-width: 1400px; margin: auto; }

    /* Slider */
    .slider { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding: 10px 0; scrollbar-width: none; }
    .slider::-webkit-scrollbar { display: none; }
    .slide-item { flex: 0 0 80%; scroll-snap-align: start; position: relative; border-radius: 15px; overflow: hidden; height: 250px; }
    .slide-item img { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.6); }
    .slide-info { position: absolute; bottom: 20px; left: 20px; }

    /* Movie Grid */
    .cat-section { margin-top: 30px; }
    .cat-header { display: flex; justify-content: space-between; border-left: 4px solid var(--primary); padding-left: 10px; margin-bottom: 15px; }
    .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; }
    .movie-card { background: var(--card); border-radius: 8px; overflow: hidden; text-decoration: none; color: #fff; transition: 0.3s; }
    .movie-card:hover { transform: scale(1.03); box-shadow: 0 0 15px var(--primary); }
    .movie-card img { width: 100%; object-fit: cover; }
    .movie-info { padding: 8px; text-align: center; font-size: 13px; }

    /* Admin 3-Dot Menu & Layout */
    .admin-nav { background: #111; padding: 15px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 1000; }
    .three-dot-menu { position: relative; cursor: pointer; font-size: 24px; }
    .menu-dropdown { display: none; position: absolute; right: 0; top: 35px; background: #1a1a1a; min-width: 200px; box-shadow: 0 0 10px #000; border-radius: 8px; overflow: hidden; }
    .menu-dropdown a { display: block; padding: 12px 20px; color: white; text-decoration: none; border-bottom: 1px solid #333; }
    .menu-dropdown a:hover { background: var(--primary); }
    .admin-section { display: none; padding: 20px; }
    .admin-section.active { display: block; }
    
    .input-group { background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    input, textarea, select { width: 100%; padding: 12px; margin: 8px 0; border-radius: 5px; border: 1px solid #333; background: #000; color: #fff; }
    .btn { background: var(--primary); color: #fff; border: none; padding: 12px 20px; cursor: pointer; border-radius: 5px; font-weight: bold; }

    @media (max-width: 600px) { .movie-grid { grid-template-columns: repeat(2, 1fr); } .slide-item { flex: 0 0 95%; } }
</style>
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
    
    <header class="container">
        <a href="/" class="logo">
            {% if settings.logo_url %}<img src="{{settings.logo_url}}" width="40" style="margin-right:10px;">{% endif %}
            {{ settings.site_name }}
        </a>
    </header>

    <div class="container">
        <!-- Search Box -->
        <form action="/" method="GET" style="text-align:center; margin-bottom:20px;">
            <input type="text" name="search" placeholder="Search movies..." style="width:70%; max-width:400px; border-radius: 20px;">
        </form>

        <!-- Slider -->
        {% if slider_movies %}
        <div class="slider">
            {% for sm in slider_movies %}
            <div class="slide-item">
                <a href="/movie/{{sm._id}}"><img src="{{sm.thumb}}"></a>
                <div class="slide-info"><h2>{{sm.name}}</h2></div>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="ads">{{ settings.ad_banner | safe }}</div>

        <!-- Categorized Movies -->
        {% for cat in categories %}
        <div class="cat-section">
            <div class="cat-header">
                <h3>{{ cat }}</h3>
                <a href="/category/{{cat}}" style="color:var(--primary); text-decoration:none;">See More &rarr;</a>
            </div>
            <div class="movie-grid">
                {% for movie in movie_data[cat] %}
                <a href="/movie/{{ movie._id }}" class="movie-card">
                    <img src="{{ movie.thumb }}" style="width:{{settings.thumb_width}}px; height:{{settings.thumb_height}}px; padding:{{settings.thumb_margin}}px">
                    <div class="movie-info">{{ movie.name }} <br> <span style="color:#aaa;">{{ movie.lang }}</span></div>
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
    <header class="container"><a href="/" class="logo">{{ settings.site_name }}</a></header>
    <div class="container" style="text-align:center;">
        <h1>{{ movie.name }}</h1>
        <div class="ads">{{ settings.ad_banner | safe }}</div>
        
        <div style="background:#000; padding:10px; border-radius:10px; margin:20px 0;">
            {{ movie.html_code | safe }}
        </div>
        
        <p>Category: {{ movie.cat }} | Language: {{ movie.lang }}</p>
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
    <title>Admin Dashboard</title>
    """ + BASE_CSS + """
    <script>
        function toggleMenu() {
            var m = document.getElementById('menuDropdown');
            m.style.display = (m.style.display === 'block') ? 'none' : 'block';
        }
        function showSection(id) {
            document.querySelectorAll('.admin-section').forEach(s => s.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            document.getElementById('menuDropdown').style.display = 'none';
        }
    </script>
</head>
<body style="background:#000;">
    <nav class="admin-nav">
        <div class="logo">{{ settings.site_name }} Admin</div>
        <div class="three-dot-menu" onclick="toggleMenu()">
            ⋮
            <div id="menuDropdown" class="menu-dropdown">
                <a href="javascript:void(0)" onclick="showSection('add_movie')">➕ Add Movie</a>
                <a href="javascript:void(0)" onclick="showSection('movie_list')">🎬 Manage Movies</a>
                <a href="javascript:void(0)" onclick="showSection('site_settings')">⚙️ Site Settings</a>
                <a href="javascript:void(0)" onclick="showSection('ad_settings')">💰 Ad Settings</a>
                <a href="javascript:void(0)" onclick="showSection('tg_settings')">📢 Telegram Settings</a>
                <a href="/logout" style="color:red;">🚪 Logout</a>
            </div>
        </div>
    </nav>

    <div class="container">
        
        <!-- Add/Edit Movie Section -->
        <div id="add_movie" class="admin-section active">
            <h2>{% if edit_movie %}Edit Movie{% else %}Add New Movie{% endif %}</h2>
            <form action="/admin/save-movie" method="POST" class="input-group">
                <input type="hidden" name="movie_id" value="{{ edit_movie._id if edit_movie else '' }}">
                <input type="text" name="name" value="{{ edit_movie.name if edit_movie else '' }}" placeholder="Movie Name" required>
                <input type="text" name="thumb" value="{{ edit_movie.thumb if edit_movie else '' }}" placeholder="Landscape Thumbnail URL" required>
                <input type="text" name="lang" value="{{ edit_movie.lang if edit_movie else '' }}" placeholder="Language (e.g. Hindi)">
                <select name="cat">
                    <option value="">Select Category</option>
                    {% for c in categories %}<option value="{{c}}" {% if edit_movie and edit_movie.cat == c %}selected{% endif %}>{{c}}</option>{% endfor %}
                </select>
                <input type="text" name="new_cat" placeholder="OR Create New Category">
                <textarea name="html_code" rows="6" placeholder="Paste HTML Player/Embed Code">{{ edit_movie.html_code if edit_movie else '' }}</textarea>
                <button type="submit" class="btn">Save Movie</button>
            </form>
        </div>

        <!-- Movie List Section -->
        <div id="movie_list" class="admin-section">
            <h2>Manage Movies</h2>
            <form method="GET" action="/admin"><input type="text" name="search" placeholder="Search to edit/delete..."></form>
            <div style="overflow-x:auto;">
                <table width="100%" style="border-collapse:collapse; background:#111;">
                    <tr style="background:#222;">
                        <th style="padding:10px;">Thumb</th><th>Name</th><th>Action</th>
                    </tr>
                    {% for m in movies %}
                    <tr style="border-bottom:1px solid #333; text-align:center;">
                        <td><img src="{{m.thumb}}" width="60"></td>
                        <td>{{m.name}}</td>
                        <td>
                            <a href="/admin?edit_id={{m._id}}" style="color:cyan;">Edit</a> | 
                            <a href="/delete/{{m._id}}" style="color:red;" onclick="return confirm('Sure?')">Delete</a>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>

        <!-- Site Settings -->
        <div id="site_settings" class="admin-section">
            <h2>Site Settings</h2>
            <form action="/admin/settings" method="POST" class="input-group">
                <input type="text" name="site_name" value="{{ settings.site_name }}" placeholder="Site Name">
                <input type="text" name="logo_url" value="{{ settings.logo_url }}" placeholder="Logo URL">
                <input type="text" name="notice_text" value="{{ settings.notice_text }}" placeholder="Notice Text">
                <input type="color" name="notice_bg" value="{{ settings.notice_bg }}">
                <input type="number" name="thumb_width" value="{{ settings.thumb_width }}" placeholder="Thumb Width">
                <input type="number" name="thumb_height" value="{{ settings.thumb_height }}" placeholder="Thumb Height">
                <input type="number" name="post_limit" value="{{ settings.post_limit }}" placeholder="Post Limit per Category">
                <button type="submit" class="btn">Update Site</button>
            </form>
        </div>

        <!-- Ad Settings -->
        <div id="ad_settings" class="admin-section">
            <h2>Ad Management</h2>
            <form action="/admin/settings" method="POST" class="input-group">
                <textarea name="ad_banner" placeholder="Banner Ad HTML Code">{{ settings.ad_banner }}</textarea>
                <textarea name="ad_popunder" placeholder="Popunder Ad Script">{{ settings.ad_popunder }}</textarea>
                <textarea name="ad_social" placeholder="Social Bar Ad HTML">{{ settings.ad_social }}</textarea>
                <button type="submit" class="btn">Save Ads</button>
            </form>
        </div>

        <!-- Telegram Settings -->
        <div id="tg_settings" class="admin-section">
            <h2>Telegram Bot Automation</h2>
            <form action="/admin/settings" method="POST" class="input-group">
                <input type="text" name="tg_token" value="{{ settings.tg_token }}" placeholder="Bot Token">
                <input type="text" name="tg_chat_id" value="{{ settings.tg_chat_id }}" placeholder="Channel ID (@username or ID)">
                <button type="submit" class="btn">Save Telegram Config</button>
            </form>
        </div>

    </div>

    {% if edit_movie %} <script>showSection('add_movie');</script> {% endif %}
</body>
</html>
"""

# --- BACKEND LOGIC ---

@app.route('/')
def home():
    settings = get_settings()
    search = request.args.get('search')
    categories = [c['name'] for c in cat_col.find().sort("name", 1)]
    
    movie_data = {}
    for cat in categories:
        query = {"cat": cat}
        if search: query["name"] = {"$regex": search, "$options": "i"}
        movie_data[cat] = list(movies_col.find(query).sort("name", 1).limit(int(settings['post_limit'])))
    
    slider_movies = list(movies_col.find().sort("_id", -1).limit(5))
    return render_template_string(HOME_HTML, settings=settings, categories=categories, movie_data=movie_data, slider_movies=slider_movies)

@app.route('/movie/<id>')
def details(id):
    settings = get_settings()
    movie = movies_col.find_one({"_id": ObjectId(id)})
    return render_template_string(DETAIL_HTML, movie=movie, settings=settings)

@app.route('/category/<name>')
def category_page(name):
    settings = get_settings()
    movies = list(movies_col.find({"cat": name}).sort("name", 1))
    return render_template_string(HOME_HTML, settings=settings, categories=[name], movie_data={name: movies}, slider_movies=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['user'] == 'admin' and request.form['pass'] == 'admin':
            session['admin'] = True
            return redirect('/admin')
    return render_template_string("""<body style="background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
    <form method="POST" style="background:#111;padding:40px;border-radius:10px;width:300px;">
    <h2 style="text-align:center;">Admin Login</h2>
    <input type="text" name="user" placeholder="Username" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;">
    <input type="password" name="pass" placeholder="Password" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;">
    <button style="width:100%;padding:10px;background:red;color:#fff;border:none;cursor:pointer;">Login</button></form></body>""")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/admin')
def admin():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    categories = [c['name'] for c in cat_col.find().sort("name", 1)]
    edit_id = request.args.get('edit_id')
    edit_movie = movies_col.find_one({"_id": ObjectId(edit_id)}) if edit_id else None
    
    search = request.args.get('search')
    query = {"name": {"$regex": search, "$options": "i"}} if search else {}
    movies = list(movies_col.find(query).sort("_id", -1))
    
    return render_template_string(ADMIN_HTML, settings=settings, categories=categories, movies=movies, edit_movie=edit_movie)

@app.route('/admin/save-movie', methods=['POST'])
def save_movie():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    movie_id = request.form.get('movie_id')
    category = request.form.get('new_cat') or request.form.get('cat')
    
    if category and not cat_col.find_one({"name": category}):
        cat_col.insert_one({"name": category})
        
    data = {
        "name": request.form['name'], "thumb": request.form['thumb'],
        "lang": request.form['lang'], "cat": category, "html_code": request.form['html_code']
    }
    
    if movie_id:
        movies_col.update_one({"_id": ObjectId(movie_id)}, {"$set": data})
    else:
        new_mov = movies_col.insert_one(data)
        # Telegram Bot Notify
        if settings['tg_token'] and settings['tg_chat_id']:
            url = request.host_url + "movie/" + str(new_mov.inserted_id)
            msg = f"🎬 *New Movie Posted!*\n\n⭐ *Name:* {data['name']}\n📂 *Cat:* {data['cat']}\n\n🔗 [Watch Now]({url})"
            requests.post(f"https://api.telegram.org/bot{settings['tg_token']}/sendPhoto", 
                          data={"chat_id": settings['tg_chat_id'], "photo": data['thumb'], "caption": msg, "parse_mode": "Markdown"})

    return redirect('/admin')

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('admin'): return redirect('/login')
    form_data = request.form.to_dict()
    settings_col.update_one({}, {"$set": form_data})
    return redirect('/admin')

@app.route('/delete/<id>')
def delete_movie(id):
    if not session.get('admin'): return redirect('/login')
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
