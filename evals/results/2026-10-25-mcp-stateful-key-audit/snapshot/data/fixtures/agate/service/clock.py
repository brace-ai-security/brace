from time import monotonic

class Clock:
    def now(self):
        return monotonic()
