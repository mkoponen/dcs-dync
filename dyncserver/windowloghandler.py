from logging import StreamHandler


class WindowLogHandler(StreamHandler):

    def __init__(self, window=None):
        StreamHandler.__init__(self)
        self.window = window

    def emit(self, record):
        if self.window is not None:
            msg = self.format(record)
            self.window.update_log(msg)

    def set_window(self, window):
        self.window = window
