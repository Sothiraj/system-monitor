from flask import Flask, render_template, jsonify
from utils.monitor import get_stats

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/stats')
def stats():
    return jsonify(get_stats())

if __name__ == '__main__':
    app.run(debug=True)
