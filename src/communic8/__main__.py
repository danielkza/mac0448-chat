from twisted.internet import reactor
from communic8.server.server import ServerProtocol, ServerFactory


def main():
    factory = ServerFactory()
    reactor.listenTCP(8125, factory)
    reactor.run()

if __name__ == '__main__':
    main()