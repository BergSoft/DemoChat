import collections
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

define('port', default=8888, help='run on the given port', type=int)
define('address', default='127.0.0.1', help='run on the given address', type=str)

class Application(tornado.web.Application):
    def __init__(self, **kwargs):
        self.db = collections.deque(maxlen=25)
        handlers = [
                (r'/', MainHandler),
                (r'/send', AddHandler),
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
        self.render('index.html', messages=self.application.db)


class AddHandler(tornado.web.RequestHandler):
    def post(self):
        logging.info('Post message')
        self.write('Your browser doesn\'t support JavaScript or WebSockets.');


class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = collections.defaultdict(set)

    def send_message(self, msg):
        logging.info('Sending message to %d waiters',
                     len(ChatSocketHandler.waiters[self.channel]))
        for waiter in ChatSocketHandler.waiters[self.channel]:
            try:
                waiter.write_message(msg)
            except:
                logging.error('Error sending message', exc_info=True)

    def send_online(self):
        msg = {
            'type': 'online',
            'count': len(ChatSocketHandler.waiters[self.channel]),
        }
        self.send_message(msg)

    def on_message(self, message):
        logging.info('Got message %r', message)
        parsed = tornado.escape.json_decode(message)
        type = parsed.get('type')
        if not type in ['connected', 'message']:
            return
        if type == 'connected':
            self.on_connect(parsed)
        elif type == 'message':
            if getattr(self, 'channel', None) is not None:
                self.on_msg(parsed)

    def on_connect(self, parsed):
        self.channel = parsed['channel']
        ChatSocketHandler.waiters[self.channel].add(self)
        logging.info('Add waiter to %s' % self.channel)
        self.send_online()

    def on_close(self):
        if getattr(self, 'channel', None) is not None:
            ChatSocketHandler.waiters[self.channel].remove(self)
            logging.info('Remove waiter from %s' % self.channel)
            self.send_online()

    def on_msg(self, parsed):
        text = unicode(parsed['body']).strip()
        if len(text) < 1:
            return
        msg = {
            'id': str(uuid4()),
            'body': text[:1024],
            'time': time.time(),
            'type': 'message',
        }
        if self.request.remote_ip == '127.0.0.1':
            msg['author'] = 'Admin'
        msg['html'] = self.render_string('message.html', message=msg)
        self.application.db.append(msg)
        self.send_message(msg)


def main():
    tornado.options.parse_command_line()
    app = Application(debug=False)
    app.listen(options.port, options.address)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
