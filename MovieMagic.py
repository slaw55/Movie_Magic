from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,  QStyle, \
    QSlider, QLabel, QAction, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QThreadPool, QObject, pyqtSignal, QRunnable, QTimer
from PyQt5.QtMultimediaWidgets import QVideoWidget
import sys
import platform
import vlc
import selectors
import socket
import time


class ThreadSignals(QObject):
    # Possible callbacks for worker threads
    finished = pyqtSignal()
    trigger = pyqtSignal(tuple)


class ThreadWorker(QRunnable):
    # Thread operator class
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
        finally:
            self.signals.finished.emit()


class Player(QWidget):

    # Video viewing panel
    def __init__(self, parent=None):
        super(Player, self).__init__(parent)

        # Creates VLC instance and a new media player within it
        self.instance = vlc.Instance()
        self.media = None
        self.mediaPlayer = self.instance.media_player_new()

        # creates a place for the VLC instance to go
        self.videoWidget = QVideoWidget()

    def create_ui(self):
        # Set up GUI

        layout = QHBoxLayout()
        layout.addWidget(self.videoWidget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Links VLC object to a frame within the widget
        if platform.system() == "Linux":  # for Linux using the X Server
            self.mediaPlayer.set_xwindow(int(self.videoWidget.winId()))
        elif platform.system() == "Windows":  # for Windows
            self.mediaPlayer.set_hwnd(int(self.videoWidget.winId()))
        elif platform.system() == "Darwin":  # for MacOS
            self.mediaPlayer.set_nsobject(int(self.videoWidget.winId()))

        # Set window size and show
        self.setGeometry(200, 200, 640, 360)
        self.show()

    def setsrc(self, src):
        # Function to open video file
        self.media = self.instance.media_new(src)
        self.create_ui()
        self.mediaPlayer.set_media(self.media)

    def closeEvent(self, event):
        # Pause on close
        self.mediaPlayer.stop()


class Client:
    def __init__(self):
        self.sel = None
        self.connected = False

        # self.host, self.port = "173.79.60.161", 10000
        self.host, self.port = "127.0.0.1", 10000
        self.sock = None

    def start_connection(self):
        addr = (self.host, self.port)
        self.sel = selectors.DefaultSelector()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.connect_ex(addr)
        time.sleep(1)
        try:
            data = 'j'
            self.sock.sendall(data.encode('utf-8'))
            events = selectors.EVENT_READ
            self.sel.register(self.sock, events, data=None)
            self.connected = True
        except:
            print('Failed to join server')
            self.connected = False



    def sock_listener(self, progress_callback):
        try:
            while True:
                trigger = self.sel.select(timeout=None)
                key, mask = trigger[0]
                data = self.sock.recv(6)
                if data:
                    header = data.decode('utf-8')[:1]
                    body = data.decode('utf-8')[-5:]
                    passback = (header, body)
                    progress_callback.emit(passback)
                else:
                    print('closing', key.fileobj)
                    self.sel.unregister(key.fileobj)
                    self.sock.close()
                    passback = ('q','00000')
                    progress_callback.emit(passback)
                    break
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        except OSError:
            return
        finally:
            self.sel.close()

    def sendpp(self):
        data = 'p'
        self.sock.sendall(data.encode('utf-8'))

    def sendtime(self, time):
        data = 't{}'.format(str(time).zfill(5))
        self.sock.sendall(data.encode('utf-8'))

    def requestsync(self):
        data = 's'
        self.sock.sendall(data.encode('utf-8'))


class Main(QMainWindow):
    def __init__(self):
        super().__init__()

        # Add ability to multi-thread
        self.threadpool = QThreadPool()

        # Add subclasses for client and viewer
        self.client = Client()
        self.videowindow = Player()

        # Set media properties
        self.media = None
        self.playing = False
        self.volume = 80
        self.time = 0
        self.mlength = 7200

        # Build internal clock
        self.clock = QTimer()
        self.clock.timeout.connect(self.tick)

        # Set up GUI
        self.timer = QLabel('00:00')
        self.videoWidget = QVideoWidget()
        self.ppbutton = QPushButton()
        self.slider = QSlider(Qt.Horizontal)
        self.init_ui()

    def init_ui(self):
        # Name window
        self.setWindowTitle("Movie Magic")

        # Set menu bar options
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        servermenu = menuBar.addMenu('&Server')
        volumemenu = menuBar.addMenu('&Volume')

        self.openAction = QAction('&Load Movie', self)
        self.openAction.triggered.connect(self.openfile)
        fileMenu.addAction(self.openAction)

        serverconnect = QAction('&Connect', self)
        serverconnect.triggered.connect(self.connect_server)
        servermenu.addAction(serverconnect)

        volumeup = QAction('&Increase', self)
        volumedown = QAction('&Decrease', self)
        volumeup.triggered.connect(self.volumeup)
        volumedown.triggered.connect(self.volumedown)
        volumemenu.addAction(volumeup)
        volumemenu.addAction(volumedown)

        # Build main window
        self.setStyleSheet("background-color: #30ffac;")
        widget = QWidget()
        widget.setStyleSheet(open('stylesheet.css').read())

        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.ppbutton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.ppbutton.clicked.connect(self.client.sendpp)

        self.slider.setMaximum(self.mlength)
        self.slider.setValue(0)
        self.slider.sliderReleased.connect(self.sliderelease)

        self.ppbutton.setEnabled(False)
        self.slider.setEnabled(False)

        layout.addWidget(self.ppbutton)
        layout.addWidget(self.slider)
        layout.addWidget(self.timer)

        layout2 = QHBoxLayout()

        self.serverlabel = QLabel('No server connected', self)
        self.serverlabel.setStyleSheet("color: #9800DA")
        self.volumelabel = QLabel('Volume: {}%'.format(self.volume), self)
        self.volumelabel.setStyleSheet("color: #B38200")
        self.volumelabel.setAlignment(Qt.AlignRight)

        layout2.addWidget(self.serverlabel)
        layout2.addWidget(self.volumelabel)

        olayout = QVBoxLayout()
        olayout.setSpacing(0)
        olayout.addLayout(layout)
        olayout.addLayout(layout2)

        widget.setLayout(olayout)
        self.resize(500, 70)

        self.setCentralWidget(widget)
        self.show()

    def update_ui(self):
        # updates timer to reflect Main timer value
        m, s = divmod(self.time, 60)
        h, m = divmod(m, 60)
        self.slider.setValue(self.time)
        secstr = str(s).zfill(2)
        minstr = str(m).zfill(2)
        if h > 0:
            self.timer.setText('{}:{}:{}'.format(h, minstr, secstr))
        else:
            self.timer.setText('{}:{}'.format(minstr, secstr))

    def volumeup(self):
        # turns volume up 10%
        if self.videowindow.isVisible():
            self.volume += 10
            self.volumelabel.setText('Volume: {}%'.format(self.volume))
            self.videowindow.mediaPlayer.audio_set_volume(self.volume)

    def volumedown(self):
        # turns volume down 10%
        if self.videowindow.isVisible():
            self.volume -= 10
            self.volumelabel.setText('Volume: {}%'.format(self.volume))
            self.videowindow.mediaPlayer.audio_set_volume(self.volume)

    def openfile(self):
        # Function to open video file
        src = QFileDialog.getOpenFileName()
        self.videowindow.setsrc(src[0])
        self.videowindow.show()
        self.videowindow.mediaPlayer.play()
        if self.client.connected:
            # Asks server for timestamp and play/pause
            self.client.requestsync()

            self.enable()
        else:
            self.videowindow.mediaPlayer.set_pause(1)

    def pptoggle(self, state):
        # Sets play/pause to server input
        if state == 'pause':
            self.playing = False
            self.ppbutton.setIcon(QIcon(self.style().standardIcon(QStyle.SP_MediaPlay)))
            self.stoptime()
        elif state == '0play':
            self.playing = True
            self.ppbutton.setIcon(QIcon(self.style().standardIcon(QStyle.SP_MediaPause)))
            self.starttime()

    def sliderelease(self):
        # Tells server to update time
        num = self.slider.value()
        self.client.sendtime(num)

    def tick(self):
        # Updates Main time
        self.time += 1
        self.update_ui()

    def starttime(self):
        # Starts main clock counting every second and plays video
        self.clock.start(1000)
        if self.videowindow:
            self.videowindow.mediaPlayer.set_pause(0)

    def stoptime(self):
        # Stops main clock counting every second and pauses video
        self.clock.stop()
        if self.videowindow:
            self.videowindow.mediaPlayer.set_pause(1)

    def settime(self, num):
        # Takes server input and updates Main clock and movie time
        self.time = num
        if self.videowindow:
            self.videowindow.mediaPlayer.set_time(num*1000)
        self.update_ui()

    def thread_complete(self):
        # Calls out when a thread has finished executing
        print('Thread complete')

    def handle_trigger(self, t):
        # Delegates server commands
        if t[0] == 'p':
            self.pptoggle(t[1])
        elif t[0] == 't':
            self.settime(int(t[1]))
        elif t[0] == 'q':
            self.serverlabel.setText('Server disconnected')
            self.disable()

    def disable(self):
        # Locks UI
        self.stoptime()
        self.videowindow.mediaPlayer.set_pause(1)
        self.ppbutton.setEnabled(False)
        self.slider.setEnabled(False)
        self.openAction.setEnabled(False)

    def enable(self):
        # Unlocks UI
        self.ppbutton.setEnabled(True)
        self.slider.setEnabled(True)

    def connect_server(self):
        # Tries to connect to server
        self.client.start_connection()
        if self.client.connected:
            listener = ThreadWorker(self.client.sock_listener)
            listener.signals.finished.connect(self.thread_complete)
            listener.signals.trigger.connect(self.handle_trigger)
            self.threadpool.start(listener)
            self.serverlabel.setText('Server connected')
            self.enable()

            # If a movie is on, it auto-syncs to server
            if self.videowindow.isVisible():
                self.client.requestsync()
        else:
            self.serverlabel.setText('Server connection failed')

    def closeEvent(self, event):
        # On close, make sure all selectors are shut down
        self.client.sel.close()


def main():
    app = QApplication([])
    mm = Main()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
