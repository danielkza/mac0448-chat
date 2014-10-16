import sys

from twisted.internet import reactor
from twisted.python import log
from communic8.protocol import server


def main():
    log.startLogging(sys.stderr)

    tcp_factory = server.Factory()
    reactor.listenTCP(8125, tcp_factory)
    reactor.run()

if __name__ == '__main__':
    main()
