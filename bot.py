import os
import requests
import base64
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "ULTRA_FINAL_MONGO_IMAGE_KEY"

# --- MongoDB Setup ---
# আপনার মঙ্গোডিবি ইউআরএল
MONGO_URI = "mongodb+srv://roxiw19528:roxiw19528@cluster0.vl508y4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
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
            "p_top": "10", "p_bottom": "10", "p_left": "10", "p_right": "10", 
            "tg_token": "", "tg_chat_id": "", "post_limit": 5, 
            "ad_banner": "", "ad_popunder": "", "ad_social": "",
            "admin_user": "admin", "admin_pass": "admin"
        }
        settings_col.insert_one(default)
        return default
    return settings

# --- CSS Design (Premium Look with Sidebar) ---
BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    :root { --primary: #e50914; --dark: #080808; --card: #121212; --text: #ffffff; }
    body { background: var(--dark); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; overflow-x: hidden; }
    
    /* ৭ কালার লোগো এনিমেশন */
    @keyframes rainbow { 0%{color:#f00} 14%{color:#f80} 28%{color:#ff0} 42%{color:#0f0} 57%{color:#0ff} 71%{color:#00f} 85%{color:#80f} 100%{color:#f00} }
    .logo { font-size: 26px; font-weight: 800; animation: rainbow 4s infinite; text-decoration: none; display: flex; align-items: center; justify-content: center; padding: 15px; }

    .notice-bar { padding: 10px; text-align: center; font-size: 14px; font-weight: bold; }
    .container { width: 95%; max-width: 1400px; margin: auto; padding-bottom: 50px; }

    /* সাইডবার মেনু */
    .sidebar { position: fixed; left: -280px; top: 0; height: 100%; width: 280px; background: #111; transition: 0.3s; z-index: 1001; border-right: 1px solid #333; }
    .sidebar.active { left: 0; }
    .sidebar-header { padding: 20px; border-bottom: 1px solid #333; font-weight: bold; color: var(--primary); font-size: 20px; text-align: center; }
    .sidebar a { display: block; padding: 15px 20px; color: white; text-decoration: none; border-bottom: 1px solid #222; }
    .sidebar a:hover { background: var(--primary); padding-left: 30px; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; }
    .overlay.active { display: block; }
    .menu-trigger { cursor: pointer; font-size: 25px; color: #fff; position: fixed; top: 45px; left: 15px; z-index: 1002; background: var(--primary); width: 45px; height: 45px; line-height: 45px; text-align: center; border-radius: 5px; }

    /* মুভি গ্রিড এবং থাম্বনেল কন্ট্রোল */
    .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 20px; }
    .movie-card { background: var(--card); border-radius: 8px; overflow: hidden; text-decoration: none; color: #fff; transition: 0.3s; border: 1px solid #222; text-align: center; }
    .movie-card:hover { transform: translateY(-5px); border-color: var(--primary); }

    /* এডমিন UI */
    .admin-box { background: #111; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; }
    input, textarea, select { width: 100%; padding: 12px; margin: 8px 0; border-radius: 6px; border: 1px solid #333; background: #000; color: #fff; box-sizing: border-box; }
    .btn { background: var(--primary); color: #fff; border: none; padding: 12px 25px; cursor: pointer; border-radius: 6px; font-weight: bold; width: 100%; }
    #html-preview { background: #000; border: 1px dashed #555; padding: 10px; margin-top: 10px; min-height: 80px; border-radius: 10px; }

    @media (max-width: 600px) { .movie-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; } .sidebar { width: 220px; } }
</style>
"""

NAV_HTML = """
<div class="menu-trigger" onclick="toggleSidebar()">☰</div>
<div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
<div class="sidebar" id="sidebar">
    <div class="sidebar-header">NAV MENU</div>
    <a href="/">🏠 Home</a>
    {% if session.admin %}
    <a href="javascript:void(0)" onclick="showSection('add_movie')">➕ Add Movie</a>
    <a href="javascript:void(0)" onclick="showSection('movie_list')">🎬 Manage Movies</a>
    <a href="javascript:void(0)" onclick="showSection('cat_manage')">📂 Categories</a>
    <a href="javascript:void(0)" onclick="showSection('site_settings')">⚙️ Settings</a>
    <a href="javascript:void(0)" onclick="showSection('security')">🔐 Security</a>
    <a href="/logout" style="color:red;">🚪 Logout</a>
    {% else %}
    {% for c in all_cats %}<a href="/category/{{c.name}}">📁 {{c.name}}</a>{% endfor %}
    <a href="/login">🔑 Login</a>
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

HOME_HTML = """
<!DOCTYPE html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{{ settings.site_name }}</title>""" + BASE_CSS + """</head>
<body>
    <div class="notice-bar" style="background:{{ settings.notice_bg }}; color:{{ settings.notice_color }};">
        <marquee>{{ settings.notice_text }}</marquee>
    </div>
    """ + NAV_HTML + """
    <header class="container">
        <a href="/" class="logo">{{ settings.site_name }}</a>
        <form action="/" method="GET" style="text-align:center;"><input type="text" name="search" placeholder="Search..." style="width:80%; max-width:400px; border-radius:20px; text-align:center;"></form>
    </header>

    <div class="container">
        <div class="ads">{{ settings.ad_banner | safe }}</div>
        {% for cat in display_cats %}
        <div style="display:flex; justify-content:space-between; border-left:4px solid red; padding-left:10px; margin:30px 0 15px;">
            <h3>{{ cat }}</h3><a href="/category/{{cat}}" style="color:red; text-decoration:none;">SEE ALL →</a>
        </div>
        <div class="movie-grid">
            {% for m in movie_data[cat] %}
            <a href="/movie/{{ m._id }}" class="movie-card" style="padding:{{settings.p_top}}px {{settings.p_right}}px {{settings.p_bottom}}px {{settings.p_left}}px;">
                <img src="{{ m.thumb }}" style="width:{{settings.thumb_width}}px; height:{{settings.thumb_height}}px; object-fit:cover; border-radius:8px;">
                <div style="padding:10px;">{{ m.name }}<br><small style="color:red;">{{ m.lang }}</small></div>
            </a>
            {% endfor %}
        </div>
        {% endfor %}
        <div class="ads">{{ settings.ad_social | safe }}</div>
    </div>
    {{ settings.ad_popunder | safe }}
</body>
</html>
"""

# --- BACKEND LOGIC ---

@app.route('/')
def home():
    settings = get_settings()
    search = request.args.get('search')
    all_cats = list(cat_col.find().sort("name", 1))
    display_cats = [c['name'] for c in all_cats]
    movie_data = {}
    for cat in display_cats:
        q = {"cat": cat}
        if search: q["name"] = {"$regex": search, "$options": "i"}
        movie_data[cat] = list(movies_col.find(q).sort("_id", -1).limit(int(settings['post_limit'])))
    return render_template_string(HOME_HTML, settings=settings, display_cats=display_cats, movie_data=movie_data, all_cats=all_cats)

@app.route('/movie/<id>')
def details(id):
    settings = get_settings()
    movie = movies_col.find_one({"_id": ObjectId(id)})
    all_cats = list(cat_col.find().sort("name", 1))
    PAGE = """
    <!DOCTYPE html>
    <html>
    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{{movie.name}}</title>""" + BASE_CSS + """</head>
    <body>
        """ + NAV_HTML + """
        <div class="container" style="text-align:center; padding-top:80px;">
            <h1>{{movie.name}}</h1>
            <div class="ads">{{settings.ad_banner|safe}}</div>
            <div style="background:#000; padding:20px; border-radius:15px; border:1px solid #333; margin:20px 0;">{{movie.html_code|safe}}</div>
            <div class="ads">{{settings.ad_social|safe}}</div>
        </div>
    </body>
    </html>
    """
    return render_template_string(PAGE, movie=movie, settings=settings, all_cats=all_cats)

@app.route('/admin')
def admin():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    all_cats = list(cat_col.find().sort("name", 1))
    edit_id = request.args.get('edit_id')
    edit_movie = movies_col.find_one({"_id": ObjectId(edit_id)}) if edit_id else None
    mq = {"name": {"$regex": request.args.get('search', ''), "$options": "i"}}
    movies_list = list(movies_col.find(mq).sort("_id", -1))

    CONTENT = f"""
    <div id="add_movie" class="admin-section active">
        <div class="admin-box">
            <h3>Add/Edit Movie (DB Poster Upload)</h3>
            <form action="/admin/save-movie" method="POST" enctype="multipart/form-data">
                <input type="hidden" name="movie_id" value="{edit_movie['_id'] if edit_movie else ''}">
                <input type="text" name="name" value="{edit_movie['name'] if edit_movie else ''}" placeholder="Name" required>
                <input type="text" name="thumb_url" value="{edit_movie['thumb'] if edit_movie else ''}" placeholder="Image URL">
                <p style="text-align:center;">OR Upload from Gallery (Saved to MongoDB)</p>
                <input type="file" name="thumb_file">
                <select name="cat" required>
                    <option value="">Category</option>
                    {" ".join([f'<option value="{c["name"]}" {"selected" if edit_movie and edit_movie["cat"]==c["name"] else ""}>{c["name"]}</option>' for c in all_cats])}
                </select>
                <input type="text" name="lang" value="{edit_movie['lang'] if edit_movie else ''}" placeholder="Language">
                <textarea name="html_code" rows="6" oninput="document.getElementById('html-preview').innerHTML=this.value" placeholder="HTML Embed">{edit_movie['html_code'] if edit_movie else ''}</textarea>
                <div id="html-preview">Preview...</div>
                <button class="btn" style="margin-top:10px;">SAVE</button>
            </form>
        </div>
    </div>
    <div id="movie_list" class="admin-section">
        <div class="admin-box">
            <h3>Manage Movies</h3>
            {" ".join([f'<div style="border-bottom:1px solid #333; padding:10px;">{m["name"]} | <a href="/admin?edit_id={m["_id"]}">Edit</a> | <a href="/delete/{m["_id"]}" style="color:red;">Delete</a></div>' for m in movies_list])}
        </div>
    </div>
    <div id="cat_manage" class="admin-section">
        <div class="admin-box">
            <h3>Categories</h3>
            <form action="/admin/add-cat" method="POST"><input name="cat_name" placeholder="Name"><button class="btn">Add</button></form>
            {" ".join([f'<div>{c["name"]} | <a href="/admin/del-cat/{c["_id"]}" style="color:red;">Del</a></div>' for c in all_cats])}
        </div>
    </div>
    <div id="site_settings" class="admin-section">
        <form action="/admin/settings" method="POST" class="admin-box">
            <h3>Settings</h3>
            Site Name: <input name="site_name" value="{settings['site_name']}">
            Notice: <input name="notice_text" value="{settings['notice_text']}">
            Notice BG: <input type="color" name="notice_bg" value="{settings['notice_bg']}">
            Notice Color: <input type="color" name="notice_color" value="{settings['notice_color']}">
            Thumb Width: <input name="thumb_width" value="{settings['thumb_width']}">
            Padding (T,B,L,R): <input name="p_top" value="{settings.get('p_top','10')}" style="width:20%"> <input name="p_bottom" value="{settings.get('p_bottom','10')}" style="width:20%"> <input name="p_left" value="{settings.get('p_left','10')}" style="width:20%"> <input name="p_right" value="{settings.get('p_right','10')}" style="width:20%">
            Limit: <input name="post_limit" value="{settings['post_limit']}">
            <button class="btn">Update</button>
        </form>
    </div>
    <div id="security" class="admin-section">
        <form action="/admin/security" method="POST" class="admin-box">
            <h3>Admin Security</h3>
            User: <input name="admin_user" value="{settings['admin_user']}">
            Pass: <input name="admin_pass" value="{settings['admin_pass']}">
            <button class="btn">Change Access</button>
        </form>
    </div>
    """
    return render_template_string("""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Admin</title>""" + BASE_CSS + """</head><body>""" + NAV_HTML + """<div class="container" style="padding-top:80px;"><h1 style="text-align:center; color:red;">ADMIN PANEL</h1>""" + CONTENT + """</div></body></html>""", settings=settings, all_cats=all_cats, edit_movie=edit_movie)

@app.route('/admin/save-movie', methods=['POST'])
def save_movie():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    movie_id = request.form.get('movie_id')
    thumb = request.form.get('thumb_url')
    
    # MongoDB-তে ছবি আপলোড করার লজিক (Base64)
    if 'thumb_file' in request.files:
        file = request.files['thumb_file']
        if file.filename != '':
            encoded_string = base64.b64encode(file.read()).decode('utf-8')
            thumb = f"data:{file.content_type};base64,{encoded_string}"
            
    data = {"name": request.form['name'], "thumb": thumb, "lang": request.form['lang'], "cat": request.form['cat'], "html_code": request.form['html_code']}
    
    if movie_id: movies_col.update_one({"_id": ObjectId(movie_id)}, {"$set": data})
    else:
        new_m = movies_col.insert_one(data)
        if settings['tg_token'] and settings['tg_chat_id']:
            requests.post(f"https://api.telegram.org/bot{settings['tg_token']}/sendPhoto", data={"chat_id": settings['tg_chat_id'], "photo": thumb, "caption": f"🎬 {data['name']}\n🔗 {request.host_url}movie/{new_m.inserted_id}", "parse_mode": "Markdown"})
    return redirect('/admin')

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('admin'): return redirect('/login')
    settings_col.update_one({}, {"$set": request.form.to_dict()})
    return redirect('/admin')

@app.route('/admin/security', methods=['POST'])
def update_security():
    if not session.get('admin'): return redirect('/login')
    settings_col.update_one({}, {"$set": {"admin_user": request.form['admin_user'], "admin_pass": request.form['admin_pass']}})
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

@app.route('/delete/<id>')
def delete_movie(id):
    if not session.get('admin'): return redirect('/login')
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

@app.route('/login', methods=['GET', 'POST'])
def login():
    s = get_settings()
    if request.method == 'POST':
        if request.form['user'] == s['admin_user'] and request.form['pass'] == s['admin_pass']:
            session['admin'] = True
            return redirect('/admin')
    return render_template_string("""<body style="background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;"><form method="POST" style="background:#111;padding:40px;border-radius:15px;width:300px;border:1px solid #333;"><h2 style="text-align:center;color:red;">LOGIN</h2><input name="user" placeholder="User" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;"><input name="pass" type="password" placeholder="Pass" style="width:100%;padding:10px;margin:10px 0;background:#000;color:#fff;border:1px solid #333;"><button style="width:100%;padding:10px;background:red;color:#fff;border:none;cursor:pointer;">Login</button></form></body>""")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
