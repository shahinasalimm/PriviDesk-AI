from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
from transformers import pipeline
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'privydesk_secret_key'

# Load Hugging Face sentiment model
sentiment_pipeline = pipeline("sentiment-analysis")

# HR Credentials
HR_USERNAME = 'hr'
HR_PASSWORD = 'admin123'

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    department TEXT,
                    sentiment TEXT,
                    date TEXT
                )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

@app.route('/submit', methods=['POST'])
def submit():
    department = request.form['department']
    feedback = request.form['feedback']

    result = sentiment_pipeline(feedback)[0]
    label = result['label']

    if label == 'POSITIVE':
        sentiment = 'Positive'
    else:
        sentiment = 'Negative'

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO submissions (department, sentiment, date) VALUES (?, ?, ?)',
              (department, sentiment, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()

    return redirect('/thankyou')

@app.route('/thankyou')
def thankyou():
    return render_template('thankyou.html')

@app.route('/hr', methods=['GET', 'POST'])
def hr_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == HR_USERNAME and password == HR_PASSWORD:
            session['hr_logged_in'] = True
            return redirect('/dashboard')
        else:
            return 'Invalid HR Credentials! Try again.'

    return render_template('hr_login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('hr_logged_in'):
        return redirect('/hr')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT department, sentiment, COUNT(*) FROM submissions GROUP BY department, sentiment')
    data = c.fetchall()
    conn.close()

    summary = {}
    department_totals = {}
    for dept, sentiment, count in data:
        if dept not in summary:
            summary[dept] = {'Positive': 0, 'Negative': 0}
            department_totals[dept] = 0
        summary[dept][sentiment] += count
        department_totals[dept] += count

    # Burnout Detection: If more than 50% Negative
    alerts = []
    for dept in summary:
        total = department_totals[dept]
        negative = summary[dept]['Negative']
        if total > 0 and (negative / total) > 0.5:
            alerts.append(dept)

    return render_template('dashboard.html', summary=summary, alerts=alerts)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/hr')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
