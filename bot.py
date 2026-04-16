import os
import base64
import io
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

try:
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except:
    pass

# --- MongoDB Setup ---
MONGO_URI = "mongodb+srv://roxiw19528:roxiw19528@cluster0.vl508y4.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['movie_v53']
movies_col = db['movie']
settings_col = db['settings']
cat_col = db['categories']
shortlinks_col = db['shortlinks'] # স্টেপ লিঙ্কের জন্য নতুন কালেকশন

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
            "thumb_width": "100%", 
            "thumb_height": "auto",
            "thumb_margin": "0", 
            "tg_token": "", 
            "tg_chat_id": "", 
            "post_limit": 5, 
            "ad_banner": "", 
            "ad_popunder": "", 
            "ad_social": "",
            "step_wait_time": 5, # ডিফল্ট স্টেপ ওয়েট টাইম
            "admin_user": "admin", 
            "admin_pass": "admin"  
        }
        settings_col.insert_one(default)
        return default
    return settings

# --- টেলিগ্রাম নোটিফিকেশন ফাংশন (Base64 ও এডিট ফিক্সড) ---
def send_tg_notification(movie_id, data, settings, is_edit=False):
    if not settings.get('tg_token') or not settings.get('tg_chat_id'):
        return
    movie_url = request.host_url + "movie/" + str(movie_id)
    title = "🔄 Movie Updated!" if is_edit else "🎬 New Movie Posted!"
    caption = f"*{title}*\n\n⭐ *Name:* {data['name']}\n🌍 *Lang:* {data['lang']}\n📂 *Cat:* {data['cat']}\n🔗 [Watch Now]({movie_url})"
    tg_api = f"https://api.telegram.org/bot{settings['tg_token']}/sendPhoto"
    try:
        if data['thumb'].startswith('data:image'):
            header, encoded = data['thumb'].split(",", 1)
            image_data = base64.b64decode(encoded)
            files = {'photo': ('image.jpg', io.BytesIO(image_data), 'image/jpeg')}
            payload = {"chat_id": settings['tg_chat_id'], "caption": caption, "parse_mode": "Markdown"}
            requests.post(tg_api, data=payload, files=files)
        else:
            payload = {"chat_id": settings['tg_chat_id'], "photo": data['thumb'], "caption": caption, "parse_mode": "Markdown"}
            requests.post(tg_api, data=payload)
    except Exception as e:
        print(f"Telegram Notification Error: {e}")

