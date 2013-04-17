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
                (r'/count', CountHandler),
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


class CountHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(str(len(ChatSocketHandler.waiters)))


class AddHandler(tornado.web.RequestHandler):
    def post(self):
        logging.info('Post message')
        self.write('Your browser doesn\'t support JavaScript or WebSockets.');


class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    ban_ips = set()

    def open(self):
        ChatSocketHandler.waiters.add(self)
        logging.info('Add waiter')

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)
        logging.info('Remove waiter')

    def on_message(self, message):
        logging.info('Got message %r', message)
        parsed = tornado.escape.json_decode(message)
        text = unicode(parsed['body']).strip()
        if len(text) < 1:
            return
        chat = {
            'id': str(uuid4()),
            'body': text[:1024],
            'time': time.time(),
        }
        if self.request.remote_ip == '127.0.0.1':
            chat['author'] = 'Admin'
        chat['html'] = self.render_string('message.html', message=chat)
        self.application.db.append(chat)
        logging.info('Sending message to %d waiters', len(ChatSocketHandler.waiters))
        for waiter in ChatSocketHandler.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error('Error sending message', exc_info=True)


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
