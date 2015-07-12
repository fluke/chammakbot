import requests
from flask import Flask
from flask import request
app = Flask(__name__)
app.config['DEBUG'] = True

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

def bot_api(method_name, method, params = {}):
    path = "https://api.telegram.org/bot91678886:AAHpiQP0tCIfeqXKy5zA8BEPHOm7EZOkLCU/" + method_name
    if params
        path += "?"
        for param in params
            path += param + "=" + params[param]
    if method == 'GET'
        return requests.get(path, verify=True).content
    if method == 'POST'
        return requests.post(path, verify=True).content

@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World!'

@app.route('/91678886:AAHpiQP0tCIfeqXKy5zA8BEPHOm7EZOkLCU', methods=['POST'])
def bot():
    """Get bot."""
    return bot_api('getMe', 'GET'), 200

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404
