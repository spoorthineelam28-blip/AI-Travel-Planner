import os, sqlite3, requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
app=Flask(__name__); app.secret_key=os.getenv('SECRET_KEY','change-me'); DB='travel_planner.db'
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 c=db(); c.execute('CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT)'); c.execute('CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY,user_id INTEGER,destination TEXT,days INTEGER,budget REAL,itinerary TEXT,created_at TEXT)'); c.commit(); c.close()
def fallback(d,n,b):
 x=[f'AI Travel Plan for {d}','']; day=b/max(n,1)
 for i in range(1,n+1): x += [f'Day {i}',f'• Morning: Explore a major attraction in {d}.',f'• Afternoon: Visit a landmark and try local food.',f'• Evening: Relax, shop or enjoy a scenic spot.',f'• Suggested daily budget: ₹{day:,.2f}','']
 return '\n'.join(x)
def itinerary(d,n,b):
 key=os.getenv('GEMINI_API_KEY')
 if not key:return fallback(d,n,b)
 try:
  model=os.getenv('GEMINI_MODEL','gemini-2.5-flash'); url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
  prompt=f'Create a concise practical day-wise travel itinerary for {d}, {n} days, budget ₹{b}. Include attractions, food, estimated expenses and travel tips. Do not claim live prices.'
  r=requests.post(url,params={'key':key},json={'contents':[{'parts':[{'text':prompt}]}]},timeout=45); r.raise_for_status(); return r.json()['candidates'][0]['content']['parts'][0]['text']
 except Exception:return fallback(d,n,b)
def weather(d):
 key=os.getenv('OPENWEATHER_API_KEY')
 if not key:return {'ok':False,'message':'Add OPENWEATHER_API_KEY for live weather.'}
 try:
  r=requests.get('https://api.openweathermap.org/data/2.5/weather',params={'q':d,'appid':key,'units':'metric'},timeout=15); r.raise_for_status(); x=r.json(); return {'ok':True,'city':x.get('name',d),'temp':round(x['main']['temp'],1),'condition':x['weather'][0]['description'].title(),'humidity':x['main']['humidity']}
 except Exception:return {'ok':False,'message':'Weather unavailable right now.'}
init()
@app.route('/')
def home(): return redirect(url_for('dashboard')) if 'uid' in session else render_template('login.html',signup=False)
@app.route('/signup',methods=['GET','POST'])
def signup():
 if request.method=='POST':
  try:
   c=db(); c.execute('INSERT INTO users(username,password) VALUES(?,?)',(request.form['username'],request.form['password'])); c.commit(); c.close(); flash('Account created. Please log in.'); return redirect('/')
  except sqlite3.IntegrityError: flash('Username already exists.')
 return render_template('login.html',signup=True)
@app.post('/login')
def login():
 c=db(); u=c.execute('SELECT * FROM users WHERE username=? AND password=?',(request.form['username'],request.form['password'])).fetchone(); c.close()
 if not u: flash('Invalid username or password.'); return redirect('/')
 session['uid']=u['id']; session['username']=u['username']; return redirect('/dashboard')
@app.get('/logout')
def logout(): session.clear(); return redirect('/')
@app.route('/dashboard',methods=['GET','POST'])
def dashboard():
 result=w=breakdown=None
 if request.method=='POST' and 'uid' in session:
  d=request.form['destination'].strip(); n=int(request.form['days']); b=float(request.form['budget']); result=itinerary(d,n,b); w=weather(d); breakdown={'Hotel':b*.4,'Food':b*.3,'Travel':b*.2,'Shopping':b*.1}
  c=db(); c.execute('INSERT INTO trips(user_id,destination,days,budget,itinerary,created_at) VALUES(?,?,?,?,?,?)',(session['uid'],d,n,b,result,datetime.now().strftime('%Y-%m-%d %H:%M'))); c.commit(); c.close()
 return render_template('dashboard.html',result=result,weather=w,breakdown=breakdown)
@app.get('/history')
def history():
 if 'uid' not in session:return redirect('/')
 c=db(); rows=c.execute('SELECT * FROM trips WHERE user_id=? ORDER BY id DESC',(session['uid'],)).fetchall(); c.close(); return render_template('history.html',trips=rows)
@app.get('/maps')
def maps():
 from urllib.parse import quote_plus
 return redirect('https://www.google.com/maps/search/?api=1&query='+quote_plus(request.args.get('destination','')))
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)))
