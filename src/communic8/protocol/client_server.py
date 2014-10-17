from twisted.internet import reactor
from twisted.internet import protocol

from communic8.model.user import User
from communic8.model.messages import *
from communic8.protocol import CommonProtocol
from communic8.util import Fysom


class ClientServerProtocol(CommonProtocol, Fysom):
    def __init__(self):
        CommonProtocol.__init__(self)
        Fysom.__init__(self, {
            'initial': 'not_connected',
            'events': [
                # event / from / to
                ('connect',           'not_connected',             'waiting_login'),
                ('disconnect',        '*',                         'done'),
                ('logout',            '*',                         'waiting_login'),
                ('login',             'waiting_login',             'logged_in'),
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
            print 'on_response_1'
            if self.check_response_error(response):
                print 'Error'
            else:
                self.transition()

        self.send_message(Connect(), on_response)

    def on_leave_not_connected(self, event):
        return False

    def on_after_connect(self, event):
        print 'on-after-connect', self.current
        self.login('test_user')
        reactor.callLater(5, self.logout)

    def on_before_login(self, event):
        def on_response(response):
            if self.check_response_error(response):
                print 'Error'
            else:
                user = response['user']
                self.user = User(user['name'], user['host'], user['port'],
                                 user['connected_at'])
                self.transition()

        self.send_message(Login(event.args[0]), on_response)

    def on_leave_waiting_login(self, event):
        return False

    def on_enter_logged_in(self, event):
        print 'Logged in as {0}'.format(event.args[0])

    def on_after_logout(self, event):
        self.send_message(Logout(), lambda r: None)
        self._logout()

    def _logout(self):
        self.user = None

    def on_enter_done(self, event):
        self._logout()
        self.transport.loseConnection()

    def connectionMade(self):
        self.connect()


class ClientServerFactory(protocol.ClientFactory):
    protocol = ClientServerProtocol

    def __init__(self):
        self.message_dispatcher = MessageDispatcher().register(
            ChatRequested
        )
