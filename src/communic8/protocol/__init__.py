import json
import inspect

from twisted.internet import defer, task, reactor
from twisted.internet.protocol import connectionDone, DatagramProtocol, Factory, \
    ClientFactory
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
        self.wait_response_deferred = None

    @property
    def message_dispatcher(self):
        return None

    def log(self, fmt, *args, **kwargs):
        prefix = "{a.type}:{a.port} - ".format(a=self.transport.getPeer())
        log.msg(prefix + fmt.format(*args, **kwargs))

    def is_transport_udp(self):
        return self.transport.getHost().type == 'UDP'

    def send_message(self, message, callback=None, timeout=10,
                     timeout_callback=None):
        if self.wait_response_deferred is not None:
            raise ProtocolError(
                "Cannot send message while waiting for response")

        self.log("Sending message '{msg}'", msg=message)
        #self.log("Sending message {cmd}", cmd=message.command)

        self.transport.write(str(message) + '\r\n')

        self.wait_response_deferred = d = defer.Deferred()

        def on_finish(result):
            self.wait_response_deferred = None
            return result

        d.addBoth(on_finish)

        if callback:
            d.addCallback(callback)

        if timeout:
            delayed_call = reactor.callLater(timeout, d.cancel)

            def on_cancel(failure):
                failure.trap(defer.CancelledError)
                self.log("Timeout waiting for message response")
                return failure

            d.addErrback(on_cancel)

            def on_result(result):
                if delayed_call.active():
                    delayed_call.cancel()
                return result

            d.addBoth(on_result)

        return d

    def send_response(self, data):
        if self.wait_response_deferred is not None:
            raise ProtocolError(
                "Cannot send response while waiting for another")

        data = dict(data)
        data.update(state=self.current)

        js = json.dumps(data)
        self.log("Sending response {data}", data=js)
        self.transport.write(js + '\r\n')

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
        self.log('received "{line}"', line=line)
        if self.wait_response_deferred:
            self.log("Received response")

            response = json.loads(line)
            self.wait_response_deferred.callback(response)
            self.wait_response_deferred = None
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


class CommonFactory(Factory):
    def __init__(self, protocol, callback, *args, **kwargs):
        self.protocol = protocol
        self.callback = callback
        self.proto_args = args
        self.proto_kwargs = kwargs

    def buildProtocol(self, addr):
        proto = self.protocol(*self.proto_args, **self.proto_kwargs)
        self.callback(proto)

        return proto


class CommonClientFactory(CommonFactory, ClientFactory):
    pass
