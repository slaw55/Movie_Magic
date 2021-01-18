import selectors
import socket
import time

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
