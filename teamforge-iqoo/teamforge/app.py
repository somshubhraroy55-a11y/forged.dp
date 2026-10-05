"""TeamForge backend - Flask + SQLite REST API.
Run:  pip install -r requirements.txt  then  python app.py
"""
import re, secrets, sqlite3
from functools import wraps
from flask import Flask, g, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, static_folder="static")
DB = "teamforge.db"

# skill -> category (the "knowledge base" used by the matcher)
SKILLS = {
    "react": "Frontend", "html": "Frontend", "css": "Frontend", "javascript": "Frontend", "tailwind": "Frontend",
    "figma": "Design", "ui": "Design", "ux": "Design", "canva": "Design",
    "node": "Backend", "python": "Backend", "flask": "Backend", "sql": "Backend", "api": "Backend", "firebase": "Backend",
    "ml": "AI/ML", "ai": "AI/ML", "tensorflow": "AI/ML", "nlp": "AI/ML", "tflite": "AI/ML", "opencv": "AI/ML",
    "c++": "Embedded", "c": "Embedded", "arduino": "Embedded", "iot": "Embedded", "esp32": "Embedded", "sensors": "Embedded",
    "kotlin": "Mobile", "android": "Mobile", "flutter": "Mobile",
    "pitch": "Pitch", "ppt": "Pitch", "presentation": "Pitch", "research": "Pitch",
}
WORDS = {"frontend": "Frontend", "backend": "Backend", "design": "Design", "embedded": "Embedded",
         "hardware": "Embedded", "mobile": "Mobile", "app": "Mobile", "web": "Frontend", "website": "Frontend"}
CATS = ["Frontend", "Design", "Backend", "AI/ML", "Embedded", "Mobile", "Pitch"]

SEED = [
    ("Aarav", "aarav@demo.com", "Web developer", "react javascript css tailwind"),
    ("Meera", "meera@demo.com", "UI designer", "figma ui ux canva"),
    ("Ishaan", "ishaan@demo.com", "Embedded tinkerer", "c++ arduino esp32 sensors"),
    ("Diya", "diya@demo.com", "ML student", "python tensorflow nlp opencv"),
    ("Kabir", "kabir@demo.com", "Backend dev", "node sql api firebase"),
    ("Zoya", "zoya@demo.com", "Android dev", "kotlin android flutter tflite"),
    ("Rohan", "rohan@demo.com", "Storyteller", "pitch ppt presentation research"),
    ("Anika", "anika@demo.com", "Full-stack", "react python flask sql"),
]

def init_db():
    con = sqlite3.connect(DB)
    con.executescript(open("schema.sql").read())
    if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        for name, email, role, sk in SEED:   # demo accounts, password = demo123
            uid = con.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                              (name, email, generate_password_hash("demo123"), role)).lastrowid
            con.executemany("INSERT INTO user_skills VALUES(?,?)", [(uid, s) for s in sk.split()])
    con.commit(); con.close()

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def tokens(text): return re.findall(r"[a-z0-9+#]+", text.lower())
def clean_skills(text): return sorted({w for w in tokens(text) if w in SKILLS})

def all_users():
    users = {r["id"]: {"id": r["id"], "name": r["name"], "role": r["role"], "skills": []}
             for r in db().execute("SELECT id,name,role FROM users")}
    for r in db().execute("SELECT user_id,skill FROM user_skills"):
        users[r["user_id"]]["skills"].append(r["skill"])
    return users

def new_session(uid):
    t = secrets.token_hex(16)
    db().execute("INSERT INTO sessions VALUES(?,?)", (t, uid)); db().commit()
    return t

def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        t = request.headers.get("Authorization", "").replace("Bearer ", "")
        row = db().execute("SELECT user_id FROM sessions WHERE token=?", (t,)).fetchone()
        if not row: return jsonify(error="Please log in first"), 401
        g.uid = row["user_id"]
        return f(*a, **kw)
    return wrapper

