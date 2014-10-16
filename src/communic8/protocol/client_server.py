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
                ('connect',           'not_connected',              'waiting_login'),
                ('disconnect',        '*',                          'disconnected'),
                ('logout',            '*',                          'waiting_login'),
                ('login',             'waiting_login',              'logged_in'),
                ('request_user_list', 'logged_in',                  'logged_in'),
                ('chat_initiate',     'logged_in',                  'chat_waiting_confirmation'),
                ('chat_confirm',      'chat_waiting_confirmation',  'chatting'),
                ('chat_reject',       'chat_waiting_confirmation',  'logged_in'),
                ('chat_ended',        'chatting',                   'logged_in'),
                ('chat_requested',    'logged_in',                  'waiting_user_confirmation'),
                ('chat_accepted',     'waiting_user_confirmation',  'waiting_chat_connection'),
                ('chat_denied',       'waiting_user_confirmation',  'logged_in')
            ]
        })

    def on_message_received(self, message):
        for msg_cls, action in {
            ChatRequested:
                lambda m : self.chat_requested(m.user)
        }.items():
            if isinstance(message, msg_cls):
                action(message)
                return

        #raise MessageError("Unhandled message {0}".format(message.command))

    def on_before_connect(self, event):
        #self.transport.write("Hello, world\n")

        self.send_message(Connect(), lambda r: self.transition())

    def on_leave_not_connected(self, event):
        return False

    def on_after_connect(self, event):
        print 'Connected'
