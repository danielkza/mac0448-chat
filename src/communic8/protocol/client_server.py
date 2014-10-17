from twisted.internet import defer, reactor, task
from twisted.internet import protocol

from communic8.model.user import User
from communic8.model.messages import *
from communic8.protocol import CommonProtocol
from communic8.util import Fysom


class ClientServerProtocol(CommonProtocol, Fysom):
    async_transitions = {'connect', 'login', 'logout', 'request_user_list',
                         'chat_initiate'}

    def __init__(self):
        CommonProtocol.__init__(self)
        Fysom.__init__(self, {
            'initial': 'not_connected',
            'events': [
                # event / from / to
                ('connect',           'not_connected',             'waiting_login'),
                ('disconnect',        '*',                         'done'),
                ('login',             'waiting_login',             'logged_in'),
                ('logout',            '*',                         'waiting_login'),
                ('request_user_list', 'logged_in',                 'logged_in'),
                ('chat_initiate',     'logged_in',                 'chat_waiting_confirmation'),
                ('chat_confirm',      'chat_waiting_confirmation', 'chatting'),
                ('chat_reject',       'chat_waiting_confirmation', 'logged_in'),
                ('chat_ended',        'chatting',                  'logged_in'),
                ('chat_requested',    'logged_in',                 'waiting_user_confirmation'),
                ('chat_accepted',     'waiting_user_confirmation', 'waiting_chat_connection'),
                ('chat_denied',       'waiting_user_confirmation', 'logged_in')
            ]
        })

        self.user = None
        self.factory = None

    @property
    def message_dispatcher(self):
        return self.factory.message_dispatcher

    def on_message_received(self, message):
        for msg_cls, action in {
            ChatRequested:
                lambda m: self.chat_requested(m.user)
        }.items():
            if isinstance(message, msg_cls):
                action(message)
                return

        #raise MessageError("Unhandled message {0}".format(message.command))

    def on_before_connect(self, event):
        def on_response(response):
            if self.check_response_error(response):
                self.cancel_transition()
            else:
                self.transition()

        self.send_message(Connect(), on_response)

    def on_before_login(self, event):
        def on_response(response):
            if self.check_response_error(response):
                self.cancel_transition()
            else:
                user = response['user']
                self.user = User(user['name'], user['host'], user['port'],
                                 user['connected_at'])
                self.transition()

        self.send_message(Login(event.args[0]), on_response)

    def on_enter_logged_in(self, event):
        print 'Logged in as {0}'.format(event.args[0])

    def on_before_logout(self, event):
        def on_response(response):
            if self.check_response_error(response):
                self.log("Logout failed (unexpected)")
                self.cancel_transition()
            else:
                self.log("Logout")
                self._logout()
                self.transition()

        self.send_message(Logout(), on_response)

    def _logout(self):
        self.user = None

    def on_enter_done(self, event):
        self._logout()
        self.transport.loseConnection()

    @defer.inlineCallbacks
    def start(self):
        yield self.defer_event(0, self.connect)
        print self.current

        yield self.defer_event(0, self.login, 'test_user')
        print self.current

        yield self.defer_event(5, self.logout)
        print self.current

        yield self.defer_event(0, self.disconnect)
        print self.current

    def connectionMade(self):
        self.start()


class ClientServerFactory(protocol.ClientFactory):
    protocol = ClientServerProtocol

    def __init__(self):
        self.message_dispatcher = MessageDispatcher().register(
            ChatRequested
        )
