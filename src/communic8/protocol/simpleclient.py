
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.


"""
An example client. Run simpleserv.py first before running this.
"""

from twisted.internet import reactor, protocol


# a client protocol

class EchoClient(protocol.Protocol):
    """Once connected, send a message, then print the result."""
    
    def connectionMade(self):
        self.transport.write("hello, world!")

    def sendMsg(self, line):
        self.transport.write(line)

    def dataReceived(self, data):
        "As soon as any data is received, write it back."
        print "Server said:", data
    
    def connectionLost(self, reason):
        print "connection lost"

class EchoFactory(protocol.ClientFactory):
    protocol = EchoClient

    def writeMsg(self, msg):
        self.protocol.sendMsg(EchoClient(), msg)

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed - goodbye!"
        reactor.stop()
    
    def clientConnectionLost(self, connector, reason):
        print "Connection lost - goodbye!"
        reactor.stop()


# this connects the protocol to a server runing on port 8000
def main(host, port):
    f = EchoFactory()
    reactor.connectTCP(host, port, f)
    reactor.run()

