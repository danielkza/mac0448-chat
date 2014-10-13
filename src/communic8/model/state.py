class StateMachine(object):
    states = set()
    transitions = {}

    def __init__(self, initial_state):
        self._current_state = initial_state

    def enter_state(self, state):
        if not state in self.states:
            raise ValueError("Invalid state {0}".format(state))

        current_transitions = self.transitions.get(self.current_state) or set()
        global_transitions = self.transitions.get('all') or set()

        if 'all' not in current_transitions and state not in current_transitions and state not in global_transitions:
            raise ValueError("Invalid transition from {0} to {1}".format(self.current_state, state))

        if hasattr(self, 'on_leave_' + self.current_state):
            getattr(self, 'on_leave_' + self.current_state)(state)

        if hasattr(self, 'on_enter_' + state):
            getattr(self, 'on_enter_' + state)(self.current_state)

        self.current_state = state

    @property
    def current_state(self):
        return self._current_state

    @current_state.setter
    def current_state(self, new_state):
        self.enter_state(new_state)