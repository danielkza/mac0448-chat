import sys

from cmd import Cmd
import time

from twisted.internet import reactor, threads, defer
from twisted.python import log

from communic8.protocol import client_server


class CommandProcessor(Cmd):
    prompt = '>> '

    def wait_call(self, f, *args, **kwargs):
        d = defer.Deferred()
        kwargs['callback'] = lambda result: d.callback(result)
        kwargs['error_callback'] = lambda: d.errback(Exception())

        def handle_error(failure):
            failure.trap(Exception)
            print 'Command failed'

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

    def do_login(self, line):
        self.wait_call(self.protocol.login, line)

    def do_logout(self, line):
        self.wait_call(self.protocol.logout)

    def do_disconnect(self, line):
        self.wait_call(self.protocol.disconnect)
        reactor.callFromThread(reactor.stop)
        return True

    def do_initiate(self, line):
        self.wait_call(self.protocol.chat_initiate, line)

    def do_confirm(self, line):
        self.wait_call(self.protocol.chat_confirm, line)

    def do_reject(self, line):
        self.wait_call(self.protocol.chat_reject, line)

    def do_quit(self, line):
        return self.do_disconnect(line)

    def emptyline(self):
        pass


def main():
    log.startLogging(sys.stderr, setStdout=False)

    client_factory = client_server.ClientServerFactory()
    reactor.connectTCP('127.0.0.1', 8125, client_factory)

    def wait_for_protocol():
        while len(client_factory.instances) == 0:
            time.sleep(1)

        return True

    d = threads.deferToThread(wait_for_protocol)

    def run_loop(_):
        proc = CommandProcessor(client_factory.instances[0])
        reactor.callInThread(proc.cmdloop)

    d.addCallback(run_loop)
    reactor.run()

if __name__ == '__main__':
    main()

