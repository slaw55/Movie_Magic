from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QListWidget, \
    QListWidgetItem, QTableWidget, QStyle, QSlider, QLabel, QAction, QFileDialog
from PyQt5.QtGui import QPalette, QColor, QIcon, QPainter, QPen
from PyQt5.QtCore import QSize, Qt, QThreadPool, QObject, pyqtSignal, QRunnable, QTime, QTimer
from PyQt5.QtMultimediaWidgets import QVideoWidget
import Client2
import sys
import platform
import vlc


class ThreadSignals(QObject):
    finished = pyqtSignal()
    #result = pyqtSignal(object)
    trigger = pyqtSignal(tuple)


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


class Player(QWidget):
    # Video GUI class

    def __init__(self, parent=None):
        super(Player, self).__init__(parent)

        self.instance = vlc.Instance()
        self.media = None
        self.mediaPlayer = self.instance.media_player_new()

        self.videoWidget = QVideoWidget()


    def create_ui(self):
        # Set up GUI

        # Creates GUI widget
        layout = QHBoxLayout()
        layout.addWidget(self.videoWidget)
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

        # Links VLC object to a frame within the widget
        if platform.system() == "Linux":  # for Linux using the X Server
            self.mediaPlayer.set_xwindow(int(self.videoWidget.winId()))
        elif platform.system() == "Windows":  # for Windows
            self.mediaPlayer.set_hwnd(int(self.videoWidget.winId()))
        elif platform.system() == "Darwin":  # for MacOS
            self.mediaPlayer.set_nsobject(int(self.videoWidget.winId()))

        # Set window size and show
        self.setGeometry(200,200,640,360)
        self.show()

    def setsrc(self, src):
        # Function to open video file
        self.media = self.instance.media_new(src)
        self.create_ui()
        self.mediaPlayer.set_media(self.media)

    def closeEvent(self, event):
        self.mediaPlayer.stop()


class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        self.threadpool = QThreadPool()
        print('Multithreading with maximum %d threads' % self.threadpool.maxThreadCount())

        self.media = None
        self.playing = False
        self.volume = 80
        self.clock = QTimer()
        self.clock.timeout.connect(self.tick)
        self.mlength = 5400
        self.time = 0
        self.timer = QLabel('00:00')

        self.videoWidget = QVideoWidget()
        self.ppbutton = QPushButton()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(self.mlength)
        self.slider.setValue(0)
        self.slider.sliderReleased.connect(self.sliderelease)

        self.client = Client2.Client()

        self.videowindow = Player()

        self.init_ui()


    def init_ui(self):
        self.setWindowTitle("Movie Magic")

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

        self.setStyleSheet("background-color: #30ffac;")


        widget = QWidget()
        widget.setStyleSheet(open('stylesheet.css').read())

        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.ppbutton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.ppbutton.clicked.connect(self.client.sendpp)

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
        if self.videowindow.isVisible():
            self.volume += 10
            self.volumelabel.setText('Volume: {}%'.format(self.volume))
            self.videowindow.mediaPlayer.audio_set_volume(self.volume)
            print(self.videowindow.mediaPlayer.audio_get_volume())

    def volumedown(self):
        if self.videowindow.isVisible():
            self.volume -= 10
            self.volumelabel.setText('Volume: {}%'.format(self.volume))
            self.videowindow.mediaPlayer.audio_set_volume(self.volume)
            print(self.videowindow.mediaPlayer.audio_get_volume())

    def openfile(self):
        # Function to open video file
        src = QFileDialog.getOpenFileName()
        self.videowindow.setsrc(src[0])
        self.videowindow.show()
        self.videowindow.mediaPlayer.play()
        if self.client.connected:
            self.client.requestsync()
            self.enable()
            print(self.videowindow.mediaPlayer.audio_get_volume())
        else:
            self.videowindow.mediaPlayer.set_pause(1)

    def pptoggle(self, state):
        if state == 'pause':
            self.playing = False
            self.ppbutton.setIcon(QIcon(self.style().standardIcon(QStyle.SP_MediaPlay)))
            self.stoptime()
        elif state == '0play':
            self.playing = True
            self.ppbutton.setIcon(QIcon(self.style().standardIcon(QStyle.SP_MediaPause)))
            self.starttime()

    def sliderelease(self):
        num = self.slider.value()
        self.client.sendtime(num)

    def tick(self):
        self.time += 1
        self.update_ui()

    def starttime(self):
        self.clock.start(1000)
        if self.videowindow:
            self.videowindow.mediaPlayer.set_pause(0)

    def stoptime(self):
        self.clock.stop()
        if self.videowindow:
            self.videowindow.mediaPlayer.set_pause(1)

    def settime(self, num):
        self.time = num
        if self.videowindow:
            self.videowindow.mediaPlayer.set_time(num*1000)
        self.update_ui()

    def thread_complete(self):
        print('Thread complete')

    def handle_trigger(self, t):
        if t[0] == 'p':
            self.pptoggle(t[1])
        elif t[0] == 't':
            self.settime(int(t[1]))
        elif t[0] == 'q':
            self.serverlabel.setText('Server disconnected')
            self.disable()

    def disable(self):
        self.stoptime()
        self.videowindow.mediaPlayer.set_pause(1)
        self.ppbutton.setEnabled(False)
        self.slider.setEnabled(False)
        self.openAction.setEnabled(False)

    def enable(self):
        self.ppbutton.setEnabled(True)
        self.slider.setEnabled(True)

    def connect_server(self):
        self.client.start_connection()
        if self.client.connected:
            listener = ThreadWorker(self.client.sock_listener)
            listener.signals.finished.connect(self.thread_complete)
            listener.signals.trigger.connect(self.handle_trigger)
            self.threadpool.start(listener)
            self.serverlabel.setText('Server connected')
            self.enable()
            if self.videowindow.isVisible():
                self.client.requestsync()
        else:
            self.serverlabel.setText('Server connection failed')

    def closeEvent(self, event):
        self.client.sel.close()
        self.clock.on = False


def main():
    app = QApplication([])
    mm = Main()
    sys.exit(app.exec_())


if __name__ == '__main__':
    src = "/Users/kennethlawson/Documents/Movies/Chinatown.1974.720p.HDTV.x264.YIFY.mp4"
    main()
