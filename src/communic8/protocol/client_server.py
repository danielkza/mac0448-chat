import time

from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet.protocol import connectionDone

from communic8.model.user import User
from communic8.model.messages import *
from communic8.protocol import CommonProtocol
from communic8.util import Fysom
from communic8.protocol import simpleserv
from communic8.protocol import simpleclient
from twisted.internet.protocol import DatagramProtocol

class Protocol(CommonProtocol, Fysom, DatagramProtocol):
    async_transitions = {'connect', 'login', 'logout', 'request_user_list'}
    message_dispatcher = MessageDispatcher().register(ChatRequested)

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
        self.f = None

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

    def on_before_connect(self, _):
        def on_response(response):
            if self.check_response_error(response):
                self.log("Connect failed")
                self.cancel_transition()
            else:
                self.log("Connect OK")
                self.transition()

        self.send_message(Connect(), on_response).addErrback(
            lambda _: self.cancel_transition())

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

        self.send_message(Login(event.args[0]), on_response).addErrback(
            lambda _: self.cancel_transition())

    def on_after_login(self, event):
        self.log('Logged in as {0}', event.args[0])

    def _send_logout(self, callback=None):
        def on_response(response):
            if self.check_response_error(response):
                self.log("Logout failed")
            else:
                self.log("Logout")
                self._logout()

        d = self.send_message(Logout(), on_response)
        if callback:
            d.addCallback(callback)

        return d

    def on_before_logout(self, _):
        def on_response(response):
            if self.check_response_error(response):
                self.cancel_transition()
            else:
                self.transition()

        self._send_logout(on_response).addErrback(
            lambda _: self.cancel_transition())

    def _logout(self):
        self.user = None

    def on_after_chat_initiate(self, event):
        user_name = event.args[0]

        def on_response(response):
            if self.check_response_error(response):
                self.log("Error requesting initiation: {0}", response['error'])
                self.chat_reject()
            elif response.get('result:') == 'confirmed':
                host = response['host']
                port = response['port']

                # TODO: connect
                self.log("Initiation accepted, connecting to {0}:{1}", host,
                         port)
                self.chat_confirmed(host, port)
            else:
                self.log("Initiation rejected")
                self.chat_rejected()

        self.send_message(RequestChat(user_name), on_response).addErrback(
            self.chat_rejected
        )

    def on_chat_confirmed(self, event):

        time.sleep(1)
        host = event.args[0]
        port = event.args[1]

        self.f = simpleclient.EchoFactory()
        reactor.connectTCP(host, port, self.f)

    def on_after_request_user_list(self, _):
        def on_response(response):
            if self.check_response_error(response):
                self.log("Couldn't get user list")
                self.cancel_transition()
            else:
                self.log("Received user list")
                for item in response.get('users', []):
                    print ('Name: {item.name}, '
                           'Connected at: {item.connected_at}').format(item)

        self.send_message(ListUsers(), on_response).addErrback(
            lambda _: self.cancel_transition())

    def on_after_chat_requested(self, event):
        user_name = event.args[0]
        self.requesting_user = user_name
        self.log("Received chat request from {0}, waiting for confirmation",
                 user_name)

    def chat_channel_open(self):
        # TODO: actually do it
            self.chat_port = 55555

    def start_chat(self, port):
            if not self.is_transport_udp():
                factory = protocol.ServerFactory()
                factory.protocol = simpleserv.Echo
                reactor.listenTCP(port,factory)

    def chat_channel_close(self):
        # TODO: actually do it
        self.chat_port = None
        pass

    def on_enter_waiting_connection(self, _):
        try:
            self.chat_channel_open()
        except Exception:
            self.log("Failed to open chat channel")

    def on_leave_waiting_connection(self, _):
        self.chat_channel_close()

    def on_leave_chatting(self, _):
        self.chat_channel_close()

    def on_after_chat_confirm(self, _):
        #if not self.chat_channel:
        #    self.chat_reject()
        #    return

        self.log("Confirmed chat request for {0} on port {1}",
                 self.requesting_user, self.chat_port)
        self.requesting_user = None

        self.send_response({'result': 'confirmed', 'port': self.chat_port})
        self.start_chat(self.chat_port)

    def on_after_chat_reject(self, _):
        self.log("Rejecting chat request for {0}", self.requesting_user)
        self.requesting_user = None

        self.send_response({'result': 'rejected'})

    def on_enter_done(self, _):
        if not self.transport_connected:
            return

        def send_quit():
            return self.send_message(Quit()).addBoth(
                self.transport.loseConnection)

        if self.user:
            self._send_logout().addBoth(send_quit)
        else:
            send_quit()

    def connectionMade(self):
        self.connect()

    def connectionLost(self, reason=connectionDone):
        self.cancel_transition()
        self.disconnect()


class Factory (protocol.ClientFactory):
    protocol = Protocol


    def __init__(self):
        self.message_dispatcher = MessageDispatcher().register(
         ChatRequested
        )

        self.instances = []

    def buildProtocol(self, addr):
        proto = protocol.ClientFactory.buildProtocol(self, addr)
        self.instances.append(proto)
        return proto

class FactoryUDP(DatagramProtocol):
    protocol = DatagramProtocol

    def __init__(self):
        self.message_dispatcher = MessageDispatcher().register(
         ChatRequested,
        )

        self.instances = []

    def startProtocol(self):
        self.transport.connect('127.0.0.1', 8125)
        proto = protocol.DatagramProtocol.startProtocol(self)
        self.instances.append(proto)
        return proto