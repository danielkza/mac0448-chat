import os
from collections import namedtuple
import itertools
import mimetypes

from zope.interface import implements
from twisted.internet import interfaces, defer
from twisted.internet.protocol import connectionDone, Factory
from twisted.web.client import FileBodyProducer

from communic8.model.messages import *
from communic8.protocol import CommonProtocol
from communic8.util import Fysom


class TransferFile(namedtuple('TransferFile',
                              'name mime_type mtime size block_size path')):
    @classmethod
    def from_message(cls, message):
        if not isinstance(message, RequestFileTransfer):
            raise ValueError

        return cls(name=message.name, mime_type=message.mime_type,
                   mtime=message.mtime, size=message.size,
                   block_size=message.block_size, path=None)

    @classmethod
    def from_path(cls, path, block_size=512):
        open(path, 'rb').close()

        name = os.path.basename(path)
        path = path
        mime_type, encoding = mimetypes.guess_type(name)

        stat = os.stat(path)
        mtime = datetime.utcfromtimestamp(stat.st_mtime)
        size = stat.st_size

        return cls(name=name, mime_type=mime_type, mtime=mtime, size=size,
                   block_size=block_size, path=path)

    def to_message(self):
        return RequestFileTransfer(name=self.name, mime_type=self.mime_type,
                                   mtime=self.mtime, size=self.size,
                                   block_size=self.block_size)


class TransferError(RuntimeError):
    pass


class FileConsumer(object):
    implements(interfaces.IConsumer)

    def __init__(self, file_object, size):
        assert size > 0

        try:
            file_object.truncate(size)
        except (IOError, OSError):
            file_object.close()
            raise

        self.file_object = file_object
        self.size = size
        self.partial_size = 0
        self.deferred = None
        self.producer = None

    def registerProducer(self, producer, streaming):
        assert streaming
        self.producer = producer
        if not self.deferred:
            self.deferred = defer.Deferred()

        return self.deferred

    def unregisterProducer(self):
        self.producer = None

    def finish(self):
        if not self.file_object:
            return

        self.unregisterProducer()
        self.file_object.close()

        deferred = self.deferred
        self.file_object = None
        self.deferred = None

        if deferred:
            if self.partial_size < self.size:
                deferred.errback(
                    TransferError("Transfer terminated before completion"))
            else:
                deferred.callback(self.size)

    def write(self, bytes_):
        assert self.producer is not None
        assert self.file_object is not None

        new_partial_size = self.partial_size + len(bytes_)
        if new_partial_size > self.size:
            bytes_ = bytes_[:self.size - self.partial_size]
            new_partial_size = self.size

        self.file_object.write(bytes_)
        self.partial_size = new_partial_size
        if self.partial_size == self.size:
            self.finish()


