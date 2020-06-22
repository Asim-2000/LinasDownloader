import socket
#creating socket object
serv=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
#AF_INET=IPV4 and SOCK_STREAM=TCP, for UDP we use SOCK_DGRAM

# we dont bind here we m will connet

serv.connect((socket.gethostname(),1234))

# in natural cases we dont connect to the lcoal machine, youc oonnect tot the remote servers

# now, accpet the message sent to us by server
full_msg=" "
while True:
    msg=serv.recv(6)
    if (len(msg)<=0):
        break
    else:
        full_msg+=msg.decode('utf-8')
# 1024 is our buffer
print(full_msg)