# --- CSS Design (সব ডিজাইন একসাথে) ---
BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
    :root { --primary: #e50914; --dark: #080808; --card: #121212; --text: #ffffff; --sidebar: #111; }
    body { background: var(--dark); color: var(--text); font-family: 'Poppins', sans-serif; margin: 0; padding: 0; overflow-x: hidden; touch-action: pan-y; }
    @keyframes rainbow { 0%{color:#ff0000} 15%{color:#ff8800} 30%{color:#ffff00} 45%{color:#00ff00} 60%{color:#00ffff} 75%{color:#0000ff} 90%{color:#8800ff} 100%{color:#ff0000} }
    .logo { font-size: 26px; font-weight: 800; animation: rainbow 4s infinite; text-decoration: none; display: flex; align-items: center; justify-content: center; padding: 15px; }
    .notice-bar { padding: 10px; text-align: center; font-size: 14px; font-weight: bold; }
    .container { width: 95%; max-width: 1400px; margin: auto; }
    .sidebar { position: fixed; left: -280px; top: 0; height: 100%; width: 280px; background: var(--sidebar); transition: 0.3s; z-index: 1001; border-right: 1px solid #333; }
    .sidebar.active { left: 0; }
    .sidebar-header { padding: 20px; border-bottom: 1px solid #333; font-weight: bold; color: var(--primary); font-size: 20px; text-align: center; }
    .sidebar a { display: block; padding: 15px 20px; color: white; text-decoration: none; border-bottom: 1px solid #222; transition: 0.3s; }
    .sidebar a:hover { background: var(--primary); padding-left: 30px; }
    .overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; }
    .overlay.active { display: block; }
    
    /* Movie Card landscape */
    .movie-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; }
    .movie-card { background: var(--card); border-radius: 8px; overflow: hidden; text-decoration: none; color: #fff; transition: 0.3s; border: 1px solid #222; position: relative; }
    .movie-card img { width: 100%; aspect-ratio: 16 / 9; object-fit: cover; display: block; }
    .movie-badge { position: absolute; top: 10px; left: 10px; background: var(--primary); color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; z-index: 2; box-shadow: 0 0 5px rgba(0,0,0,0.5); }
    .movie-info { padding: 10px; text-align: left; font-size: 14px; }
    
    /* Detail Page Unlocker Styles */
    .poster-top { width: 100%; max-width: 800px; margin: 0 auto; line-height: 0; overflow: hidden; }
    .poster-top img { width: 100%; height: auto; border-bottom: 5px solid #1a1a1a; display: block; }
    .lang-card { background: linear-gradient(145deg, #0f0f0f, #000); border: 2px solid #333; border-left: 10px solid #00ff00; padding: 20px; border-radius: 8px; display: flex; align-items: center; justify-content: center; gap: 20px; box-shadow: 0 0 30px rgba(0,255,0,0.1); }
    .lang-value { color: #00ff00; font-size: 24px; font-weight: 900; text-shadow: 0 0 10px rgba(0,255,0,0.4); }
    .unlock-area { background: #080808; padding: 30px 15px; border-radius: 8px; border: 1px solid #1a1a1a; margin-top: 20px; text-align: center; }
    .massive-button { width: 100%; max-width: 600px; padding: 25px 15px; font-size: 28px; font-weight: 900; color: #fff; border-radius: 10px; border: none; cursor: pointer; text-transform: uppercase; background: linear-gradient(to right, #ff0000, #9b0000); box-shadow: 0 8px 25px rgba(255, 0, 0, 0.4); }
    .massive-button:disabled { background: #222 !important; color: #444 !important; cursor: not-allowed; box-shadow: none; }
    .progress-wrap { width: 100%; height: 20px; background: #111; margin: 20px auto; border-radius: 10px; display: none; overflow: hidden; border: 1px solid #222; max-width: 600px; }
    .progress-fill { width: 0%; height: 100%; background: linear-gradient(90deg, #ff0000, #00ff00); transition: 0.4s; }
    .timer-style { display:none; color:#ffcc00; font-weight:bold; margin-top:15px; font-size:30px; }
    .unlock-success { background: linear-gradient(to right, #00b09b, #96c93d) !important; animation: pulse 1.5s infinite; }
    
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.03);} 100% {transform: scale(1);} }

    /* Slider landscape */
    .slider { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; gap: 10px; padding: 10px 0; scrollbar-width: none; }
    .slider::-webkit-scrollbar { display: none; }
    .slide-item { flex: 0 0 85%; scroll-snap-align: start; position: relative; border-radius: 12px; overflow: hidden; aspect-ratio: 16 / 9; }
    .slide-item img { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.7); }

    /* Admin UI */
    .admin-section { display: none; padding: 20px; }
    .admin-section.active { display: block; }
    .input-group { background: #1a1a1a; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333; }
    input, textarea, select { width: 100%; padding: 12px; margin: 8px 0; border-radius: 5px; border: 1px solid #333; background: #000; color: #fff; box-sizing: border-box; }
    .btn { background: var(--primary); color: #fff; border: none; padding: 12px 25px; cursor: pointer; border-radius: 5px; font-weight: bold; width: 100%; }
    
    @media (max-width: 600px) { .movie-grid { grid-template-columns: repeat(1, 1fr); } .slide-item { flex: 0 0 100%; } }
</style>
"""

SIDEBAR_HTML = """
<div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
<div class="sidebar" id="sidebar">
    <div class="sidebar-header">MENU</div>
    <a href="/">🏠 Home</a>
    {% if session.admin %}
    <a href="javascript:void(0)" onclick="showSection('add_movie')">➕ Add Movie</a>
    <a href="javascript:void(0)" onclick="showSection('movie_list')">🎬 Manage Movies</a>
    <a href="javascript:void(0)" onclick="showSection('cat_manage')">📂 Categories</a>
    <a href="javascript:void(0)" onclick="showSection('step_manage')">🔗 Manage Step Links</a>
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

HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ settings.site_name }}</title>
    """ + BASE_CSS + """
</head>
<body>
    <div class="notice-bar" style="background:{{ settings.notice_bg }}; color:{{ settings.notice_color }};">
        <marquee>{{ settings.notice_text }}</marquee>
    </div>
    """ + SIDEBAR_HTML + """
    <header class="container">
        <a href="/" class="logo">{{ settings.site_name }}</a>
        <div style="text-align:center; color:#555; font-size:10px;"><span onclick="toggleSidebar()" style="cursor:pointer;">Categories</span></div>
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
        {% for cat in categories %}
        <div class="cat-section" style="margin-top:30px;">
            <div style="display:flex; justify-content:space-between; border-left:4px solid red; padding-left:10px; margin-bottom:15px;">
                <h3 style="margin:0;">{{ cat }}</h3>
                <a href="/category/{{cat}}" style="color:red; text-decoration:none; font-weight:bold;">SEE ALL →</a>
            </div>
            <div class="movie-grid">
                {% for movie in movie_data[cat] %}
                <a href="/movie/{{ movie._id }}" class="movie-card">
                    {% if movie.badge %}<div class="movie-badge">{{ movie.badge }}</div>{% endif %}
                    <img src="{{ movie.thumb }}">
                    <div class="movie-info"><strong>{{ movie.name }}</strong><span style="color:#888; font-size:12px;">{{ movie.lang }}</span></div>
                </a>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

DETAIL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ movie.name }} - Premium Unlocker</title>
    """ + BASE_CSS + """
</head>
<body>
    """ + SIDEBAR_HTML + """
    <header class="container"><a href="/" class="logo">{{ settings.site_name }}</a></header>
    
    <div class="poster-top">
        <img src="{{ movie.thumb }}" alt="Poster">
    </div>

    <div class="container" style="max-width:900px;">
        <div class="lang-card" style="margin-top:20px;">
            <div class="lang-content" style="text-align:center; width:100%;">
                <span style="color: #888; font-size: 14px; font-weight: bold; display: block;">MOVIE AUDIO LANGUAGE</span>
                <span class="lang-value">{{ movie.lang }}</span>
            </div>
        </div>

        <div class="unlock-area">
            <p id="status-text" style="color: #ffcc00; font-size: 20px; font-weight: bold; margin-bottom: 20px;">Click the button to start ({{ total_steps }} Steps)</p>
            <div id="progress-container" class="progress-wrap"><div id="progress-bar" class="progress-fill"></div></div>
            <button id="mainBtn" class="massive-button" onclick="handleStep()">UNLOCK STEP 01</button>
            <div id="timer-display" class="timer-style">WAITING: <span id="seconds">00</span>s</div>
        </div>

        <div style="margin-top:40px; display:flex; justify-content:center; gap:20px;">
            <a href="https://t.me/Drama4uOfficial" target="_blank" style="text-decoration:none; color:#0088cc; text-align:center;">
                <img src="https://cdn-icons-png.flaticon.com/512/2111/2111646.png" width="40"><br>CHANNEL 01
            </a>
            <a href="https://t.me/Drama2hChat" target="_blank" style="text-decoration:none; color:#0088cc; text-align:center;">
                <img src="https://cdn-icons-png.flaticon.com/512/2111/2111646.png" width="40"><br>CHANNEL 02
            </a>
        </div>
    </div>

    <script>
        const AD_LINKS = {{ ad_links | tojson }};
        const FINAL_LINK = "{{ movie.final_link }}";
        const STEP_WAIT_TIME = {{ settings.step_wait_time }};
        
        let currentStep = 1;
        let timerInterval = null;
        let secondsRemaining = STEP_WAIT_TIME;
        let isTimerBusy = false;

        function playVoice(text) {
            if ('speechSynthesis' in window) {
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.volume = 1.0; utterance.rate = 0.7; utterance.lang = 'en-US';
                window.speechSynthesis.speak(utterance);
            }
        }

        function handleStep() {
            if (isTimerBusy) return;
            if (currentStep > AD_LINKS.length) { window.location.href = FINAL_LINK; return; }
            window.open(AD_LINKS[currentStep - 1], '_blank');
            startCountdown();
        }

        function startCountdown() {
            isTimerBusy = true;
            secondsRemaining = STEP_WAIT_TIME;
            document.getElementById('mainBtn').disabled = true;
            document.getElementById('progress-container').style.display = 'block';
            document.getElementById('timer-display').style.display = 'block';
            document.getElementById('status-text').innerText = "Verifying... Stay on the Ad Page!";

            timerInterval = setInterval(() => {
                if (document.hidden) { 
                    secondsRemaining--;
                    document.getElementById('seconds').innerText = (secondsRemaining < 10 ? "0" : "") + secondsRemaining;
                    document.getElementById('progress-bar').style.width = ((STEP_WAIT_TIME - secondsRemaining) / STEP_WAIT_TIME) * 100 + "%";

                    if (secondsRemaining <= 0) {
                        clearInterval(timerInterval);
                        isTimerBusy = false;
                        playVoice("Attention! Step completed. Please return to the website now.");
                        document.getElementById('status-text').innerText = "✅ Step Unlocked! Come Back.";
                        document.getElementById('status-text').style.color = "#00ff00";
                    }
                }
            }, 1000);
        }

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !isTimerBusy && secondsRemaining <= 0) {
                if (currentStep <= AD_LINKS.length) { 
                    currentStep++; 
                    updateUI(); 
                }
                document.getElementById('mainBtn').disabled = false;
                document.getElementById('progress-container').style.display = 'none';
                document.getElementById('timer-display').style.display = 'none';
            }
        });

        function updateUI() {
            if (currentStep <= AD_LINKS.length) {
                document.getElementById('mainBtn').innerText = "UNLOCK STEP 0" + currentStep;
                document.getElementById('status-text').innerText = "Step Verified! Click the button below.";
                document.getElementById('status-text').style.color = "#ffcc00";
            } else {
                document.getElementById('mainBtn').innerText = "DOWNLOAD MOVIE NOW";
                document.getElementById('mainBtn').classList.add('unlock-success');
                document.getElementById('status-text').innerText = "CONGRATULATIONS! ACCESS GRANTED.";
                playVoice("Success! Your movie is ready for download. Click the button now.");
            }
        }
    </script>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Admin Dashboard</title>
    """ + BASE_CSS + """
</head>
<body style="background:#000;">
    <div style="padding:10px; text-align:center;"><button onclick="toggleSidebar()" class="btn" style="width:auto;">OPEN ADMIN MENU</button></div>
    """ + SIDEBAR_HTML + """
    <div class="container" style="padding-top:20px;">
        <h1 style="text-align:center; color:red; text-shadow:0 0 10px red;">ADMIN DASHBOARD</h1>
        
        <!-- Add Movie -->
        <div id="add_movie" class="admin-section active">
            <div class="input-group">
                <h3>{% if edit_movie %}Edit Movie{% else %}Add New Movie{% endif %}</h3>
                <form action="/admin/save-movie" method="POST" enctype="multipart/form-data">
                    <input type="hidden" name="movie_id" value="{{ edit_movie._id if edit_movie else '' }}">
                    <input type="text" name="name" value="{{ edit_movie.name if edit_movie else '' }}" placeholder="Movie Name" required>
                    <input type="text" name="final_link" value="{{ edit_movie.final_link if edit_movie else '' }}" placeholder="Final Movie Link (Telegram/Drive)" required>
                    <input type="text" name="badge" value="{{ edit_movie.badge if edit_movie else '' }}" placeholder="Badge (HD, 4K)">
                    <input type="text" name="thumb_url" value="{{ edit_movie.thumb if edit_movie else '' }}" placeholder="Thumb URL">
                    <input type="file" name="thumb_file">
                    <select name="cat">
                        {% for c in all_categories %}<option value="{{c.name}}" {% if edit_movie and edit_movie.cat == c.name %}selected{% endif %}>{{c.name}}</option>{% endfor %}
                    </select>
                    <input type="text" name="lang" value="{{ edit_movie.lang if edit_movie else '' }}" placeholder="Language (Hindi, English)">
                    <button type="submit" class="btn">Save & Post</button>
                </form>
            </div>
        </div>

        <!-- Step Management -->
        <div id="step_manage" class="admin-section">
            <div class="input-group">
                <h3>Manage Step Links (Shortlinks)</h3>
                <form action="/admin/add-shortlink" method="POST">
                    <input type="text" name="link" placeholder="Enter Shortlink" required>
                    <button type="submit" class="btn">Add New Step</button>
                </form>
                <div style="margin-top:20px;">
                    {% for sl in shortlinks %}
                    <div style="display:flex; justify-content:space-between; background:#222; padding:10px; margin-bottom:5px; border-radius:5px;">
                        <span style="overflow:hidden;">{{ sl.link }}</span>
                        <a href="/admin/del-shortlink/{{ sl._id }}" style="color:red; font-weight:bold;">Delete</a>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <div id="movie_list" class="admin-section">
            <div class="input-group">
                <h3>Manage Movies</h3>
                {% for m in movies %}
                <div style="padding:10px; border-bottom:1px solid #333;">{{m.name}} | <a href="/admin?edit_id={{m._id}}" style="color:cyan;">Edit</a> | <a href="/delete/{{m._id}}" style="color:red;">Delete</a></div>
                {% endfor %}
            </div>
        </div>

        <div id="site_settings" class="admin-section">
            <form action="/admin/settings" method="POST" class="input-group">
                <h3>Settings</h3>
                Wait Time (Seconds): <input type="number" name="step_wait_time" value="{{ settings.step_wait_time }}">
                Site Name: <input type="text" name="site_name" value="{{ settings.site_name }}">
                <button type="submit" class="btn">Update Settings</button>
            </form>
        </div>

        <!-- (Security, TG Settings etc remain as before) -->
        <div id="tg_settings" class="admin-section">
            <form action="/admin/settings" method="POST" class="input-group">
                <h3>Telegram Bot</h3>
                Token: <input type="text" name="tg_token" value="{{ settings.tg_token }}">
                Chat ID: <input type="text" name="tg_chat_id" value="{{ settings.tg_chat_id }}">
                <button type="submit" class="btn">Update</button>
            </form>
        </div>
    </div>
</body>
</html>
"""

# --- Backend Logics ---

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
    shortlinks = list(shortlinks_col.find())
    ad_links = [sl['link'] for sl in shortlinks]
    all_cats = list(cat_col.find().sort("name", 1))
    return render_template_string(DETAIL_HTML, movie=movie, settings=settings, ad_links=ad_links, total_steps=len(ad_links), all_categories=all_cats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    s = get_settings()
    if request.method == 'POST':
        if request.form['user'] == s['admin_user'] and request.form['pass'] == s['admin_pass']:
            session['admin'] = True
            return redirect('/admin')
    return render_template_string('<body style="background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;"><form method="POST"><h2>ADMIN</h2><input type="text" name="user"><input type="password" name="pass"><button>Login</button></form></body>')

@app.route('/admin')
def admin():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    all_cats = list(cat_col.find().sort("name", 1))
    edit_id = request.args.get('edit_id')
    edit_movie = movies_col.find_one({"_id": ObjectId(edit_id)}) if edit_id else None
    movies_list = list(movies_col.find().sort("_id", -1))
    shortlinks = list(shortlinks_col.find())
    return render_template_string(ADMIN_HTML, settings=settings, all_categories=all_cats, movies=movies_list, edit_movie=edit_movie, shortlinks=shortlinks)

@app.route('/admin/save-movie', methods=['POST'])
def save_movie():
    if not session.get('admin'): return redirect('/login')
    settings = get_settings()
    movie_id = request.form.get('movie_id')
    thumb = request.form.get('thumb_url')
    if 'thumb_file' in request.files:
        file = request.files['thumb_file']
        if file.filename != '':
            encoded_string = base64.b64encode(file.read()).decode('utf-8')
            thumb = f"data:{file.content_type};base64,{encoded_string}"
    
    data = {
        "name": request.form['name'], 
        "final_link": request.form['final_link'],
        "thumb": thumb,
        "badge": request.form.get('badge', ''),
        "lang": request.form['lang'], 
        "cat": request.form['cat']
    }
    
    if movie_id:
        movies_col.update_one({"_id": ObjectId(movie_id)}, {"$set": data})
        send_tg_notification(movie_id, data, settings, is_edit=True)
    else:
        new_mov = movies_col.insert_one(data)
        send_tg_notification(new_mov.inserted_id, data, settings, is_edit=False)
    return redirect('/admin')

@app.route('/admin/add-shortlink', methods=['POST'])
def add_shortlink():
    if not session.get('admin'): return redirect('/login')
    shortlinks_col.insert_one({"link": request.form['link']})
    return redirect('/admin')

@app.route('/admin/del-shortlink/<id>')
def del_shortlink(id):
    if not session.get('admin'): return redirect('/login')
    shortlinks_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if not session.get('admin'): return redirect('/login')
    settings_col.update_one({}, {"$set": request.form.to_dict()})
    return redirect('/admin')

@app.route('/delete/<id>')
def delete_movie(id):
    if not session.get('admin'): return redirect('/login')
    movies_col.delete_one({"_id": ObjectId(id)})
    return redirect('/admin')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