class Protocol(CommonProtocol, Fysom):
    message_dispatcher = MessageDispatcher().register(
        Connect, Quit,
        SendChat, RequestFileTransfer
    )

    async_transitions = {'connect', 'send_file'}

    def __init__(self, client_server_proto, user_name, is_initiator=False,
                 file_receive_path=None):
        CommonProtocol.__init__(self)
        Fysom.__init__(self, initial='not_connected', events=[
            # event / from / to
            ('connect',
                'not_connected', 'connected'),
            ('disconnect',
             '*', 'done'),
            ('accept_connection',
                'not_connected', 'connected'),
            ('send_chat',
                'connected', 'connected'),
            ('receive_chat',
                'connected', 'connected'),
            ('send_file',
                'connected', 'sending_file'),
            ('receive_file',
                'connected', 'receiving_file'),
            ('send_file_success',
                'sending_file', 'connected'),
            ('send_file_failure',
                'sending_file', 'connected'),
            ('receive_file_success',
                'receiving_file', 'connected'),
            ('receive_file_failure',
                'receiving_file', 'connected')
        ])

        self.client_server_proto = client_server_proto
        self.other_user_name = user_name
        self.transfer_file = None
        self.file_producer = None
        self.file_consumer = None
        self.is_initiator = is_initiator

        self.receive_path = file_receive_path
        if not self.receive_path:
            self.receive_path = os.path.abspath(os.getcwd())

    def on_message_received(self, message):
        for msg_cls, action in {
            Connect:
                lambda m: self.accept_connection(),
            Quit:
                lambda m: self.disconnect(),
            RequestFileTransfer:
                lambda m: self.receive_file(TransferFile.from_message(m)),
            SendChat:
                lambda m: self.receive_chat(m.message)
        }.items():
            if isinstance(message, msg_cls):
                action(message)
                return

    def rawDataReceived(self, data):
        assert self.file_consumer is not None
        self.file_consumer.write(data)

    def on_before_connect(self, _):
        def on_response(response):
            if self.check_response_error(response):
                self.log("Connection rejected")
                self.cancel_transition()
                self.disconnect()
            else:
                self.log("Connected")
                self.transition()

        self.send_message(Connect(), on_response)

    def on_accept_connection(self, _):
        self.log("Accepting incoming connection")
        self.send_response({})

    def on_before_send_chat(self, event):
        message = event.args[0]

        def on_response(response):
            if self.check_response_error(response):
                self.log("Received negative chat ack")
            else:
                self.log("Received positive chat ack")

        self.send_message(SendChat(message), on_response)

    def on_receive_chat(self, event):
        self.log("Received chat message: '{message}'", message = event.args[0])

        self.send_response({})

    def open_transfer_file_read(self, transfer):
        try:
            fp = open(transfer.path, 'rb')
            self.file_producer = FileBodyProducer(fp,
                readSize=transfer.block_size)
            self.transfer_file = transfer
        except IOError:
            return False

        return True

    def on_before_send_file(self, event):
        transfer = event.args[0]

        def on_response(response):
            if self.check_response_error(response):
                self.log("Received error after file transfer request")
            elif response.get('result') != 'confirmed':
                self.log("File transfer request denied")
            else:
                self.log("File transfer request accepted, starting")
                if self.open_transfer_file_read(transfer):
                    self.transition()
                    return

            self.cancel_transition()

        self.send_message(transfer.to_message(), on_response).addErrback(
            lambda _: self.cancel_transition())

    def on_enter_sending_file(self, _):
        assert self.transfer_file is not None
        assert self.file_producer is not None

        self.setRawMode()
        d = self.file_producer.startProducing(self.transport)

        def on_success(_):
            self.log("File send successfully")
            self.send_file_success()

        def on_failure(failure):
            failure.trap(Exception)
            self.log("File send failed: {e}", e=failure)
            self.send_file_failure()

        d.addCallbacks(on_success, on_failure)

    def on_leave_sending_file(self, _):
        self.transfer_file = None
        self.file_producer.stopProducing()
        self.file_producer = None

        self.setLineMode()

    def open_transfer_file_write(self, transfer):
        try:
            fp = open(transfer.path, 'wb')
        except (OSError, IOError) as e:
            self.log("Failed to open file for writing: {e}", e=e)
            return False

        try:
            self.file_consumer = FileConsumer(fp, transfer.size)
            self.transfer_file = transfer
        except (IOError, OSError) as e:
            self.log("Failed allocating {size} byte file for transfer: {e}",
                     size=transfer.size, e=e)
            fp.close()
            return False

        return True

    def on_before_receive_file(self, event):
        transfer = event.args[0]
        path = os.path.join(self.receive_path, transfer.name)

        def generate_unique_path(initial_path):
            filename, ext = os.path.splitext(initial_path)
            for n in itertools.count():
                yield "{0}-{1}{2}".format(filename, n, ext)

        if os.path.exists(path):
            for path in generate_unique_path(path):
                if not os.path.exists(path):
                    break

        transfer = transfer._replace(path=path)

        if not self.open_transfer_file_write(transfer):
            self.write_response({'result': 'rejected'})
            return False

        self.log("Receiving file as {path}", path=path)
        self.send_response({'result': 'confirmed'})

    def on_enter_receiving_file(self, _):
        assert self.transfer_file is not None
        assert self.file_consumer is not None

        self.setRawMode()
        d = self.file_consumer.registerProducer(self, streaming=True)

        def on_success(_):
            self.log("File received successfully")
            self.receive_file_success()

        def on_failure(failure):
            failure.trap(Exception)
            self.log("File receive failed: {e}", e=failure)
            self.receive_file_failure()

        d.addCallbacks(on_success, on_failure)

    def on_leave_receiving_file(self, _):
        self.transfer_file = None
        self.file_consumer.finish()
        self.file_consumer = None

        self.setLineMode()

    def connectionMade(self):
        if self.is_initiator:
            self.connect()

    def connectionLost(self, reason=connectionDone):
        self.cancel_transition()
        self.disconnect()

    def on_enter_done(self, _):
        if self.current == 'receiving_file':
            self.receive_file_failure()
        elif self.current == 'sending_file':
            self.send_file_failure()

        if not self.transport_connected:
            return

        self.send_message(Quit()).addBoth(
            self.transport.loseConnection)
