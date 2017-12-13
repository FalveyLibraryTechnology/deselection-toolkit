import sys

class ProgressBar:
    def __init__(self, total, size = 65, label = '', advchar='='):
        self.prev = 0
        self.index = 0
        self.size = size - len(label)
        self.total = total / self.size
        self.advchar = advchar
        sys.stdout.write(label + '[%s]%s' % (" " * self.size, '\b' * (self.size + 1)))
        sys.stdout.flush()

    def progress(self, progress = None):
        if progress == None:
            self.index += 1
            progress = self.index
        percent = int(progress / self.total)
        if percent > self.prev:
            for i in range(self.prev, percent):
                sys.stdout.write(self.advchar)
            sys.stdout.flush()
            self.prev = percent

    def finish(self, post = ''):
        for i in range(self.prev, self.size):
            sys.stdout.write("=")
        sys.stdout.write("] %s\n" % post)
        sys.stdout.flush()
