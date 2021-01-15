
src = "/Users/kennethlawson/Documents/Movies/Chinatown.1974.720p.HDTV.x264.YIFY.mp4"

import sys
import vlc
import platform
import Client2
from PyQt5.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal, QEvent, Qt
from PyQt5.QtWidgets import QApplication, QWidget, QAction, QMainWindow, QVBoxLayout, QPushButton
from PyQt5.QtMultimediaWidgets import QVideoWidget


class ThreadSignals(QObject):
    finished = pyqtSignal()
    #result = pyqtSignal(object)
    trigger = pyqtSignal(str)


class ThreadWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(ThreadWorker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ThreadSignals()
        self.kwargs['progress_callback'] = self.signals.trigger

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            #self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()


class Player(QMainWindow):
    # Video GUI class

    def __init__(self, parent=None):
        super(Player, self).__init__(parent)
        self.setWindowTitle("Movie Magic")

        # Establish new empty VLC instance
        self.instance = vlc.Instance()
        self.media = None
        self.mediaPlayer = self.instance.media_player_new()

        self.videoWidget = QVideoWidget()

        self.create_ui()

        self.threadpool = QThreadPool()
        print('Multithreading with maximum %d threads' % self.threadpool.maxThreadCount())

        self.client = Client2.Client()
        self.listen()

    def create_ui(self):
        # Set up GUI

        # Adds button to open file
        openAction = QAction('&Open', self)
        openAction.triggered.connect(self.openFile)

        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(openAction)

        # Creates GUI widget
        window = QWidget(self)
        self.setCentralWidget(window)

        window.setStyleSheet("""
                QWidget {
                    border: 0px solid black;
                    border-radius: 0px;
                    background-color: rgb(255, 255, 255);
                    }
                """)

        layout = QVBoxLayout()
        layout.addWidget(self.videoWidget)
        window.setLayout(layout)

        # Links VLC object to a frame within the widget
        if platform.system() == "Linux":  # for Linux using the X Server
            self.mediaPlayer.set_xwindow(int(self.videoWidget.winId()))
        elif platform.system() == "Windows":  # for Windows
            self.mediaPlayer.set_hwnd(int(self.videoWidget.winId()))
        elif platform.system() == "Darwin":  # for MacOS
            self.mediaPlayer.set_nsobject(int(self.videoWidget.winId()))

        window2 = QWidget(self)

        # Set window size and show
        self.setGeometry(100, 100, 555, 300)
        self.show()


    def listen(self):
        listener = ThreadWorker(self.client.sock_listener)
        listener.signals.finished.connect(self.thread_complete)
        listener.signals.trigger.connect(self.handle_trigger)
        self.threadpool.start(listener)

    def handle_trigger(self, p):
        if p == 'play':
            self.mediaPlayer.set_pause(0)
        elif p == 'pause':
            self.mediaPlayer.set_pause(1)

    def thread_complete(self):
        print('Thread complete')

    def openFile(self):
        # Function to open video file

        self.media = self.instance.media_new(src)
        self.mediaPlayer.set_media(self.media)
        self.mediaPlayer.play()

    def closeEvent(self, event):
        self.client.sel.close()


def main():
    # Entry point

    app = QApplication(sys.argv)
    player = Player()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
