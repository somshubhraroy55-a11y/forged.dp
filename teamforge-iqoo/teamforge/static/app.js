// TeamForge frontend - talks to the Flask REST API in app.py
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let token = localStorage.getItem('tf_token'), me = null, users = [], vocab = {skills:{}, words:{}}, registerMode = false;

async function api(path, opt = {}) {
  const res = await fetch('/api' + path, {
    method: opt.method || 'GET',
    headers: {'Content-Type': 'application/json', ...(token ? {Authorization: 'Bearer ' + token} : {})},
    body: opt.body ? JSON.stringify(opt.body) : undefined
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// ---- on-device matching (runs in the browser, no server call) ----
function localMatch(text) {
  const want = new Set(), cats = new Set();
  (text.toLowerCase().match(/[a-z0-9+#]+/g) || []).forEach(w => {
    if (vocab.skills[w]) { want.add(w); cats.add(vocab.skills[w]); }
    if (vocab.words[w]) cats.add(vocab.words[w]);
  });
  const ranked = users.filter(u => !me || u.id !== me.id).map(u => {
    let score = 0; const hit = [];
    u.skills.forEach(s => {
      if (want.has(s)) { score += 3; hit.push(s); }
      else if (cats.has(vocab.skills[s])) { score += 1; hit.push(s); }
    });
    return {...u, score, matched: hit};
  }).sort((a, b) => b.score - a.score);
  return {ranked, cats: [...cats], want: [...want]};
}

function showMatches() {
  const {ranked, cats, want} = localMatch($('need').value);
  $('detected').innerHTML = cats.length ? 'Detected: ' + cats.map(c => `<span class="chip m">${esc(c)}</span>`).join('') + want.map(s => `<span class="chip">${esc(s)}</span>`).join('') : 'No skills detected yet. Try words like react, c++, figma.';
  $('matches').innerHTML = ranked.filter(u => u.score > 0).slice(0, 6).map(u => `
    <div class="u"><div><b>${esc(u.name)}</b> <span class="mut">${esc(u.role)}</span><br>
    ${u.skills.map(s => `<span class="chip ${u.matched.includes(s) ? 'm' : ''}">${esc(s)}</span>`).join('')}</div>
    <div><b>${u.score}</b><br><button data-to="${u.id}">Connect</button></div></div>`).join('') || '<p class="mut">No matches yet.</p>';
}

async function loadFeed() {
  const posts = await api('/posts');
  $('feed').innerHTML = posts.map(p => `<div class="post"><b>${esc(p.name)}</b>: ${esc(p.text)}</div>`).join('') || '<p class="mut">No posts yet.</p>';
}
async function loadConns() {
  const c = await api('/connections');
  $('conns').innerHTML = c.length ? c.map(x => `<div class="post">${x.sent_by_me ? 'You asked' : 'Request from'} <b>${esc(x.name)}</b> (${esc(x.status)})</div>`).join('') : 'Nothing yet.';
}

function setView() {
  const on = !!me;
  $('authBox').hidden = on; $('app').hidden = !on;
  $('who').innerHTML = on ? `${esc(me.name)} <button id="out">Logout</button>` : '';
  if (on) { loadFeed(); loadConns(); }
}

async function boot() {
  vocab = await api('/skills'); users = await api('/users');
  if (token) { try { me = await api('/me'); } catch (e) { token = null; localStorage.removeItem('tf_token'); } }
  setView();
}

$('toggle').onclick = e => {
  e.preventDefault(); registerMode = !registerMode;
  ['name', 'role', 'skills'].forEach(i => $(i).hidden = !registerMode);
  $('authTitle').textContent = $('authBtn').textContent = registerMode ? 'Create account' : 'Login';
  $('toggle').textContent = registerMode ? 'Have an account? Login' : 'New here? Create account';
};
$('authBtn').onclick = async () => {
  try {
    const body = {email: $('email').value, password: $('pw').value, name: $('name').value, role: $('role').value, skills: $('skills').value};
    const d = await api(registerMode ? '/register' : '/login', {method: 'POST', body});
    token = d.token; me = d.user; localStorage.setItem('tf_token', token);
    users = await api('/users'); $('authErr').textContent = ''; setView();
  } catch (e) { $('authErr').textContent = e.message; }
};
$('find').onclick = showMatches;
$('need').oninput = showMatches;
$('share').onclick = async () => {
  showMatches();
  try { await api('/posts', {method: 'POST', body: {text: $('need').value}}); loadFeed(); } catch (e) { alert(e.message); }
};
document.addEventListener('click', async e => {
  if (e.target.id === 'out') { token = null; me = null; localStorage.removeItem('tf_token'); setView(); }
  if (e.target.dataset.to) {
    try { await api('/connect', {method: 'POST', body: {to_id: +e.target.dataset.to}}); loadConns(); e.target.textContent = 'Sent'; }
    catch (err) { alert(err.message); }
  }
});
boot();
