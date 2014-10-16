import sys

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.python import log
from communic8.protocol import client_server


def main():
    log.startLogging(sys.stderr)

    client_factory = ClientFactory()
    client_factory.protocol = client_server.ClientServerProtocol
    reactor.connectTCP('127.0.0.1', 8125, client_factory)
    reactor.run()

if __name__ == '__main__':
    main()

