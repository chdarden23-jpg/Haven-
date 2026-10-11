"""Encrypted SQLite data store, secure password hashes, opaque persistent sessions."""
import os,json,hmac,hashlib,secrets,sqlite3,time,base64
from pathlib import Path
from cryptography.fernet import Fernet
DB_PATH=os.environ.get('ANEIRA_DATABASE',str(Path(__file__).parent/'runtime'/'aneira.sqlite3'))
KEY=os.environ.get('ANEIRA_ENCRYPTION_KEY')
if not KEY:
 raise RuntimeError('Set ANEIRA_ENCRYPTION_KEY to a stable Fernet key; refusing to start without encryption')
FERNET=Fernet(KEY.encode())
SESSION_AGE=60*60*24*7

def connect():
 p=Path(DB_PATH);p.parent.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(str(p));c.row_factory=sqlite3.Row
 c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA journal_mode=WAL');return c

def init():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,created REAL NOT NULL);
  CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires REAL NOT NULL);
  CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,kind TEXT NOT NULL,item_key TEXT NOT NULL,payload BLOB NOT NULL,updated REAL NOT NULL, UNIQUE(user_id,kind,item_key));
  CREATE TABLE IF NOT EXISTS resets(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires REAL NOT NULL,used INTEGER DEFAULT 0);
  CREATE INDEX IF NOT EXISTS records_owner ON records(user_id,kind);
  CREATE INDEX IF NOT EXISTS sessions_owner ON sessions(user_id);
  ''')

def pw_hash(password):
 if len(password)<12 or len(password)>1024:raise ValueError('Password must have at least 12 characters')
 salt=secrets.token_bytes(16);dk=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
 return 'scrypt$'+base64.urlsafe_b64encode(salt).decode()+'$'+base64.urlsafe_b64encode(dk).decode()

def check_pw(password,stored):
 try:
  _,sa,ha=stored.split('$');salt=base64.urlsafe_b64decode(sa);expected=base64.urlsafe_b64decode(ha)
  calc=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
  return hmac.compare_digest(calc,expected)
 except Exception:return False

def digest(token):return hashlib.sha256(token.encode()).hexdigest()

def register(email,password):
 with connect() as c:
  try:
   x=c.execute('INSERT INTO users(email,password_hash,created) VALUES(?,?,?)',(email.lower().strip(),pw_hash(password),time.time()))
   return x.lastrowid
  except sqlite3.IntegrityError:raise ValueError('Account already exists')

def login(email,password):
 with connect() as c:
  user=c.execute('SELECT id,password_hash FROM users WHERE email=?',(email.lower().strip(),)).fetchone()
  if not user or not check_pw(password,user['password_hash']):raise ValueError('Incorrect credentials')
  token=secrets.token_urlsafe(40);c.execute('INSERT INTO sessions VALUES(?,?,?)',(digest(token),user['id'],time.time()+SESSION_AGE));return token

def identify(token):
 if not token:return None
 with connect() as c:
  row=c.execute('SELECT user_id FROM sessions WHERE token_hash=? AND expires>?',(digest(token),time.time())).fetchone()
  return row['user_id'] if row else None

def logout(token):
 if token:
  with connect() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(digest(token),))

def save(uid,kind,item_key,obj):
 encoded=FERNET.encrypt(json.dumps(obj,ensure_ascii=False).encode())
 with connect() as c:c.execute('INSERT INTO records(user_id,kind,item_key,payload,updated) VALUES(?,?,?,?,?) ON CONFLICT(user_id,kind,item_key) DO UPDATE SET payload=excluded.payload,updated=excluded.updated',(uid,kind,item_key,encoded,time.time()))

def load(uid,kind,item_key):
 with connect() as c:r=c.execute('SELECT payload FROM records WHERE user_id=? AND kind=? AND item_key=?',(uid,kind,item_key)).fetchone()
 return json.loads(FERNET.decrypt(r['payload'])) if r else None

def list_records(uid,kind=None):
 with connect() as c:
  rows=c.execute('SELECT kind,item_key,payload,updated FROM records WHERE user_id=? '+('AND kind=? ' if kind else '')+'ORDER BY updated DESC',(uid,kind) if kind else (uid,)).fetchall()
 return [{'kind':r['kind'],'key':r['item_key'],'data':json.loads(FERNET.decrypt(r['payload'])),'updated':r['updated']} for r in rows]

def erase(uid,kind,key):
 with connect() as c:c.execute('DELETE FROM records WHERE user_id=? AND kind=? AND item_key=?',(uid,kind,key))

def delete_user(uid):
 with connect() as c:c.execute('DELETE FROM users WHERE id=?',(uid,))

def begin_reset(email):
 # Return token only to configured mail delivery; no user enumeration.
 with connect() as c:
  u=c.execute('SELECT id FROM users WHERE email=?',(email.lower().strip(),)).fetchone()
  if not u:return None
  token=secrets.token_urlsafe(36)
  c.execute('INSERT INTO resets(token_hash,user_id,expires) VALUES(?,?,?)',(digest(token),u['id'],time.time()+900))
  return token

def complete_reset(token,password):
 newhash=pw_hash(password)
 with connect() as c:
  r=c.execute('SELECT user_id FROM resets WHERE token_hash=? AND used=0 AND expires>?',(digest(token),time.time())).fetchone()
  if not r:raise ValueError('Invalid or expired reset link')
  uid=r['user_id'];c.execute('UPDATE users SET password_hash=? WHERE id=?',(newhash,uid));c.execute('UPDATE resets SET used=1 WHERE user_id=?',(uid,));c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
