import requests
import random
import json
import logging
from flask import Flask
from flask import request
app = Flask(__name__)
app.config['DEBUG'] = True

# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

def bot_api(method_name, method, params):
    path = "https://api.telegram.org/bot91678886:AAHpiQP0tCIfeqXKy5zA8BEPHOm7EZOkLCU/" + method_name
    if params:
        path += "?"
        for param in params:
            path += param + "=" + str(params[param]) + "&"
        path = path[:-1]

    if method == 'GET':
        return requests.get(path, verify=True).text
    if method == 'POST':
        return requests.post(path, verify=True).text

@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    json_data = json.loads(bot_api('setWebhook', 'POST', {'url': 'https://99ec3070.ngrok.io/91678886:AAHpiQP0tCIfeqXKy5zA8BEPHOm7EZOkLCU'}))
    return str(json_data), 200

@app.route('/91678886:AAHpiQP0tCIfeqXKy5zA8BEPHOm7EZOkLCU', methods = ['POST'])
def bot():
    """Get bot."""
    webhook = json.loads(request.data)
    logging.info(webhook)
    if 'text' in webhook['message']:
      if webhook['message']['text'].startswith('/quote'):
        # if webhook['message']['from']['id'] != 24135208:
        chammakisms = ['Lovely dinner with special', 'You wanna come see my coffee machine?', 'I\'m so important that people want me killed.. yo!', "Hi. I'm roll number 2.", "You are too cool for me Khushboo Sharma!! You are too awesome for me! :'(", 'Let me be your Chammak Challo', 'A coffee machine is a good investment', 'The cloud bro', 'I don\'t go to shady places', 'I can\'t sleep without the AC', 'I wish Mallika would like me.', '*snakes hand in between you and a girl*', 'I have a patent in the US.', 'It\'s all dynamic bro']
        params = {'chat_id': webhook['message']['chat']['id'], 'text': chammakisms[random.randint(1, len(chammakisms)) - 1]}
        json_data = json.loads(bot_api('sendMessage', 'GET', params))
        return str(json_data), 200
      else: 
        return 'Not a command', 200
    else:
      return 'Not a command', 200

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, nothing at this URL.', 404
