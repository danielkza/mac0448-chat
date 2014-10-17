import fysom


class Fysom(fysom.Fysom):
    async_transitions = False

    def _before_event(self, e):
        fnname = 'on_before_' + e.event
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

    def _after_event(self, e):
        ret = None
        for fnname in ['on_after_' + e.event, 'on_' + e.event]:
            if hasattr(self, fnname):
                ret = getattr(self, fnname)(e)
                break

        if hasattr(e, 'deferred'):
            e.deferred.callback(ret)

        return ret

    def _leave_state(self, e):
        fnname = 'on_leave_' + e.src
        ret = None
        if hasattr(self, fnname):
            ret = getattr(self, fnname)(e)

        if ret is False:
            return False

        if e.src != 'none' and self.async_transitions and (
           self.async_transitions is True or e.event in self.async_transitions):
            return False

        return ret

    def _enter_state(self, e):
        ret = None
        for fnname in ['on_enter_' + e.dst, 'on_' + e.dst]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _change_state(self, e):
        fnname = 'on_change_state'
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

