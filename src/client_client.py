import sys

from cmd import Cmd
import time
from fysom import FysomError

from twisted.internet import reactor, threads, defer
from twisted.internet.protocol import ClientFactory
from twisted.python import log

from communic8.protocol import client, CommonClientFactory
from twisted.internet import ssl, task, protocol, endpoints, defer
from twisted.python.modules import getModule

class CommandProcessor(Cmd):
    prompt = '>> '

    def wait_call(self, f, *args, **kwargs):
        d = defer.Deferred()
        kwargs['callback'] = lambda result: d.callback(result)
        kwargs['error_callback'] = lambda: d.errback(Exception())

        def handle_invalid_state(failure):
            failure.trap(FysomError)
            print 'Invalid command for current state'

        def handle_error(failure):
            failure.trap(Exception)
            print 'Command failed'

        d.addErrback(handle_invalid_state)
        d.addErrback(handle_error)

        reactor.callFromThread(f, *args, **kwargs)
        while not d.called:
            time.sleep(0.1)

    def __init__(self, protocol):
        Cmd.__init__(self)
        self.protocol = protocol

    def do_EOF(self, line):
        return self.do_disconnect(line)

    def do_connect(self, line):
        self.wait_call(self.protocol.connect)

    def do_disconnect(self, line):
        self.wait_call(self.protocol.disconnect)
        reactor.callFromThread(reactor.stop)
        return True

    def do_send_chat(self, line):
        self.wait_call(self.protocol.send_chat, line)

    def do_send_file(self, line):
        transfer = client.TransferFile.from_path(line)
        self.wait_call(self.protocol.send_file, transfer)

    def do_quit(self, line):
        return self.do_disconnect(line)

    def emptyline(self):
        pass


def main(reactor, port, host):
    log.startLogging(sys.stderr, setStdout=False)

    def run_loop(proto):
        proc = CommandProcessor(proto)
        reactor.callInThread(proc.cmdloop)

    factory = protocol.Factory.forProtocol(clien_client.Factory)
    certData = getModule(__name__).filePath.sibling('server.pem').getContent()
    authority = ssl.Certificate.loadPEM(certData)
    options = ssl.optionsForClientTLS(u'example.com', authority)
    endpoints.SSL4ClientEndpoint(reactor, 'localhost', 8125,
                                            options).connect(factory)

if __name__ == '__main__':
    import clien_client
    port = int(sys.argv[1])

    if len(sys.argv) > 2:
        host = sys.argv[2]
    else:
        host = None

    task.react(client.main(port, host))

