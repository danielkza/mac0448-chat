import sys

from twisted.internet import reactor
from twisted.python import log
from communic8.protocol import server


import sys

from twisted.internet import ssl, protocol, task, defer
from twisted.python import log
from twisted.python.modules import getModule
from communic8.protocol import server


def main(reactor):
    log.startLogging(sys.stdout)
    certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    certificate = ssl.PrivateCertificate.loadPEM(certData)
    factory = protocol.Factory.forProtocol(server.Factory)
    reactor.listenSSL(8125, factory, certificate.options())
    return defer.Deferred()

if __name__ == '__main__':
    import server
    task.react(server.main)
