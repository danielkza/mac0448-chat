import json
import inspect

from twisted.internet import defer, task, reactor
from twisted.internet.protocol import connectionDone, DatagramProtocol
from twisted.protocols.basic import LineReceiver
from twisted.python import log
from fysom import FysomError, Canceled

from communic8.model.messages import MessageError


class ProtocolError(RuntimeError):
    pass


class CommonProtocol(LineReceiver):
    ERROR_MESSAGES = {
        'INVALID_COMMAND': 'Invalid or unknown command',
        'INVALID_COMMAND_FOR_STATE': 'Invalid command {command} for state {state}'
    }

    def __init__(self):
        self.transport_connected = False
        self.wait_response_callback = None

    @property
    def message_dispatcher(self):
        return None

    def log(self, fmt, *args, **kwargs):
        prefix = "{a.type}:{a.port} - ".format(a=self.transport.getPeer())
        log.msg(prefix + fmt.format(*args, **kwargs))

    def send_message(self, message, response_callback=None):
        if self.wait_response_callback is not None:
            raise ProtocolError(
                "Cannot send message while waiting for response")

        self.log("Sending message '{msg}'", msg=message)
        #self.log("Sending message {cmd}", cmd=message.command)

        self.transport.write(str(message))
        self.transport.write('\r\n')

        if response_callback:
            self.log("Waiting for response")
            self.wait_response_callback = response_callback

    def send_response(self, data):
        if self.wait_response_callback is not None:
            raise ProtocolError(
                "Cannot send response while waiting for response")

        data = dict(data)
        data.update(state=self.current)

        self.log("Sending response {data}", data=json.dumps(data))

        json.dump(data, self.transport)
        self.transport.write('\r\n')

    @classmethod
    def error_type_message(cls, key):
        try:
            for mro_cls in inspect.getmro(cls):
                try:
                    return mro_cls.ERROR_MESSAGES[key]
                except KeyError:
                    pass
        except AttributeError:
            return None

    def send_error_response(self, key, message=None, *args, **kwargs):
        if not message:
            message = self.error_type_message(key)
            if message:
                message = message.format(*args, **kwargs)
            else:
                message = key

        self.log("Sending error response {key}".format(key=key))

        return self.send_response({'error': key, 'message': message})

    def check_response_error(self, response):
        return 'error' in response

    def on_message_received(self, message):
        pass

    # Twisted callbacks

    def connectionMade(self):
        LineReceiver.connectionMade(self)
        self.transport_connected = True

        self.log("Transport connected")

    def connectionLost(self, reason=connectionDone):
        LineReceiver.connectionLost(self)
        self.transport_connected = False

        self.log("Transport disconnected")

    def lineReceived(self, line):
        print 'received "{0}"'.format(line)
        if self.wait_response_callback:
            self.log("Received response")

            response = json.loads(line)
            callback = self.wait_response_callback
            self.wait_response_callback = None
            callback(response)
        else:
            try:
                message = self.message_dispatcher.parse(line)
            except MessageError:
                self.send_error_response('INVALID_COMMAND')
                return

            self.log("Received message {cmd}", cmd=message.command)

            try:
                self.on_message_received(message)
            except Canceled:
                # The pre-transition handlers is responsible for returning an
                # error response if it cancels the transition
                pass
            except FysomError:
                self.send_error_response('INVALID_COMMAND_FOR_STATE', None,
                                         command=message.command,
                                         state=self.current)
