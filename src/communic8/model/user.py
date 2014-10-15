from datetime import datetime
from collections import namedtuple


User = namedtuple('User', 'name host port connected_at')


class UserDatabaseError(RuntimeError):
    pass


class UserNameAlreadyUsed(UserDatabaseError):
    pass


class AddressAlreadyUsed(UserDatabaseError):
    pass


class UserNotLoggedIn(UserDatabaseError, KeyError):
    pass


class UserDatabase(object):
    def __init__(self):
        self._users = {}
        self._users_by_address = {}
        self._last_seen = {}

    def __getitem__(self, name):
        try:
            return self._users[name]
        except KeyError:
            raise UserNotLoggedIn()

    def __delitem__(self, name):
        try:
            user = self._users.pop(name)
            del self._users_by_address[(user.host, user.port)]
        except KeyError:
            raise UserNotLoggedIn()

    def users(self):
        return self._users.itervalues()

    def add(self, name, host, port):
        address = (host, port)

        if name in self._users:
            raise UserNameAlreadyUsed()
        elif address in self._users_by_address:
            raise UserNameAlreadyUsed()

        user = User(name, host, port, datetime.now())
        self._users[user.name] = user
        self._users_by_address[address] = user
        self._last_seen[user] = datetime.now()
        return user

    def remove(self, name):
        del self[name]

    def get(self, name, default=None):
        return self._users.get(name, default)

    def get_by_address(self, host, port, default=None):
        return self._users_by_address.get((host, port), default)

    def get_user_last_seen(self, name):
        user = self[name]
        return self._last_seen[user]

    def update_user_last_seen(self, name, time=None):
        user = self[name]
        time = time or datetime.now()

        self._last_seen[user] = time


