from itertools import chain
import time
from datetime import datetime


class MessageError(RuntimeError):
    pass


class Message(object):
    arg_types = ()
    parse_args = True
    command = 'NOP'

    def __init__(self):
        pass

    @classmethod
    def args_from_string(cls, s):
        if not cls.parse_args:
            return [s]

        args = s.split(" ") if s else []
        if len(args) != len(cls.arg_types):
            raise MessageError("Invalid number of arguments for message")

        try:
            args_with_types = zip(args, cls.arg_types)
            return map(lambda (arg, type_): type_(arg), args_with_types)
        except ValueError:
            raise MessageError("Failed to parse argument")

    def args(self):
        return []

    def __str__(self):
        return ' '.join(chain((self.command,), map(str, self.args())))


class MessageDispatcher(object):
    def __init__(self):
        self.types = {}

    def register(self, *types):
        for type_ in types:
            if type_.command in self.types:
                raise MessageError("Message type is already registered")

        self.types.update((type_.command, type_) for type_ in types)
        return self

    def parse(self, s):
        parts = s.split(' ', 1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ''

        try:
            type_ = self.types[command]
        except KeyError:
            raise MessageError("Invalid command")

        return type_(*type_.args_from_string(args))


class Connect(Message):
    command = "CONNECT"
    arg_types = ()


class Quit(Message):
    command = "QUIT"
    arg_types = ()


class Login(Message):
    command = "LOGIN"
    arg_types = (str, )

    def __init__(self, user):
        super(Login, self).__init__()
        self.user = user

    def args(self):
        return self.user,


class Logout(Message):
    command = "LOGOUT"
    arg_types = ()


class ListUsers(Message):
    command = "LIST_USERS"
    arg_types = ()


class RequestChat(Message):
    command = "REQUEST_CHAT"
    arg_types = (str, )

    def __init__(self, user):
        super(RequestChat, self).__init__()
        self.user = user

    def args(self):
        return self.user,


class ChatRequested(Message):
    command = "CHAT_REQUESTED"
    arg_types = (str, )

    def __init__(self, user):
        super(ChatRequested, self).__init__()
        self.user = user

    def args(self):
        return self.user,


class SendChat(Message):
    command = "SEND_CHAT"
    arg_types = (str, )
    parse_args = False

    def __init__(self, message):
        super(SendChat, self).__init__()
        self. message = message

    def args(self):
        return self.message,


class EndChat(Message):
    command = "END_CHAT"
    arg_types = (str,)

    def __init__(self, user):
        super(EndChat, self).__init__()
        self.user = user

    def args(self):
        return self.user,


class RequestFileTransfer(Message):
    command = "REQUEST_FILE_TRANSFER"
    arg_types = (str, str, long, long, int)
    parse_args = True

    def __init__(self, name, mime_type, mtime, size, block_size):
        super(RequestFileTransfer, self).__init__()
        self.name = name
        self.mime_type = mime_type

        if isinstance(mtime, datetime):
            self.mtime = mtime
        else:
            self.mtime = datetime.utcfromtimestamp(mtime)

        self.size = size
        self.block_size = block_size

    def mtime_timestamp(self):
        return long(time.mktime(self.mtime.timetuple()))

    def args(self):
        return (self.name, self.mime_type, self.mtime_timestamp(), self.size,
                self.block_size)
