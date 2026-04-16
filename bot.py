import os
import requests
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "ULTRA_FINAL_SECRET_KEY_99"

# --- CONFIGURATION FOR UPLOADS ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- MongoDB Setup ---
# এখানে আপনার মঙ্গোডিবি ইউআরএল বসান
MONGO_URI = "mongodb+srv://roxiw19528:roxiw19528@cluster0.vl508y4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['movie_v6_final']
movies_col = db['movies']
settings_col = db['settings']
cat_col = db['categories']

# --- ডিফল্ট সেটিংস ফাংশন ---
def get_settings():
    settings = settings_col.find_one()
    if not settings:
        default = {
            "site_name": "PREMIUM-CINEMA", "logo_url": "", 
            "notice_text": "আমাদের ওয়েবসাইটে স্বাগতম!", "notice_bg": "#ff0000", "notice_color": "#ffffff", 
            "thumb_width": "280", "thumb_height": "160", "thumb_p_top": "10", "thumb_p_bottom": "10",
            "thumb_p_left": "10", "thumb_p_right": "10", "post_limit": 6, 
            "ad_banner": "", "ad_popunder": "", "ad_social": "",
            "tg_token": "", "tg_chat_id": "",
            "admin_user": "admin", "admin_pass": "admin"
        }
        settings_col.insert_one(default)
        return default
    return settings

