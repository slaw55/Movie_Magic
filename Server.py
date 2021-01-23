import socket
import selectors


class Server:
    def __init__(self):
        self.sel = selectors.DefaultSelector()
        self.host, self.port = "192.168.1.156", 55555
        #self.host, self.port = "127.0.0.1", 10000
        self.client_list = []
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        self.lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.lsock.bind((self.host, self.port))
        self.lsock.listen()
        print("listening on", (self.host, self.port))
        self.lsock.setblocking(False)
        self.sel.register(self.lsock, selectors.EVENT_READ, data=None)

        self.playpause = False
        self.time = 0

        self.mainloop()

    def accept(self, sock):
        conn, addr = sock.accept()
        print('accepted', conn, 'from', addr)
        conn.setblocking(False)
        self.client_list.append(conn)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

    def read(self, conn, mask):
        header = conn.recv(1)  # Should be ready
        if header:
            if header.decode('utf-8') == 'j':
                self.j_fn()
                return
            elif header.decode('utf-8') == 'p':
                self.playpause = not self.playpause
                payload = self.p_fn()
            elif header.decode('utf-8') == 't':
                body = conn.recv(5).decode('utf-8')
                payload = self.t_fn(body)
            elif header.decode('utf-8') == 's':
                payload = self.p_fn()
                conn.send(payload.encode('utf-8'))
                payload = self.t_fn(str(self.time))
                conn.send(payload.encode('utf-8'))
            for c in self.client_list:
                c.send(payload.encode('utf-8'))  # Hope it won't block
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

    def j_fn(self):
        print('Client joined')

    def p_fn(self):
        if self.playpause:
            payload = 'p0play'
        else:
            payload = 'ppause'
        return payload

    def t_fn(self, time):
        self.time = int(time)
        time = str(self.time).zfill(5)
        payload = 't' + time
        return payload


mmserver = Server()
