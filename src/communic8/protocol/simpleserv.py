
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.


from twisted.internet import reactor, protocol


class Echo(protocol.Protocol):
    """This is just about the simplest possible protocol"""
    
    def dataReceived(self, data):
        "As soon as any data is received, write it back."
        self.transport.write(data)


def main(port):
    """This runs the protocol on port 8000"""
    print "Oi"
    factory = protocol.ServerFactory()
    factory.protocol = Echo
    reactor.listenTCP(port,factory)
    reactor.run()

