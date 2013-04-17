import logging
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
import os.path
import time

from tornado.options import define, options
from uuid import uuid4
from collections import defaultdict, deque
from functools import partial

define('debug', default=False, help='enable debug', type=bool)
define('port', default=8888, help='run on the given port', type=int)
define('address', default='127.0.0.1', help='run on the given address', type=str)

class Application(tornado.web.Application):
    def __init__(self, **kwargs):
        self.db = defaultdict(partial(deque, maxlen=25))
        handlers = [
                (r'/', MainHandler),
                (r'/socket', ChatSocketHandler)
        ]
        settings = dict(
            cookie_secret='nIgZ4V53+K6plun2hq3NMFlJe30dtXtrpvSslYr0t50=',
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            xsrf_cookies=True,
            autoescape=None,
            debug=False,
        )
        settings.update(kwargs)
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('index.html')

    def post(self):
        self.write("Your browser doesn't support JavaScript or WebSockets.")


class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = defaultdict(set)

    @property
    def channel_waiters(self):
        return ChatSocketHandler.waiters[self.channel]

    @property
    def channel_messages(self):
        return self.application.db[self.channel]

    def send(self, msg):
        try:
            self.write_message(msg)
        except:
            logging.error('Error sending message', exc_info=True)

    def send_last(self):
        msg = {
            'type': 'last',
            'last': list(self.channel_messages),
        }
        self.send(msg)

    def channel_send(self, msg):
        logging.info('Sending message to %d waiters', len(self.channel_waiters))
        for waiter in self.channel_waiters:
            waiter.send(msg)

    def channel_send_online(self):
        msg = {
            'type': 'online',
            'count': len(self.channel_waiters),
        }
        self.channel_send(msg)

    def on_connect(self, parsed):
        self.nickname = parsed.get('nickname', '').strip()[:16]
        self.nickname = self.nickname or u'Anonymous'
        self.channel = parsed['channel']
        self.channel_waiters.add(self)
        logging.info('Add waiter to %s' % self.channel)
        self.channel_send_online()
        self.send_last()

    def on_close(self):
        if getattr(self, 'channel', None) is not None:
            self.channel_waiters.remove(self)
            logging.info('Remove waiter from %s' % self.channel)
            self.channel_send_online()

    def on_msg(self, parsed):
        body = parsed.get('body', '').strip()[:8192]
        if len(body) < 1:
            return
        msg = {
            'id': str(uuid4()),
            'author': self.nickname,
            'body': body,
            'time': time.time(),
            'type': 'message',
            'is_admin': self.request.remote_ip == '127.0.0.1',
        }
        msg['html'] = self.render_string('message.html', message=msg)
        self.channel_messages.append(msg)
        self.channel_send(msg)

    def on_message(self, message):
        parsed = tornado.escape.json_decode(message)
        logging.info('Got message %r', parsed)
        type = parsed.get('type')
        if not type in ['connected', 'message']:
            return
        if type == 'connected' and parsed.get('channel') is not None:
            self.on_connect(parsed)
        elif type == 'message':
            if getattr(self, 'channel', None) is not None:
                self.on_msg(parsed)


def main():
    tornado.options.parse_command_line()
    app = Application(debug=options.debug)
    app.listen(options.port, options.address)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
