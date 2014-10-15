import ipaddr
from itertools import chain


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
            raise MessageError("Invalid number or arguments for message")

        try:
            map(lambda (arg, type_): type_(arg), zip(args, cls.arg_types))
        except ValueError:
            raise MessageError("Failed to parse argument")

        return args

    def args(self):
        return []

    def __str__(self):
        return ' '.join(chain((self.command,), map(str, self.args)))


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
        return [self.user]


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
        return [self.user]


class ChatRequested(Message):
    command = "CHAT_REQUESTED"
    arg_types = (str, )

    def __init__(self, user):
        super(ChatRequested, self).__init__()
        self.user = user

    def args(self):
        return [self.user]


class AcceptChat(Message):
    command = "ACCEPT_CHAT"
    arg_types = (str, int)

    def __init__(self, user, port):
        super(AcceptChat, self).__init__()
        self.user = user
        self.port = port

    def args(self):
        return [self.user, self.port]


class ChatAccepted(Message):
    command = "CHAT_ACCEPTED"
    arg_types = (str, ipaddr.IPAddress, int)

    def __init__(self, user, host, port):
        super(ChatAccepted, self).__init__()
        self.user = user
        self.host = host
        self.port = port

    def args(self):
        return [self.user, self.host, self.port]


class SendChat(Message):
    command = "SEND_CHAT"
    arg_types = (str, )
    parse_args = False

    def __init__(self, message):
        super(SendChat, self).__init__()
        self. message = message

    def args(self):
        return [self.message]


class RequestFileTransfer(Message):
    command = "REQUEST_FILE_TRANSFER"
    arg_types = (str, int)
    parse_args = True

    def __init__(self, mime_type, file_size):
        super(RequestFileTransfer, self).__init__()
        self.mime_type = mime_type
        self.file_size = file_size

    def args(self):
        return [self.mime_type, self.file_size]
