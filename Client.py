from PyQt5.QtWidgets import QWidget, QPushButton, QApplication
from PyQt5.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal
import sys
import socket
import selectors


class ThreadSignals(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(object)
    progress = pyqtSignal(str)


class ThreadWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(ThreadWorker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ThreadSignals()
        self.kwargs['progress_callback'] = self.signals.progress

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class GUI(QWidget):

    def __init__(self):
        super().__init__()

        self.threadpool = QThreadPool()
        print('Multithreading with maximum %d threads' % self.threadpool.maxThreadCount())

        self.initUI()

        self.sel = selectors.DefaultSelector()

        # self.host, self.port = "173.79.60.161", 10000
        self.host, self.port = "127.0.0.1", 10000
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.start_connection()

        worker = ThreadWorker(self.sock_listener)
        worker.signals.result.connect(self.print_output)
        worker.signals.finished.connect(self.thread_complete)
        worker.signals.progress.connect(self.progress_fn)
        self.threadpool.start(worker)


    def initUI(self):

        self.setGeometry(300, 300, 300, 220)
        self.setWindowTitle('MovieMagic')

        button = QPushButton('Ping', self)
        button.setToolTip('Test echo response')
        button.move(100, 70)
        button.clicked.connect(self.on_click)

        self.show()

    def start_connection(self):
        addr = (self.host, self.port)
        print("starting connection to", addr)
        self.sock.setblocking(False)
        self.sock.connect_ex(addr)
        events = selectors.EVENT_READ
        self.sel.register(self.sock, events, self.delegate)

    def sock_listener(self, progress_callback):
        print('listening')
        try:
            while True:
                trigger = self.sel.select(timeout=None)
                for key, mask in trigger:
                    callback = key.data
                    callback(key.fileobj, mask)
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        except OSError:
            return
        finally:
            self.sel.close()

    def delegate(self, conn, mask):
        data = self.sock.recv(1000)  # Should be ready
        if data:
            print('recieved: {}'.format(data.decode('utf-8')))
        else:
            print('closing', conn)
            self.sel.unregister(conn)
            self.sock.close()

    def print_output(self, s):
        if s:
            print(s)

    def thread_complete(self):
        print('Thread complete')

    def progress_fn(self, n):
        print(n)

    def on_click(self):
        data = 'Test'
        print('sending: {}'.format(data))
        self.sock.send(data.encode('utf-8'))

    def closeEvent(self, event):
        self.sel.close()


app = QApplication(sys.argv)
gui = GUI()
sys.exit(app.exec_())
