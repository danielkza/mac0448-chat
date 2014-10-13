import ipaddr


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


class MessageDispatcher(object):
    def __init__(self):
        self.types = {}

    def add_message(self, message_type):
        if message_type.command in self.types:
            raise MessageError("Message type is already registered")

        self.types[message_type.command] = message_type

    def parse_message(self, s):
        print 'parse_message: ' + s
        parts = s.split(' ', 1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ''

        print 'command: {0}, args: {1}'.format(command, args)

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


class Alive(Message):
    command = "ALIVE"
    arg_types = ()


class ListUsers(Message):
    command = "LIST_USERS"
    arg_types = ()


class ChatStart(Message):
    command = "CHAT_START"
    arg_types = (str, )

    def __init__(self, user):
        super(ChatStart, self).__init__()
        self.user = user

    def args(self):
        return [self.user]


class ChatRequested(Message):
    command = "CHAT_REQUESTED"
    arg_types = (str, )

    def __init__(self, user):
        super(ChatRequested, self).__init__()
        self. user = user

    def args(self):
        return [self.user]


class ChatAccept(Message):
    command = "CHAT_ACCEPT"
    arg_types = (str, int)

    def __init__(self, user, port):
        super(ChatAccept, self).__init__()
        self.user = user
        self.port = port

    def args(self):
        return [self.user, self.port]


class ChatConfirmed(Message):
    command = "CHAT_CONFIRMED"
    arg_types = (str, ipaddr.IPAddress, int)

    def __init__(self, user, ip, port):
        super(ChatConfirmed, self).__init__()
        self.user = user
        self.ip = ip
        self.port = port

    def args(self):
        return [self.user, self.ip, self.port]


def test():
    d = MessageDispatcher()
    d.add_message(Connect)
    d.add_message(Alive)
    d.add_message(Quit)
    d.add_message(ListUsers)
    d.add_message(ChatStart)
    d.add_message(ChatAccept)
    d.add_message(ChatRequested)
    d.add_message(ChatConfirmed)

    def p(o):
        import pprint
        print o.__class__.__name__ + " " + pprint.pformat(vars(o))

    p(d.parse_message("CONNECT"))
    p(d.parse_message("ALIVE"))
    p(d.parse_message("QUIT"))
    p(d.parse_message("CHAT_START joaozinho"))
    p(d.parse_message("CHAT_REQUESTED daniboy")) # to joaozinho
    p(d.parse_message("CHAT_ACCEPT daniboy 2000")) # from joaozinho
    p(d.parse_message("CHAT_CONFIRMED joaozinho 192.168.1.1 2000"))

