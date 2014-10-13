import json

from twisted.internet.protocol import Factory, Protocol, connectionDone
from twisted.protocols.basic import LineOnlyReceiver

from communic8.model.state import StateMachine
from communic8.model.user import UserDatabase, UserAlreadyLoggedIn, UserDatabaseError
from communic8.model.messages import *


class ServerProtocol(LineOnlyReceiver, StateMachine):
    states = {
        'waiting_login',
        'logged_in',
        'starting_chat',
        'waiting_chat_accept_other',
        'waiting_chat_accept_self',
        'chatting',
        'ending'
    }

    transitions = {
        'all':                       {'ending'},
        'waiting_login':             {'logged_in', 'ending'},
        'logged_in':                 {'starting_chat', 'waiting_chat_acceptance_self'},
        'starting_chat':             {'waiting_chat_acceptance_other', 'logged_in'},
        'waiting_chat_accept_other': {'chatting', 'logged_in'},
        'chatting':                  {'logged_in'},
        'waiting_chat_accept_self':  {'chatting', 'logged_in'}
    }

    def __init__(self, user_database, dispatcher):
        StateMachine.__init__(self, 'waiting_login')

        self.user_database = user_database
        self.dispatcher = dispatcher

    def send_json(self, data):
        json.dump(data, self.transport)
        self.transport.write('\n')

    def lineReceived(self, line):
        try:
            message = self.dispatcher.parse_message(line)
        except MessageError:
            self.send_json({'state': 'error', 'message': 'Invalid message'})
        else:
            self.send_json({'state': 'OK', 'message': 'Received message {0}'.format(message.command)})


class ServerFactory(Factory):
    def __init__(self):
        self.users = UserDatabase()
        self.dispatcher = d = MessageDispatcher()

        d.add_message(Connect)
        d.add_message(Alive)
        d.add_message(Quit)
        d.add_message(ListUsers)
        d.add_message(ChatStart)
        d.add_message(ChatAccept)
        d.add_message(ChatRequested)
        d.add_message(ChatConfirmed)

    def buildProtocol(self, addr):
        return ServerProtocol(self.users, self.dispatcher)
