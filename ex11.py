from socket import AF_INET, socket, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread
import sys
import time
quitcmd = '/quit'
default_port = 12345

class Chatting:
    def __init__(self, host, port):
        print('Chatting.__init__')
        self.addr = (host,port)
        self.BUFSIZ = 512
        self.sock = socket(AF_INET,SOCK_STREAM)
        self.loginf = open("login.txt", "r")
        
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
        self.usernames = []
        self.passwords = []
        for entry in self.loginf: #assigning usernames and passwords from file
        	entry.strip()
        	entry = entry.rstrip("\n")
        	entries = entry.split(" ")
        	self.usernames.append(entries[0])
        	self.passwords.append(entries[1])
        	print(entries[0], entries[1])
        self.loginf.close()
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
        password = self.recv_mesg(cli)
        isUser = 0
        index = 0
        for username in self.usernames:
        	if username == name:
        		realPass = self.passwords[index]
        		if realPass == password:
        			isUser = 1
        	index = index + 1
        role = self.recv_mesg(cli)
        if isUser == 0:
        	self.send_mesg(cli,"-1") #to signal "stop, you failed"
        	print("failed login attempt by user", name)
        else:
        	self.send_mesg(cli,"1")
        	mesg = "{} has joined as {}.".format(name, role)
        	print(mesg)
        self.cli_info[cli]['name'] = name
        self.cli_info[cli]['role'] = role
        while True:
	        try:
	        	msg = quitcmd
	        	if isUser == 1:
	        	    msg = self.recv_mesg(cli)
	        except OSError:
	            print('connection closed')
	            break
	        if msg != quitcmd and isUser == 1:
	            self.broadcast(msg)
	        else:
	            deleted = []
	            for cli in self.cli_info:
	                cli_name = self.cli_info[cli]['name']
	                cli_role = self.cli_info[cli]['role']
	                if cli_name == name:
	                    if cli_role == 'viewer' or cli_role == 'client':
	                        self.send_mesg(cli,quitcmd)
	                    deleted.append(cli)
	            for cli in deleted:
	                cli.close()
	                del self.cli_info[cli]
	            if isUser != 0:
	            	self.broadcast('User has left')
	            	print('User', name, 'has left')
	            break
    def broadcast(self, msg):
        deleted = []
        for cli in self.cli_info:
            if self.cli_info[cli]['role'] == 'viewer' or self.cli_info[cli]['role'] == 'client':
                name = self.cli_info[cli]['name']
                print('broadcast to user',name, 'message:', msg)
                try:
                    self.send_mesg(cli, msg)
                except OSError:
                    print('possibly closed. removed from the connections')
                    deleted.append(cli)
        for d in deleted:
            del self.cli_info[d]

class Client(Chatting):
    def __init__(self, name, password, host, port):
        super().__init__(host,port)
        print('Client.__init__')
        self.accepted = 0
        self.name = name
        self.password = password
        self.sock.connect(self.addr)
        self.send_mesg(self.sock, name)
        self.send_mesg(self.sock, password)
        self.send_mesg(self.sock,'client')
    def start(self):
        self.recvth = Thread(target = Client.recv_loop,
                        args = (self,))
        self.recvth.start()
        self.recvth.join()
    def send_loop(self):
        while True:
            
            user_msg = input('Enter new message:\n')
            if user_msg != quitcmd:
                msg = self.name + ':' + user_msg
            else:
                msg = user_msg
            try:
                self.send_mesg(self.sock, msg)
                if (msg == quitcmd):
                	break
            except OSError:
                print('connection closed')
                break
    def recv_loop(self):
    	msg = self.recv_mesg(self.sock) #initial -1 or 1
    	if msg == "1":
    		self.sendth = Thread(target = Client.send_loop,
                        args = (self,))
    		self.sendth.start()
    		print("You have successfully logged in")
    		while True:
		        msg = self.recv_mesg(self.sock)
		        if msg == quitcmd:
		            print('You have quit')
		            break
		        elif msg == "-1":
		        	print("No login, incorrect username or password")
		        	break
		        else:
		            print(msg)
    	else:
    		print("No login, incorrect username or password", msg, "end")
    
def main(argc, argv):
    if argv[1] == 'server':
        host = argv[2]
        if argc <= 3:
            port = default_port
        else:
            port = int(argv[3])
        server = Server(host,port)
        server.start()
    elif argv[1] == 'client':
        name = argv[2]
        password = argv[3]
        host = argv[4]
        if argc <= 5:
            port = default_port
        else:
            port = int(argv[5])
        client = Client(name,password,host,port)
        time.sleep(1)
        client.start()
    else:
        print("Undefined rule")

if __name__ == '__main__':
    main(len(sys.argv), sys.argv)
