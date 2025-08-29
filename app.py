from flask import Flask, request, redirect, render_template_string, url_for
import sqlite3
import string
import random

app = Flask(__name__)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    long_url TEXT NOT NULL,
                    short_code TEXT NOT NULL UNIQUE
                )""")
    conn.commit()
    conn.close()

init_db()

# --- Helper function: Generate random short code ---
def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# --- API Endpoint: Create Short URL ---
@app.route('/shorten', methods=['POST'])
def shorten():
    # Accept from HTML form or JSON
    json_data = request.get_json(silent=True) or {}
    long_url = request.form.get('url') or json_data.get('url')
    if not long_url:
        # If the request is from a browser form, show a friendly page
        if request.content_type and 'application/json' not in request.content_type:
            return render_template_string("""
            <h2>Missing URL</h2>
            <p>Please provide a URL to shorten.</p>
            <p><a href="/">Go back</a></p>
            """), 400
        return {"error": "URL is required"}, 400

    # Generate unique short code
    short_code = generate_short_code()
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO urls (long_url, short_code) VALUES (?, ?)", (long_url, short_code))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"error": "Short code already exists"}, 500
    conn.close()

    short_url = request.host_url + short_code

    # If submitted via HTML form, render a result page
    if request.content_type and 'application/json' not in request.content_type:
        return render_template_string(
            """
            <h2>Short URL Created</h2>
            <p><strong>Original:</strong> <a href="{{ long_url }}" target="_blank">{{ long_url }}</a></p>
            <p><strong>Short:</strong> <a href="/{{ code }}" target="_blank">{{ host }}{{ code }}</a></p>
            <p>
                <a href="/">Create another</a> ·
                <a href="/list">View recent</a>
            </p>
            """,
            long_url=long_url,
            code=short_code,
            host=request.host_url,
        )

    # Otherwise return JSON
    return {"short_url": short_url, "long_url": long_url}

# --- Redirect Route ---
@app.route('/<short_code>')
def redirect_url(short_code):
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("SELECT long_url FROM urls WHERE short_code = ?", (short_code,))
    row = c.fetchone()
    conn.close()
    if row:
        return redirect(row[0])
    else:
        return {"error": "URL not found"}, 404

# --- Optional Frontend ---
@app.route('/')
def home():
    html = """
    <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;max-width:720px;margin:40px auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px">
      <h2 style="margin:0 0 16px 0">Simple URL Shortener</h2>
      <form method="POST" action="/shorten" style="display:flex;gap:8px">
        <input type="url" name="url" placeholder="Enter long URL" style="flex:1;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px" required>
        <button type="submit" style="padding:10px 14px;border:0;background:#2563eb;color:white;border-radius:8px;cursor:pointer">Shorten</button>
      </form>
      <p style="margin-top:12px;font-size:14px;color:#475569">
        You can also POST JSON to <code>/shorten</code> with {"url": "https://..."}
      </p>
      <p style="margin-top:8px"><a href="/list">View recent links</a></p>
    </div>
    """
    return render_template_string(html)

# --- List recent URLs ---
@app.route('/list')
def list_urls():
    conn = sqlite3.connect("urls.db")
    c = conn.cursor()
    c.execute("SELECT long_url, short_code FROM urls ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return render_template_string(
        """
        <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;max-width:800px;margin:40px auto;padding:24px">
          <h2 style="margin:0 0 16px 0">Recent Shortened URLs</h2>
          <p><a href="/">Create new</a></p>
          {% if rows %}
          <table style="width:100%;border-collapse:collapse">
            <thead>
              <tr>
                <th style="text-align:left;border-bottom:1px solid #e5e7eb;padding:8px">Short</th>
                <th style="text-align:left;border-bottom:1px solid #e5e7eb;padding:8px">Destination</th>
              </tr>
            </thead>
            <tbody>
              {% for long_url, code in rows %}
              <tr>
                <td style="border-bottom:1px solid #f1f5f9;padding:8px">
                  <a href="/{{ code }}" target="_blank">{{ host }}{{ code }}</a>
                </td>
                <td style="border-bottom:1px solid #f1f5f9;padding:8px;word-break:break-all">
                  <a href="{{ long_url }}" target="_blank">{{ long_url }}</a>
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
          {% else %}
            <p>No URLs yet.</p>
          {% endif %}
        </div>
        """,
        rows=rows,
        host=request.host_url,
    )

if __name__ == '__main__':
    app.run(debug=True)
