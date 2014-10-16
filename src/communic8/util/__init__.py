import fysom


class Fysom(fysom.Fysom):
    def _before_event(self, e):
        fnname = 'on_before_' + e.event
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

    def _after_event(self, e):
        for fnname in ['on_after_' + e.event, 'on_' + e.event]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _leave_state(self, e):
        fnname = 'on_leave_' + e.src
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

    def _enter_state(self, e):
        for fnname in ['on_enter_' + e.dst, 'on_' + e.dst]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _change_state(self, e):
        fnname = 'on_change_state'
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

