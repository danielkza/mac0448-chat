import fysom


class Fysom(fysom.Fysom):
    async_transitions = False

    def __init__(self, *args, **kwargs):
        fysom.Fysom.__init__(self, *args, **kwargs)
        self._current_event = None

    def _before_event(self, e):
        fnname = 'on_before_' + e.event
        ret = None
        if hasattr(self, fnname):
            ret = getattr(self, fnname)(e)

        if ret is False:
            if hasattr(e, 'error_callback'):
                new_ret = e.error_callback()
                if new_ret is not None:
                    ret = new_ret

        if ret is not False:
            self._current_event = e

        return ret

    def _after_event(self, e):
        ret = None
        for fnname in ['on_after_' + e.event, 'on_' + e.event]:
            if hasattr(self, fnname):
                ret = getattr(self, fnname)(e)
                break

        if hasattr(e, 'callback'):
            e.callback(ret)

        self._current_event = None

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
        for fnname in ['on_enter_' + e.dst, 'on_' + e.dst]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _change_state(self, e):
        fnname = 'on_change_state'
        if hasattr(self, fnname):
            return getattr(self, fnname)(e)

    def cancel_transition(self):
        if not hasattr(self, 'transition'):
            return

        del self.transition
        if self._current_event:
            ev = self._current_event
            if hasattr(ev, 'error_callback'):
                ev.error_callback()

        self._current_event = None

