import sys

from twisted.internet import reactor
from twisted.python import log

from communic8.protocol import client_server


def main():
    log.startLogging(sys.stderr)

    client_factory = client_server.ClientServerFactory()
    reactor.connectTCP('127.0.0.1', 8125, client_factory)
    reactor.run()

if __name__ == '__main__':
    main()