# --- CSS Design (একদম প্রিমিয়াম লুক) ---
BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    :root { --primary: #e50914; --bg: #050505; --card: #121212; --text: #ffffff; }
    body { background: var(--bg); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; }
    
    /* ৭ কালার লোগো এনিমেশন */
    @keyframes rainbow { 
        0%{color:#ff0000} 14%{color:#ff8800} 28%{color:#ffff00} 
        42%{color:#00ff00} 57%{color:#00ffff} 71%{color:#0000ff} 
        85%{color:#8800ff} 100%{color:#ff0000} 
    }
    .logo { font-size: 28px; font-weight: 800; animation: rainbow 5s infinite; text-decoration: none; display: flex; align-items: center; justify-content: center; padding: 15px; }

    .notice-bar { padding: 10px; text-align: center; font-size: 14px; font-weight: bold; position: sticky; top: 0; z-index: 1001; overflow: hidden; }
    .container { width: 95%; max-width: 1400px; margin: auto; padding-bottom: 50px; }

    /* প্রিমিয়াম সাইডবার */
    .sidebar { width: 260px; height: 100vh; background: #111; position: fixed; left: -260px; top: 0; transition: 0.4s; z-index: 2000; border-right: 1px solid #222; }
    .sidebar.active { left: 0; }
    .sidebar-header { padding: 20px; border-bottom: 1px solid #222; font-weight: bold; color: var(--primary); text-align:center; font-size: 20px; }
    .sidebar a { display: block; padding: 15px 20px; color: #ccc; text-decoration: none; border-bottom: 1px solid #1a1a1a; }
    .sidebar a:hover { background: #222; color: var(--primary); padding-left: 30px; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1999; }
    .overlay.active { display: block; }
    .menu-btn { cursor: pointer; font-size: 25px; color: #fff; position: fixed; top: 45px; left: 15px; z-index: 1002; background: var(--primary); width: 45px; height: 45px; line-height: 45px; text-align: center; border-radius: 50%; }

    /* মুভি গ্রিড */
    .cat-section { margin-top: 40px; }
    .cat-header { display: flex; justify-content: space-between; align-items: center; border-left: 5px solid var(--primary); padding-left: 15px; margin-bottom: 20px; }
    .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }
    .movie-card { background: var(--card); border-radius: 12px; overflow: hidden; text-decoration: none; color: #fff; transition: 0.3s; border: 1px solid #222; text-align: center; }
    .movie-card:hover { transform: translateY(-8px); border-color: var(--primary); }
    .movie-card img { width: 100%; object-fit: cover; }

    /* এডমিন প্যানেল */
    .admin-card { background: #111; padding: 20px; border-radius: 15px; margin-bottom: 20px; border: 1px solid #333; }
    input, textarea, select { width: 100%; padding: 12px; margin: 10px 0; border-radius: 8px; border: 1px solid #333; background: #000; color: #fff; box-sizing: border-box; }
    .btn { background: var(--primary); color: #fff; border: none; padding: 12px 25px; cursor: pointer; border-radius: 8px; font-weight: bold; width: 100%; }
    
    /* এইচটিএমএল প্রিভিউ */
    #preview-box { background: #000; border: 2px dashed #444; padding: 10px; min-height: 100px; border-radius: 10px; margin-top: 10px; }

    @media (max-width: 768px) { .movie-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; } .sidebar { width: 220px; } }
</style>
"""

# --- কম্পোনেন্ট: নেভিগেশন ---
NAV_HTML = """
<div class="menu-btn" onclick="toggleSidebar()">☰</div>
<div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
<div class="sidebar" id="sidebar">
    <div class="sidebar-header">NAV MENU</div>
    <a href="/">🏠 Home</a>
    {% if session.admin %}
    <a href="/admin">📊 Dashboard</a>
    <a href="/admin/category">📂 Categories</a>
    <a href="/admin/settings">⚙️ Site Settings</a>
    <a href="/admin/ads">💰 Ad Settings</a>
    <a href="/admin/security">🔐 Security</a>
    <a href="/logout" style="color:red;">🚪 Logout</a>
    {% else %}
    {% for c in all_cats %}<a href="/category/{{c.name}}">📁 {{c.name}}</a>{% endfor %}
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

# --- ইউজার টেমপ্লেট ---
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
    """ + NAV_HTML + """
    <header class="container">
        <a href="/" class="logo">
            {% if settings.logo_url %}<img src="{{settings.logo_url}}" width="40" style="margin-right:10px;">{% endif %}
            {{ settings.site_name }}
        </a>
        <form action="/" method="GET" style="text-align:center;"><input type="text" name="search" placeholder="Search movies..." style="width:80%; max-width:400px; border-radius:30px; text-align:center; border:1px solid var(--primary);"></form>
    </header>

    <div class="container">
        <div style="text-align:center;">{{ settings.ad_banner | safe }}</div>
        {% for cat in display_cats %}
        <div class="cat-section">
            <div class="cat-header">
                <h2 style="margin:0;">{{ cat }}</h2>
                <a href="/category/{{cat}}" style="color:red; text-decoration:none; font-weight:bold;">SEE MORE →</a>
            </div>
            <div class="movie-grid">
                {% for movie in movie_data[cat] %}
                <a href="/movie/{{ movie._id }}" class="movie-card" style="padding: {{settings.thumb_p_top}}px {{settings.thumb_p_right}}px {{settings.thumb_p_bottom}}px {{settings.thumb_p_left}}px;">
                    <img src="{{ movie.thumb }}" style="width:{{settings.thumb_width}}px; height:{{settings.thumb_height}}px; border-radius:8px;">
                    <div style="padding:10px;">{{ movie.name }} <br><small style="color:red;">{{ movie.lang }}</small></div>
                </a>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        <div style="text-align:center; margin-top:20px;">{{ settings.ad_social | safe }}</div>
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
    """ + NAV_HTML + """
    <div class="container" style="text-align:center; padding-top:80px;">
        <h1 style="color:red;">{{ movie.name }}</h1>
        <div class="ads">{{ settings.ad_banner | safe }}</div>
        <div style="background:#000; padding:15px; border-radius:15px; border:1px solid #333; margin:20px 0;">
            {{ movie.html_code | safe }}
        </div>
        <p>Category: {{ movie.cat }} | Language: {{ movie.lang }}</p>
        <div class="ads">{{ settings.ad_social | safe }}</div>
    </div>
    {{ settings.ad_popunder | safe }}
</body>
</html>
"""

# --- এডমিন টেমপ্লেট ---
ADMIN_WRAPPER = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    """ + BASE_CSS + """
</head>
<body>
    """ + NAV_HTML + """
    <div class="container" style="margin-top:80px;">
        <h1 style="text-align:center; color:red;">ADMIN SYSTEM</h1>
        {{ content | safe }}
    </div>
</body>
</html>
"""

# --- ব্যাকএন্ড লজিক ---

@app.route('/')
def home():
    settings = get_settings()
    search = request.args.get('search')
    all_cats = list(cat_col.find().sort("name", 1))
    movie_data = {}
    display_cats = [c['name'] for c in all_cats]
    for cat in display_cats:
        query = {"cat": cat}
        if search: query["name"] = {"$regex": search, "$options": "i"}
        movie_data[cat] = list(movies_col.find(query).sort("name", 1).limit(int(settings['post_limit'])))
    return render_template_string(HOME_HTML, settings=settings, display_cats=display_cats, movie_data=movie_data, all_cats=all_cats)

@app.route('/movie/<id>')
def details(id):
    settings = get_settings()
    movie = movies_col.find_one({"_id": ObjectId(id)})
    all_cats = list(cat_col.find().sort("name", 1))
    return render_template_string(DETAIL_HTML, movie=movie, settings=settings, all_cats=all_cats)

@app.route('/category/<name>')
def category_page(name):
    settings = get_settings()
    movies = list(movies_col.find({"cat": name}).sort("name", 1))
    all_cats = list(cat_col.find().sort("name", 1))
    return render_template_string(HOME_HTML, settings=settings, display_cats=[name], movie_data={name: movies}, all_cats=all_cats)

@app.route('/admin')
def admin_dash():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    all_cats = list(cat_col.find().sort("name", 1))
    edit_id = request.args.get('edit_id')
    edit_movie = movies_col.find_one({"_id": ObjectId(edit_id)}) if edit_id else None
    
    search = request.args.get('search')
    mq = {"name": {"$regex": search, "$options": "i"}} if search else {}
    movies_list = list(movies_col.find(mq).sort("_id", -1))

    content = f"""
    <div class="admin-card">
        <h3>{'Edit' if edit_movie else 'Add New'} Movie</h3>
        <form action="/admin/save-movie" method="POST" enctype="multipart/form-data">
            <input type="hidden" name="movie_id" value="{edit_movie['_id'] if edit_movie else ''}">
            <input type="text" name="name" value="{edit_movie['name'] if edit_movie else ''}" placeholder="Movie Name" required>
            
            <label>Thumbnail (URL or Upload):</label>
            <input type="text" name="thumb_url" value="{edit_movie['thumb'] if edit_movie else ''}" placeholder="Image URL">
            <input type="file" name="thumb_file">

            <select name="cat" required>
                <option value="">Select Category</option>
                {" ".join([f'<option value="{c["name"]}" {"selected" if edit_movie and edit_movie["cat"]==c["name"] else ""}>{c["name"]}</option>' for c in all_cats])}
            </select>
            <input type="text" name="lang" value="{edit_movie['lang'] if edit_movie else ''}" placeholder="Language">
            
            <textarea name="html_code" id="hcode" rows="6" oninput="document.getElementById('preview-box').innerHTML=this.value" placeholder="HTML Player Code">{edit_movie['html_code'] if edit_movie else ''}</textarea>
            <div id="preview-box">Preview will appear here...</div>
            
            <button class="btn" style="margin-top:15px;">SAVE MOVIE</button>
        </form>
    </div>

    <div class="admin-card">
        <h3>Manage Movies</h3>
        <form method="GET"><input type="text" name="search" placeholder="Search..."></form>
        <table width="100%">
            {"".join([f"<tr><td>{m['name']}</td><td><a href='/admin?edit_id={m['_id']}'>Edit</a> | <a href='/delete/{m['_id']}'>Delete</a></td></tr>" for m in movies_list])}
        </table>
    </div>
    """
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_cats=all_cats)

@app.route('/admin/save-movie', methods=['POST'])
def save_movie():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    movie_id = request.form.get('movie_id')
    thumb = request.form.get('thumb_url')
    
    if 'thumb_file' in request.files:
        file = request.files['thumb_file']
        if file.filename != '':
            fn = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
            thumb = '/static/uploads/' + fn

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
            msg = f"🎬 *New Movie:* {data['name']}\n📂 *Cat:* {data['cat']}\n🔗 [Watch Now]({url})"
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
    content = f"""<div class="admin-card"><h3>Categories</h3><form method="POST"><input name="cat_name" placeholder="New Category"><button class="btn">Add</button></form>
    <table width="100%">{"".join([f"<tr><td>{c['name']}</td><td><a href='/admin/cat/del/{c['_id']}'>Delete</a></td></tr>" for c in all_cats])}</table></div>"""
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_cats=all_cats)

@app.route('/admin/cat/del/<id>')
def del_cat(id):
    cat_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin/category')

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    if request.method == 'POST':
        settings_col.update_one({}, {"$set": request.form.to_dict()})
        return redirect('/admin/settings')
    
    content = f"""<div class="admin-card"><h3>Site Settings</h3><form method="POST">
    Site Name: <input name="site_name" value="{settings['site_name']}">
    Logo URL: <input name="logo_url" value="{settings['logo_url']}">
    Notice: <input name="notice_text" value="{settings['notice_text']}">
    Notice BG: <input type="color" name="notice_bg" value="{settings['notice_bg']}">
    Notice Color: <input type="color" name="notice_color" value="{settings['notice_color']}">
    Thumb Width: <input name="thumb_width" value="{settings['thumb_width']}">
    Thumb Height: <input name="thumb_height" value="{settings['thumb_height']}">
    Padding (Top/Bottom/Left/Right): 
    <input name="thumb_p_top" value="{settings['thumb_p_top']}" style="width:20%">
    <input name="thumb_p_bottom" value="{settings['thumb_p_bottom']}" style="width:20%">
    <input name="thumb_p_left" value="{settings['thumb_p_left']}" style="width:20%">
    <input name="thumb_p_right" value="{settings['thumb_p_right']}" style="width:20%">
    Home Post Limit: <input name="post_limit" value="{settings['post_limit']}">
    <button class="btn">Update</button></form></div>"""
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_cats=list(cat_col.find()))

@app.route('/admin/ads', methods=['GET', 'POST'])
def admin_ads():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    if request.method == 'POST':
        settings_col.update_one({}, {"$set": request.form.to_dict()})
        return redirect('/admin/ads')
    content = f"""<div class="admin-card"><h3>Ads Control</h3><form method="POST">
    Banner Ad: <textarea name="ad_banner">{settings['ad_banner']}</textarea>
    Popunder Script: <textarea name="ad_popunder">{settings['ad_popunder']}</textarea>
    Social Bar Ad: <textarea name="ad_social">{settings['ad_social']}</textarea>
    Telegram Token: <input name="tg_token" value="{settings['tg_token']}">
    Telegram Chat ID: <input name="tg_chat_id" value="{settings['tg_chat_id']}">
    <button class="btn">Save Ads & TG</button></form></div>"""
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_cats=list(cat_col.find()))

@app.route('/admin/security', methods=['GET', 'POST'])
def admin_security():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    if request.method == 'POST':
        settings_col.update_one({}, {"$set": {"admin_user": request.form['admin_user'], "admin_pass": request.form['admin_pass']}})
        flash("Admin Security Updated!")
        return redirect('/admin/security')
    content = f"""<div class="admin-card"><h3>Security</h3><form method="POST">
    User: <input name="admin_user" value="{settings['admin_user']}">
    Pass: <input name="admin_pass" value="{settings['admin_pass']}">
    <button class="btn">Change Access</button></form></div>"""
    return render_template_string(ADMIN_WRAPPER, settings=settings, content=content, all_cats=list(cat_col.find()))

@app.route('/login', methods=['GET', 'POST'])
def login():
    s = get_settings()
    if request.method == 'POST':
        if request.form['user'] == s['admin_user'] and request.form['pass'] == s['admin_pass']:
            session['admin'] = True
            return redirect('/admin')
    return render_template_string("""<body style="background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
    <form method="POST" style="background:#111;padding:40px;border-radius:15px;width:300px;">
    <h2 style="text-align:center;">ADMIN</h2><input type="text" name="user" placeholder="User" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;"><input type="password" name="pass" placeholder="Pass" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;"><button style="width:100%;padding:10px;background:red;color:#fff;border:none;cursor:pointer;">LOGIN</button></form></body>""")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/delete/<id>')
def delete_movie(id):
    if not session.get('admin'): return redirect('/login')
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
