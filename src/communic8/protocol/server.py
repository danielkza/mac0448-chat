from twisted.internet import protocol, task, reactor
from twisted.python import log

from communic8.model.user import User, UserDatabase, UserNameAlreadyUsed, \
    AddressAlreadyUsed, UserDatabaseError
from communic8.model.messages import *
from communic8.protocol import CommonProtocol
from communic8.util import Fysom


class Protocol(CommonProtocol, Fysom):
    ERROR_MESSAGES = {
        'LOGIN_FAILED_USER_NAME_TAKEN': "An user with name '{name}' is already logged in",
        'LOGIN_FAILED_ADDRESS_IN_USE': "An user with address {host}:{port!d} is already logged in",
        'LOGIN_FAILED': "Login failed for unknown reasons"
    }

    def __init__(self):
        CommonProtocol.__init__(self)
        Fysom.__init__(self, {
            'initial': 'waiting_connection',
            'events': [
                # event / from / to
                ('connect',               'waiting_connection',               'waiting_login'),
                ('disconnect',            '*',                                'disconnected'),
                ('logout',                '*',                                'waiting_login'),
                ('login',                 'waiting_login',                    'logged_in'),
                ('send_user_list',        'logged_in',                        'logged_in'),
                ('chat_initiate',         'logged_in',                        'chat_waiting_confirmation'),
                ('chat_ask_confirmation', 'logged_in',                        'chat_waiting_client_confirmation'),
                ('chat_confirm',          'chat_waiting_confirmation',        'chatting'),
                ('chat_reject',           'chat_waiting_confirmation',        'logged_in'),
                ('chat_client_confirm',   'chat_waiting_client_confirmation', 'chatting'),
                ('chat_client_reject',    'chat_waiting_client_confirmation', 'logged_in'),
                ('ending_chat',           'chatting',                         'logged_in'),
                ('chat_finished',         'chatting',                         'logged_in')
            ]
        })

        self.factory = None
        self.user = None

    @property
    def user_database(self):
        return self.factory.user_database

    @property
    def message_dispatcher(self):
        return self.factory.message_dispatcher

    def on_message_received(self, message):
        for msg_cls, action in {
            Connect:
                lambda m: self.connect(),
            Login:
                lambda m: self.login(m.user),
            Quit:
                lambda m: self.transport.loseConnection(),
            Logout:
                lambda m: self.logout(),
            ListUsers:
                lambda m: self.send_user_list(),
            RequestChat:
                lambda m: self.chat_initiate(m.user),
            AcceptChat:
                lambda m: self.chat_client_confirm(m.user, m.port),
            RejectChat:
                lambda m: self.chat_client_reject(m.user),
            EndChat:
                lambda m : self.ending_chat(m.user)
        }.items():
            if isinstance(message, msg_cls):
                action(message)
                return

        raise MessageError("Unhandled message {0}".format(message.command))


    def on_after_connect(self, event):
        self.send_response({})

    def on_before_login(self, event):
        user_name = event.args[0]
        address = self.transport.getPeer()
        host, port = address.host, address.port

        try:
            self.user = self.user_database.add(user_name, host, port)
        except UserNameAlreadyUsed:
            self.send_error_response('LOGIN_FAILED_USER_NAME_TAKEN',
                                     name=user_name)
        except AddressAlreadyUsed:
            self.send_error_response('LOGIN_FAILED_ADDRESS_IN_USE', host=host,
                                     port=port)
        except UserDatabaseError:
            self.send_error_response('LOGIN_FAILED')
        else:
            self.factory.set_protocol_user(self, user_name)
            return True

        return False

    def on_after_login(self, event):
        self.log("Login successful as '{user}'", user=self.user.name)

        self.send_response({
            'user': {'name': self.user.name, 'host': self.user.host,
                     'port': self.user.port,
                     'connected_at': self.user.connected_at.isoformat()}
        })

    def on_before_logout(self, event):
        if self.user is None:
            return False

        return True

    def _logout(self):
        if self.user:
            self.user_database.remove(self.user.name)
            self.factory.remove_protocol_user(self.user.name)

        self.user = None

    def on_after_logout(self, event):
        self._logout()
        self.send_response({})

    def on_enter_disconnected(self, event):
        if self.transport_connected:
            self.transport.loseConnection()

        self._logout()

    def on_send_user_list(self, event):
        users = []
        for user in self.user_database.users():
            users.append({'name': user.name, 'connected_at': user.connected_at.isoformat()})

        self.send_response({"users:": users})

    def on_before_chat_initiate(self, event):
        user_name = event.args[0]

        self.log("Attempted chat initiation from {from_name} to {to_name}", from_name=self.user.name, to_name=user_name)

        if user_name == self.user.name:
            self.send_error_response("CANNOT_CHAT_WITH_SELF")
        else:
            user_proto = self.factory.get_user_protocol(user_name)
            if not user_proto:
                self.send_error_response("USER_NOT_LOGGED_IN", user_name=user_name)
            elif user_proto.current != 'logged_in':
                self.send_error_response("USER_NOT_AVAILABLE", user_name=user_name)
            else:
                return True

        return False

    def on_chat_initiate(self, event):
        user_name = event.args[0]
        user_proto = self.factory.get_user_protocol(user_name)
        assert user_proto is not None

        d = task.deferLater(reactor, 0, user_proto.chat_ask_confirmation, self.user.name)

        def handle_error(error):
            print str(error)
            print error.getTraceback()

        d.addErrback(handle_error)

    def on_chat_ask_confirmation(self, event):
        user_name = event.args[0]
        self.log("Sending chat confirmation from {from_name} to {to_name}", from_name=user_name, to_name=self.user.name)

        self.send_message(ChatRequested(user_name))

    def on_chat_client_confirm(self, event):
        user_name = event.args[0]
        user_chat_port = event.args[1]
        user_proto = self.factory.get_user_protocol(user_name)
        assert  user_proto is not None
        self.log("Sent client confirmation for {user_name}", user_name =user_name)

        d = task.deferLater(reactor, 0, user_proto.chat_confirm, [self.user.name, user_chat_port])

        def handle_error(error):
            print str(error)
            print error.getTraceback()

        d.addErrback(handle_error)

    def on_chat_client_reject(self, event):

        user_name = event.args[0]
        user_proto = self.factory.get_user_protocol(user_name)
        assert  user_proto is not None

        self.log("Sent client rejection for {user_name}", user_name = user_name)

        d = task.deferLater(reactor, 0, user_proto.chat_reject, self.user.name)

        def handle_error(error):
            print str(error)
            print error.getTraceback()

        d.addErrback(handle_error)


    def on_chat_confirm(self, event):
        user_name = event.args[0][0]
        user_chat_port = event.args[0][1]
        user_proto = self.factory.get_user_protocol(user_name)
        assert  user_proto is not None

        self.log("Received chat confirmation from {from_name} to {to_name}", from_name=self.user.name, to_name=user_name)
        self.send_message(ChatAccepted(self.user.name, self.user.host, user_chat_port))


    def on_chat_reject(self, event):
        user_name = event.args[0]
        user_proto = self.factory.get_user_protocol(user_name)
        assert  user_proto is not None

        self.log("Received chat rejection from {from_name} to {to_name}", from_name=self.user.name, to_name=user_name)
        self.send_message(ChatRejected(self.user.name))

    def on_ending_chat(self, event):
        user_name = event.args[0]
        user_proto = self.factory.get_user_protocol(user_name)
        assert  user_proto is not None

        self.log("Ending chat from {from_name} to {to_name}", from_name=self.user.name, to_name=user_name)

        d = task.deferLater(reactor, 0, user_proto.chat_finished, self.user.name)

    def connectionMade(self):
        self.transport_connected = True

    def connectionLost(self, reason=protocol.connectionDone):
        self.transport_connected = False
        self.disconnect()


class Factory(protocol.ServerFactory):
    protocol = Protocol

    def __init__(self):
        self.user_database = UserDatabase()
        self.message_dispatcher = MessageDispatcher().register(
            Connect, Quit,
            Login, Logout,
            ListUsers,
            RequestChat, ChatRequested,
            AcceptChat, ChatAccepted,
            RejectChat, ChatRejected,
            EndChat,
        )
        self.user_protocols = {}

    def set_protocol_user(self, user_protocol, user_name):
        self.user_protocols[user_name] = user_protocol

    def remove_protocol_user(self, user_name):
        del self.user_protocols[user_name]

    def get_user_protocol(self, user_name, default=None):
        return self.user_protocols.get(user_name, default)

    def buildProtocol(self, address):
        if self.user_database.get_by_address(address.host, address.port):
            log.msg("Refused secondary connection from {0}".format(address))
            return None

        return protocol.ServerFactory.buildProtocol(self, address)
