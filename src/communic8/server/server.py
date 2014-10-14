import json

from twisted.internet.protocol import Factory, Protocol, connectionDone
from twisted.protocols.basic import LineOnlyReceiver

from communic8.model.state import StateMachine
from communic8.model.user import UserDatabase, UserAlreadyLoggedIn, UserDatabaseError, User
from communic8.model.messages import *
from fysom import Fysom, FysomError



class ServerProtocol(LineOnlyReceiver, Fysom):
    # states = {
    #     'waiting_connection'
    #     'waiting_login',
    #     'logged_in',
    #     'starting_chat',
    #     'waiting_chat_accept_other',
    #     'waiting_chat_accept_self',
    #     'chatting',
    #     'ending'
    # }
    #
    # allowed_transitions = {
    #     'all':                       {'ending'},
    #     'waiting_connection':        {'waiting_login'},
    #     'waiting_login':             {'waiting_connection','logged_in'},
    #     'logged_in':                 {'starting_chat', 'waiting_chat_acceptance_self'},
    #     'starting_chat':             {'waiting_chat_acceptance_other', 'logged_in'},
    #     'waiting_chat_accept_other': {'chatting', 'logged_in'},
    #     'chatting':                  {'logged_in'},
    #     'waiting_chat_accept_self':  {'chatting', 'logged_in'}
    # }



    def __init__(self, user_database, dispatcher):
        Fysom.__init__(self, {'initial': 'waiting_connection',
                          'events': [('connect', 'waiting_connection', 'waiting_login'),
                                     ('login', 'waiting_login', 'logged_in'),
                                     ('disconnect', '*', 'disconnected' ),
                                     ('logout', '*', 'waiting_login'),
                                     ('user_list', 'logged_in', 'logged_in')] })

        self.connected = False
        self.user = None
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
            return
        self.send_json({'state': 'OK', 'message': 'Received message {0}'.format(message.command)})
        try:
            if isinstance(message, Connect):
                self.connect()
            elif isinstance(message, Login):
                self.login(message.user)
            elif isinstance(message, Quit):
                self.transport.loseConnection()
            elif isinstance(message, Logout):
                self.logout()
            elif isinstance(message, ListUsers):
                self.user_list()
            print self.current
        except FysomError:
            self.send_json({'state': 'FAILED', 'message': 'Invalid message for current state'})

    def onbeforelogin(self, event):
        user_name = event.args[0]
        ip = self.transport.getPeer().host
        try:
            cur_user = User(user_name, ip)
            self.user_database.add(cur_user)
            self.user = cur_user

        except UserAlreadyLoggedIn:
            self.send_json({'state': 'FAILED', 'message': 'User already logged in'})
            return False
        return True

    def onbeforelogout(self, event):
        if self.user is None:
            return False
        return True

    def onafterlogout(self, event):
        self.user_database.remove(self.user)
        self.user = None

    def onenterdisconnected(self, event):
        print "disconnected"
        if self.connected:
            self.transport.loseConnection()

    def onafteruser_list(self, event):
        users = []
        for name, user in self.user_database.users.items():
            users.append({'name': user.name, 'ip': user.ip})
        self.send_json(users)

    def connectionMade(self):
        self.connected = True

    def connectionLost(self, reason):
        self.connected = False
        self.disconnect()

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
        d.add_message(Login)
        d.add_message(SendChat)
        d.add_message(Logout)



    def buildProtocol(self, addr):
        return ServerProtocol(self.users, self.dispatcher)
