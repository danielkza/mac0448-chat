import datetime


class User(object):
    def __init__(self, name, ip, connected_at=None, last_seen_at=None):
        self.name = name
        self.ip = ip
        self.connected_at = connected_at if connected_at else datetime.datetime.now()
        self.last_seen_at = last_seen_at if last_seen_at else self.connected_at

        if self.last_seen_at < self.connected_at:
            raise ValueError("Invalid combination of connection and last seen times")

    def seen(self, time=None):
        if not time:
            time = datetime.datetime.now()

        self.last_seen_at = time


class UserDatabaseError(RuntimeError):
    pass


class UserAlreadyLoggedIn(UserDatabaseError):
    pass


class UserDatabase(object):
    def __init__(self):
        self.users = {}

    def __setitem__(self, name, user):
        if name in self.users:
            raise UserAlreadyLoggedIn("User {0} is already logged in".format(user.name))

        self.users[name] = user

    def __getitem__(self, name):
        try:
            return self.users[name]
        except KeyError:
            raise KeyError("User {0} is not logged in".format(name))

    def __delitem__(self, name):
        try:
            del self.users[name]
        except KeyError:
            raise KeyError("User {0} is not logged in".format(name))

    def add(self, user):
        self[user.name] = user

    def remove(self, user):
        existing_user = self[user.name]
        if existing_user != user:
            raise UserDatabaseError("Logged in user does not match specified user")

        del self.users[user.name]

    def get(self, name):
        return self.users.get(name)