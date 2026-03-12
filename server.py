from flask import Flask, send_from_directory
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

@app.route('/terms-of-service')
def terms():
    return send_from_directory('static', 'terms.html')

@app.route('/privacy-policy')
def privacy():
    return send_from_directory('static', 'privacy.html')

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()