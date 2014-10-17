from twisted.internet import defer, reactor, task
from twisted.internet import protocol

from communic8.model.user import User
from communic8.model.messages import *
from communic8.protocol import CommonProtocol
from communic8.util import Fysom


class ChatChannelError(RuntimeError):
    pass


class ClientServerProtocol(CommonProtocol, Fysom):
    async_transitions = {'connect', 'login', 'logout', 'request_user_list',
                         'chat_initiate'}

    def __init__(self):
        CommonProtocol.__init__(self)
        Fysom.__init__(self, initial='not_connected', events=[
            # event / from / to
            ('connect',
                'not_connected', 'waiting_login'),
            ('disconnect',
                '*', 'done'),
            ('login',
                'waiting_login', 'logged_in'),
            ('logout',
                '*', 'waiting_login'),
            ('request_user_list',
                'logged_in', 'logged_in'),
            ('chat_initiate',
                'logged_in', 'waiting_server_confirmation'),
            ('chat_confirmed',
                'waiting_server_confirmation', 'starting_connection'),
            ('chat_rejected',
                'waiting_server_confirmation', 'logged_in'),
            ('chat_connect',
                'starting_connection', 'chatting'),
            ('chat_requested',
                'logged_in', 'waiting_user_confirmation'),
            ('chat_confirm',
                'waiting_user_confirmation', 'waiting_connection'),
            ('chat_reject',
                ['waiting_user_confirmation', 'waiting_connection'],
                'logged_in'),
            ('chat_wait_timeout',
                'waiting_connection', 'logged_in'),
            ('chat_connected',
                'waiting_connection', 'chatting'),
            ('chat_ended',
                'chatting', 'logged_in'),
        ])

        self.user = None
        self.factory = None
        self.requesting_user = None
        self.chat_channel = None
        self.chat_port = None

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
                self.log("Connect failed")
                self.cancel_transition()
            else:
                self.log("Connect OK")
                self.transition()

        self.send_message(Connect(), on_response)

    def on_before_login(self, event):
        def on_response(response):
            if self.check_response_error(response):
                self.log("Login failed")
                self.cancel_transition()
            else:
                user = response['user']
                self.user = User(user['name'], user['host'], user['port'],
                                 user['connected_at'])
                self.transition()

        self.send_message(Login(event.args[0]), on_response)

    def on_enter_logged_in(self, event):
        self.log('Logged in as {0}', event.args[0])

    def on_before_logout(self, event):
        def on_response(response):
            if self.check_response_error(response):
                self.log("Logout failed")
                self.cancel_transition()
            else:
                self.log("Logout")
                self._logout()
                self.transition()

        self.send_message(Logout(), on_response)

    def _logout(self):
        self.user = None

    def on_after_chat_initiated(self, event):
        user_name = event.args[0]

        def on_response(response):
            if self.check_response_error(response):
                self.log("Error requesting initiation: {0}", response['error'])
                self.chat_reject()
            elif response.get('result') == 'accepted':
                host = response['host']
                port = response['port']

                # TODO: connect
                self.log("Initiation accepted, connecting to {0}:{1}", host,
                         port)
                self.chat_confirmed(host, port)
            else:
                self.log("Initiation rejected")
                self.chat_rejected()

        self.send_message(RequestChat(user_name), on_response)

    def on_after_request_user_list(self, event):
        def on_response(response):
            if self.check_response_error(response):
                self.log("Couldn't get user list")
                self.cancel_transition()
            elif response.get('result:') == 'ok':
                self.log("Received user list")

        self.send_message(ListUsers(), on_response)

    def on_after_chat_requested(self, event):
        user_name = event.args[0]
        self.requesting_user = user_name
        self.log("Received chat request from {0}, waiting for confirmation",
                 user_name)

        # TODO: wait for confirmation
        # self.chat_confirm()

    def chat_channel_open(self):
        # TODO: actually do it
        return 55555

    def chat_channel_close(self):
        # TODO: actually do it
        pass

    def on_enter_waiting_connection(self, event):
        try:
            self.chat_channel_open()
        except Exception:
            self.log("Failed to open chat channel")

    def on_leave_waiting_connection(self, event):
        self.chat_channel_close()

    def on_leave_chatting(self, event):
        self.chat_channel_close()

    def on_after_chat_confirm(self, event):
        if not self.chat_channel:
            self.chat_reject()
            return

        self.log("Confirmed chat request for {0} on port {1}",
                 self.requesting_user, self.chat_port)
        self.requesting_user = None

        self.send_response({'result': 'confirmed', 'port': self.chat_port})

    def on_after_chat_reject(self, event):
        self.log("Rejecting chat request for {0}", self.requesting_user)
        self.requesting_user = None

        self.send_response({'result': 'rejected'})

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
        self.instances = []

    def buildProtocol(self, addr):
        proto = protocol.ClientFactory.buildProtocol(self, addr)
        self.instances.append(proto)
        return proto


