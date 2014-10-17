import os
import sys

from cmd import Cmd
import time

from twisted.internet import reactor, threads
from twisted.python import log

from communic8.protocol import client_server


class CommandProcessor(Cmd):
    prompt = '>>'

    def __init__(self, protocol):
        Cmd.__init__(self)
        self.protocol = protocol

    def do_EOF(self, line):
        return True

    def do_connect(self, line):
        self.protocol.connect()

    def do_login(self, line):
        self.protocol.login(line)

    def do_logout(self, line):
        self.protocol.logout()

    def do_disconnect(self, line):
        self.protocol.disconnect()


def wait_for_protocol(factory):
    while len(factory.instances) == 0:
        time.sleep(1)

    return True


def main():
    log.startLogging(sys.stderr)

    client_factory = client_server.ClientServerFactory()
    reactor.connectTCP('127.0.0.1', 8125, client_factory)

    d = threads.deferToThread(wait_for_protocol, client_factory)

    def run_loop(_):
        proc = CommandProcessor(client_factory.instances[0])
        reactor.callInThread(proc.cmdloop)

    d.addCallback(run_loop)
    reactor.run()

if __name__ == '__main__':
    main()

