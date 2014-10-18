from collections import namedtuple

from twisted.protocols.basic import FileSender

from communic8.model.messages import *
from communic8.protocol import CommonProtocol
from communic8.util import Fysom


TransferFile = namedtuple('TransferFile', 'name path mime_type mtime size')


class Protocol(CommonProtocol, Fysom, FileSender):
    message_dispatcher = MessageDispatcher().register(
        Connect, Quit,
        SendChat, RequestFileTransfer
    )

    def __init__(self, client_server_proto):
        CommonProtocol.__init__(self)
        Fysom.__init__(self, initial='not_connected', events=[
            # event / from / to
            ('connect',
                'not_connected', 'connected'),
            ('listen',
                'not_connected', 'waiting_connection'),
            ('accept',
                'waiting_connection', 'connected'),
            ('send_file',
                'connected', 'sending_file'),
            ('receive_file',
                'connected', 'receiving_file'),
            ('finish_send_file',
                'sending_file', 'connected'),
            ('finish_receive_file',
                'receiving_file', 'connected'),
            ('abort_file_transfer',
                ['sending_file', 'receiving_file'], 'connected'),
            ('disconnect',
                '*', 'disconnected')
        ])

        self.client_server_proto = client_server_proto
        self.transfer_file = None
        self.user = None
        self.factory = None
        self.requesting_user = None
        self.chat_channel = None
        self.chat_port = None
