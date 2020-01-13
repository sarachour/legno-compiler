import socket
import time
import select
import sys

def SocketConnect(ipaddr,port):
    try:
        #create an AF_INET, STREAM socket (TCP)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print ('Failed to create socket.')
        sys.exit();
    try:
        #Connect to remote server
        s.connect((ipaddr, port))
    except socket.error:
        print ('failed to connect to ip ' + ipaddr)
        sys.exit(1)

    return s

class SICPDevice:

    def __init__(self,ipaddr,port):
        self._ip = ipaddr
        self._port = port
        self._buf = bytearray([])

    def ready(self):
        return not self._sock is None

    def setup(self):
        if self._ip is None or self._port is None:
            self._sock = None
        else:
            self._sock = SocketConnect(self._ip,self._port)

    def close(self):
        self._sock.close()
        time.sleep(1)

    def _flush(self):
        readable, writable, exceptional = select.select([self._sock],
                                                        [],
                                                        [],
                                                        1.0)
        if readable:
            data = self._sock.recv(1024)
        else:
            return

    def _recvall(self,eom=b'\n',timeout_sec=3):
        total_data=[];
        data=self._buf
        self._buf = bytearray([])
        done = False
        while not done:
            if eom in data:
                eom_idx = data.find(eom)
                assert(eom_idx >= 0)
                seg = data[:eom_idx]
                self._buf = data[eom_idx+len(eom):]
                total_data.append(seg)
                done = True
                continue
            else:
                total_data.append(data)

            ready = select.select([self._sock], [], [], timeout_sec)
            if ready[0]:
                data=self._sock.recv(4096)
            else:
                return None

        ba = bytearray([])
        for datum in total_data:
            ba += datum

        return ba


    def _write(self,cmd):
        try :
            #Send cmd string
            print("-> %s" % cmd)
            self._sock.sendall(bytes(cmd,'UTF-8'))
            self._sock.sendall(b'\n')
        except socket.error:
            #Send failed
            print(socket.error)
            print ('send failed <%s>' % cmd)
            sys.exit()

    def write(self,cmd):
        self._flush()
        self._write(cmd)
        time.sleep(0.5)

    def query(self,cmd,decode='UTF-8',eom=b'\n\r>>',timeout_sec=3):
        reply = None
        while reply is None:
            self._flush()
            self._write(cmd)
            time.sleep(0.1)
            reply = self._recvall(eom=eom,timeout_sec=3)

        if not decode is None:
            return reply.decode(decode)
        else:
            return reply

    def get_identifier(self):
        return self.query("*IDN?")
