import datetime
import json


class Message(object):
    def __init__(self, content, timestamp):
        self.content = content
        self.timestamp = timestamp


class Command(object):
    type_name = None

    def __init__(self, args):
        self.args = args

    _classes = {}
    @classmethod
    def register(cls, command_cls):
        name = command_cls.type_name
        if name in cls._classes:
            raise KeyError("Name already registered")

        cls._classes[name] = command_cls

    def to_message(self):
        content = ""
        content += self.type_name
        content += '\0'
        for arg in self.args:
            content += str(arg)
            content += '\0'

        # TODO: add time
        return Message(content, 0)


class LoginCommand(Command):
    type_name = 'LOGIN'

    def __init__(self, user_name):
        super(LoginCommand, self).__init__([user_name])

    @classmethod
    def from_array(cls, args):
        if len(args) != 1:
            raise ValueError
        return LoginCommand(args[0])

Command.register(LoginCommand)


class LogoutCommand(Command):
    type_name = 'LOGOUT'

    def __init__(self):
        super(LogoutCommand, self).__init__([])

    @classmethod
    def from_array(cls, args):
        if len(args) != 0:
            raise ValueError
        return LogoutCommand()

Command.register(LogoutCommand)

class Heartbeat(Command):
    type_name = 'HEARTBEAT'

    def __init__(self):
        super(Heartbeat, self).__init__([])

    @classmethod
    def from_array(cls, args):
        if len(args) != 0:
            raise ValueError
        return Heartbeat()

Command.register(Heartbeat)


class UserList(Command):
    type_name = 'USERLIST'

    def __init__(self):
        super(UserList, self).__init__([])

    @classmethod
    def from_array(cls, args):
        if len(args) != 0:
            raise ValueError
        return UserList()

Command.register(UserList)


class Response(object):
    def __init__(self, content):
        self.content = content

    def to_message(self):
        content = json.dumps(dict(self.content), ensure_ascii=True)

        # TODO: add time
        return Message(content, 0)
