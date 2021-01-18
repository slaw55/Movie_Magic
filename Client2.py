import threading
import selectors
import socket

class Client:
    def __init__(self):
        self.sel = selectors.DefaultSelector()

        # self.host, self.port = "173.79.60.161", 10000
        self.host, self.port = "127.0.0.1", 10000
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.start_connection()

    def start_connection(self):
        addr = (self.host, self.port)
        print("starting connection to", addr)
        self.sock.setblocking(False)
        self.sock.connect_ex(addr)
        events = selectors.EVENT_READ
        self.sel.register(self.sock, events, data=None)

    def sock_listener(self, progress_callback):
        print('listening to server')
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