def match(text, exclude=None):
    """Score = 3 per exact skill match + 1 per same-category skill."""
    want, cats = set(), set()
    for w in tokens(text):
        if w in SKILLS: want.add(w); cats.add(SKILLS[w])
        if w in WORDS: cats.add(WORDS[w])
    out = []
    for u in all_users().values():
        if u["id"] == exclude: continue
        score, hit = 0, []
        for s in u["skills"]:
            if s in want: score += 3; hit.append(s)
            elif SKILLS[s] in cats: score += 1; hit.append(s)
        out.append({**u, "score": score, "matched": hit})
    return sorted(out, key=lambda x: -x["score"])

# ---------- routes ----------
@app.get("/")
def home(): return send_from_directory("static", "index.html")

@app.get("/api/skills")
def skills(): return jsonify(skills=SKILLS, words=WORDS, cats=CATS)

@app.post("/api/register")
def register():
    d = request.get_json(silent=True) or {}
    name, email, pw = d.get("name", "").strip(), d.get("email", "").strip().lower(), d.get("password", "")
    sk = clean_skills(d.get("skills", ""))
    if not name or "@" not in email or len(pw) < 4: return jsonify(error="Enter name, valid email and a 4+ character password"), 400
    if not sk: return jsonify(error="Add at least one known skill, e.g. react, c++, python"), 400
    try:
        uid = db().execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                           (name[:40], email, generate_password_hash(pw), d.get("role", "Student")[:40] or "Student")).lastrowid
    except sqlite3.IntegrityError:
        return jsonify(error="Email already registered"), 409
    db().executemany("INSERT INTO user_skills VALUES(?,?)", [(uid, s) for s in sk]); db().commit()
    return jsonify(token=new_session(uid), user=all_users()[uid])

@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    r = db().execute("SELECT * FROM users WHERE email=?", (d.get("email", "").strip().lower(),)).fetchone()
    if not r or not check_password_hash(r["password_hash"], d.get("password", "")):
        return jsonify(error="Wrong email or password"), 401
    return jsonify(token=new_session(r["id"]), user=all_users()[r["id"]])

@app.get("/api/me")
@login_required
def me(): return jsonify(all_users()[g.uid])

@app.get("/api/users")
def users(): return jsonify(list(all_users().values()))

@app.post("/api/match")
def match_api():
    text = (request.get_json(silent=True) or {}).get("text", "")
    return jsonify(match(text))

@app.get("/api/posts")
def posts():
    rows = db().execute("SELECT p.id,p.text,p.created_at,u.name FROM posts p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC LIMIT 20")
    return jsonify([dict(r) for r in rows])

@app.post("/api/posts")
@login_required
def add_post():
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text or len(text) > 300: return jsonify(error="Post must be 1-300 characters"), 400
    db().execute("INSERT INTO posts(user_id,text) VALUES(?,?)", (g.uid, text)); db().commit()
    return jsonify(ok=True), 201

@app.post("/api/connect")
@login_required
def connect():
    to = (request.get_json(silent=True) or {}).get("to_id")
    if to == g.uid or to not in all_users(): return jsonify(error="Invalid user"), 400
    try:
        db().execute("INSERT INTO connections(from_id,to_id) VALUES(?,?)", (g.uid, to)); db().commit()
    except sqlite3.IntegrityError:
        return jsonify(error="Request already sent"), 409
    return jsonify(ok=True), 201

@app.get("/api/connections")
@login_required
def connections():
    rows = db().execute("""SELECT c.id,c.status,c.from_id,u.name FROM connections c
        JOIN users u ON u.id = CASE WHEN c.from_id=? THEN c.to_id ELSE c.from_id END
        WHERE c.from_id=? OR c.to_id=?""", (g.uid, g.uid, g.uid))
    return jsonify([{**dict(r), "sent_by_me": r["from_id"] == g.uid} for r in rows])

init_db()
if __name__ == "__main__":
    app.run(debug=True, port=5000)
