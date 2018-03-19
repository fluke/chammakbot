import json
import os
import sys
import logging
import random
here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, "./vendored"))

import requests

TOKEN = os.environ['TELEGRAM_TOKEN']
BASE_URL = "https://api.telegram.org/bot{}/".format(TOKEN)

def bot_api(method_name, method, params):
    path = BASE_URL + method_name
    if params:
        path += "?"
        for param in params:
            path += param + "=" + str(params[param]) + "&"
        path = path[:-1]

    if method == 'GET':
        return requests.get(path, verify=True).text
    if method == 'POST':
        return requests.post(path, verify=True).text

def quote(event, context):
    try:
        webhook = json.loads(event["body"])
        logging.info(webhook)
        if 'text' in webhook['message']:
          if webhook['message']['text'].startswith('/quote'):
            # if webhook['message']['from']['id'] != 24135208:
            chammakisms = ['Lovely dinner with special', 'You wanna come see my coffee machine?', 'I\'m so important that people want me killed.. yo!', "Hi. I'm roll number 2.", "You are too cool for me Khushboo Sharma!! You are too awesome for me! :'(", 'Let me be your Chammak Challo', 'A coffee machine is a good investment', 'The cloud bro', 'I don\'t go to shady places', 'I can\'t sleep without the AC', 'I wish Mallika would like me.', '*snakes hand in between you and a girl*', 'I have a patent in the US.', 'It\'s all dynamic bro']
            params = {'chat_id': webhook['message']['chat']['id'], 'text': chammakisms[random.randint(1, len(chammakisms)) - 1]}
            json_data = json.loads(bot_api('sendMessage', 'GET', params))

    except Exception as e:
        print(e)

    return {"statusCode": 200}