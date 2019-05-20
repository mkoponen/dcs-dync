import requests
import json
import logging

logger = logging.getLogger('general')


class MessageService:
    @staticmethod
    def hook_post_message(username, message, url):
        headers = {
            'Content-Type': 'application/json',
        }
        payload = {
            'username': username,
            'content': message
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        logger.info('Request got response: %s' % repr(response))
        return
