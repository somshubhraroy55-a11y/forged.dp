# TeamForge - Community App (iQOO Hackathon)
Finds the teammates your hackathon project is missing. Skill matching runs **in the browser (on-device)**; Flask + SQLite store profiles, posts and connection requests.

## Run
```
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000  - demo login: `aarav@demo.com` / `demo123`

## Structure
- `app.py` - Flask REST API + matching engine
- `schema.sql` - SQLite tables: users, user_skills, sessions, posts, connections
- `static/` - index.html, style.css, app.js (frontend)

## API
| Method | Route | Auth | Purpose |
|---|---|---|---|
| POST | /api/register, /api/login | no | create account / get token |
| GET | /api/me | yes | current user |
| GET | /api/users | no | all profiles with skills |
| GET | /api/skills | no | skill dictionary |
| POST | /api/match | no | server-side ranking for a text |
| GET/POST | /api/posts | POST yes | community feed |
| POST | /api/connect | yes | send connection request |
| GET | /api/connections | yes | my requests |

## Matching logic
Score = 3 per exact skill the user asked for + 1 per skill in the same category. Passwords are hashed (werkzeug); sessions use random tokens.
