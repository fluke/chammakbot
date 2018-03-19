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

wrench = u'\U0001F527'
wine = u'\U0001F377'

key = 'AKIAJUS6XG6DKLRZXKJA'
secret = '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'

def bot_api(method_name, method, params):
    path = "https://api.telegram.org/bot545176716:AAFJd0oqTnXxS99MYswmdQiCfdwpfLJkyDA/" + method_name
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
    json_data = json.loads(bot_api('setWebhook', 'POST', {'url': 'https://7855b829.ngrok.io/545176716:AAFJd0oqTnXxS99MYswmdQiCfdwpfLJkyDA'}))
    return str(json_data), 200

@app.route('/545176716:AAFJd0oqTnXxS99MYswmdQiCfdwpfLJkyDA', methods = ['POST'])
def bot():
    """Get bot."""
    webhook = json.loads(request.data)
    logging.info(webhook)
    if 'text' in webhook['message']:
      if webhook['message']['text'].startswith('/quote'):
        # if webhook['message']['from']['id'] != 24135208:
        chammakisms = [('Is this a wrench or a spanner ' + wrench).encode('utf-8'), 'How dare are you.', 'I\'m sitting like an awkward intern', 'Hey Sandesh Is Kartik there', 'I\'m getting stress rashes because of this shit hole', 'You should get her to talk to prajwal about clones and check if she goes mad or not', 'Welcome to monogamy', 'You know I had a doctor called rex. Misdiagnosed me with malaria When I had jaundice', 'I\'m going to go eat my sweet potato in silence', ('Drown sorrow with ' + wine).encode('utf-8')]
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
