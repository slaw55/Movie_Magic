import socket
import selectors


class Server:
    def __init__(self):
        self.sel = selectors.DefaultSelector()
        # self.host, self.port = "192.168.1.156", 10000
        self.host, self.port = "127.0.0.1", 10000
        self.client_list = []
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind((self.host, self.port))
        self.lsock.listen()
        print("listening on", (self.host, self.port))
        self.lsock.setblocking(False)
        self.sel.register(self.lsock, selectors.EVENT_READ, data=None)

        self.playpause = 'play'

        self.mainloop()

    def accept(self, sock):
        conn, addr = sock.accept()
        print('accepted', conn, 'from', addr)
        conn.setblocking(False)
        self.client_list.append(conn)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

    def read(self, conn, mask):
        data = conn.recv(1000)  # Should be ready
        if data:
            if self.playpause == 'play':
                self.playpause = 'pause'
            elif self.playpause == 'pause':
                self.playpause = 'play'
            print('broadcasting', self.playpause)
            for c in self.client_list:
                c.send(self.playpause.encode('utf-8'))  # Hope it won't block
        else:
            print('closing', conn)
            self.sel.unregister(conn)
            self.client_list.remove(conn)
            conn.close()

    def mainloop(self):
        try:
            while True:
                trigger = self.sel.select(timeout=None)
                for key, mask in trigger:
                    if key.data is None:
                        self.accept(key.fileobj)
                    else:
                        callback = key.data
                        callback(key.fileobj, mask)
        except KeyboardInterrupt:
            print("caught keyboard interrupt, exiting")
        finally:
            self.sel.close()


mmserver = Server()
