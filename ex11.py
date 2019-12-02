from socket import AF_INET, socket, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread
import sys

quitcmd = '/quit'
default_port = 12345

class Chatting:
    def __init__(self, host, port):
        print('Chatting.__init__')
        self.addr = (host,port)
        self.BUFSIZ = 512
        self.sock = socket(AF_INET,SOCK_STREAM)
    def send_mesg(self, sock, msg):
        hdr = bytearray('00','utf-8')
        hdr[0] = len(msg) // 256
        hdr[1] = len(msg) % 256
        assert(len(hdr) == 2)
        sock.sendall(hdr)
        sock.sendall(bytes(msg,'utf-8'))
    def recv_mesg(self, sock):
        hdr = b''
        while len(hdr) < 2:
            hdr += sock.recv(2 - len(hdr))
        nbytes = hdr[0] * 256 + hdr[1]
        nbytes_read = 0
        data = b''
        while nbytes_read < nbytes:
            data += sock.recv(nbytes - nbytes_read)
            nbytes_read = len(data)
        return data.decode('utf-8')

class Server(Chatting):
    def __init__(self, host, port:int):
        super().__init__(host,port)
        print('Server.__init__')
        self.sock.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
        self.sock.bind(self.addr)
        self.cli_info = {}
    def start(self):
        self.sock.listen(1)
        print('waiting')
        self.accept_thread = Thread(target=Server.accept_loop,
                                    args=(self,))
        self.accept_thread.start()
        self.accept_thread.join()
        self.sock.close()
    def accept_loop(self):
        while True:
            cli,caddr = self.sock.accept()
            th = Thread(target = Server.handle_cli,
                        args = (self,cli))
            self.cli_info[cli] = {'addr': caddr,
                                  'thread': th}
            th.start()
    def handle_cli(self,cli):
        name = self.recv_mesg(cli)
        role = self.recv_mesg(cli)
        mesg = "{} has joined as {}.".format(name, role)
        print(mesg)
        self.cli_info[cli]['name'] = name
        self.cli_info[cli]['role'] = role
        while True:
            try:
                msg = self.recv_mesg(cli)
            except OSError:
                print('connection closed')
                break
            if msg != quitcmd:
                self.broadcast(msg)
            else:
                deleted = []
                for cli in self.cli_info:
                    cli_name = self.cli_info[cli]['name']
                    cli_role = self.cli_info[cli]['role']
                    if cli_name == name:
                        if cli_role == 'viewer':
                            self.send_mesg(cli,quitcmd)
                        deleted.append(cli)
                for cli in deleted:
                    cli.close()
                    del self.cli_info[cli]
                self.broadcast('client left')
                break
    def broadcast(self, msg):
        deleted = []
        for cli in self.cli_info:
            if self.cli_info[cli]['role'] == 'viewer':
                name = self.cli_info[cli]['name']
                print('broadcast', msg)
                try:
                    self.send_mesg(cli, msg)
                except OSError:
                    print('possibly closed. removed from the connections')
                    deleted.append(cli)
        for d in deleted:
            del self.cli_info[d]

class Client(Chatting):
    def __init__(self, name, host, port):
        super().__init__(host,port)
        print('Client.__init__')
        self.name = name
        self.sock.connect(self.addr)
        self.send_mesg(self.sock, name)

class Viewer(Client):
    def __init__(self, name, host, port:int):
        super().__init__(name,host,port)
        print('Viewer.__init__')
        self.send_mesg(self.sock, 'viewer')
    def recv_loop(self):
        while True:
            msg = self.recv_mesg(self.sock)
            if msg == quitcmd:
                print('quit')
                break
            else:
                print(msg)

class Sender(Client):
    def __init__(self, name, host, port:int):
        super().__init__(name,host,port)
        print('Sender.__init__')
        self.name = name
        self.send_mesg(self.sock,'sender')
    def send_loop(self):
        while True:
            user_msg = input('Enter input: ')
            if user_msg != quitcmd:
                msg = self.name + ':' + user_msg
            else:
                msg = user_msg
            try:
                self.send_mesg(self.sock, msg)
            except OSError:
                print('connection closed')
                break

def main(argc, argv):
    if argv[1] == 'server':
        host = argv[2]
        if argc <= 3:
            port = default_port
        else:
            port = int(argv[3])
        server = Server(host,port)
        server.start()
    elif argv[1] == 'viewer':
        name = argv[2]
        host = argv[3]
        if argc <= 4:
            port = default_port
        else:
            port = int(argv[4])
        viewer = Viewer(name,host,port)
        viewer.recv_loop()
    elif argv[1] == 'sender':
        name = argv[2]
        host = argv[3]
        if argc <= 4:
            port = default_port
        else:
            port = int(argv[4])
        viewer = Sender(name,host,port)
        viewer.send_loop()
    else:
        print("Undefined rule")

if __name__ == '__main__':
    main(len(sys.argv), sys.argv)
