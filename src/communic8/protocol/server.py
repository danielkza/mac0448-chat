from twisted.internet import protocol
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
                ('connect',        'waiting_connection', 'waiting_login'),
                ('disconnect',     '*',                  'disconnected'),
                ('logout',         '*',                  'waiting_login'),
                ('login',          'waiting_login',      'logged_in'),
                ('send_user_list', 'logged_in',          'logged_in')
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
        if isinstance(message, Connect):
            self.connect()
        elif isinstance(message, Login):
            self.login(message.user)
        elif isinstance(message, Quit):
            self.transport.loseConnection()
        elif isinstance(message, Logout):
            self.logout()
        elif isinstance(message, ListUsers):
            self.send_user_list()

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
            users.append({'name': user.name, 'connected_at': user.connected_at})

        self.send_response(users)

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
            SendChat
        )

    def buildProtocol(self, address):
        if self.user_database.get_by_address(address.host, address.port):
            log.msg("Refused secondary connection from {0}".format(address))
            return None

        return protocol.ServerFactory.buildProtocol(self, address)
