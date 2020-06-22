import socket
#creating socket object
serv=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
#F_INET=IPV4 and SOCK_STREAM=TCP, for UDP we use SOCK_DGRAM

#bind the server with a tuple of host and port number. Go with any port number, go with higher one
serv.bind((socket.gethostname(),1234))

#socket is the end point that recives data

# start listenign

serv.listen(5)   # a queue of 5

while True:
    clientsocket, address=serv.accept()   #.accpet returns  a tuuple of client socket and client address
    print(f"Connection from {address} has been established!")
    # send to client's socket
    clientsocket.send(bytes("Welcome to the server","utf-8")) # utf-8 is the type of data/bytes we are sending 
    clientsocket.close()
