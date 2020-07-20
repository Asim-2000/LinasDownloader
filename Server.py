from socket import *
import time
import os
import multiprocessing
import curses
import argparse


serverIP = gethostname() # ip address for all servers
bufferSize = 8192  # maximum number of bytes that can be transferred in one instance

# adding module description
parser = argparse.ArgumentParser(  # initializing parser
    description="Multithreaded Server: Creates multiple instances of a virtual server containing a video file to be sent to a client as interpreted."
)

#Using the parser to add paramteres that can be used through command line flags
parser.add_argument('-n', '--numOfServers', help="Number of Ports", type=int,default=5)
parser.add_argument('-i', '--timeInterval', help="Time Interval for refresh", type=int, default=1)
parser.add_argument('-f', '--fileName', help="File/ Directory with extension", default="Rivers.mp4")
parser.add_argument('-p', '--ListOfPorts', nargs='+', help="Port Numbers for all servers", type=int,default=[12000,13000,14000,15000,16000])

args = parser.parse_args()  # command-line arguments are parsed to be stored into appropriate variables
numOfServers = args.numOfServers  # number of virtual servers to be initialized
refresh_time = args.timeInterval  # time interval in seconds after which metrics screen is to be updated
fileName = args.fileName  # file location of video file to be sent
ports = args.ListOfPorts  # ports list for all virtual servers to be initialized


####supplementary functions####
def get_range(message):  # to interpret formatted range request sent by client, sent in format 'bytes=0-1023'
    start = int(message.split('-')[0].split('=')[1])  # to get start of range
    end = int(message.split('-')[1]) # to get end of range
    return start, end


def copy_file_range(in_file, out,range_from,range_to): # Copies only the range between range_from/to.
    in_file.seek(range_from)  # media file I/O pointer is taken to start of range request
    bytes_to_copy = 1 + range_to - range_from   # bytes to be sent to client total, add 1 because the range is inclusive
    buf_length = bufferSize  # length of socket buffer a.k.a maximum number of bytes that can be sent
    bytes_copied = 0  # bytes that have been sent to client so far
    while bytes_copied < bytes_to_copy:
        # Media file is read from until required size threshold is met. Minimum between maximum buffer length and bytes left to
        # copy is taken in the event that we are near the end of the required segment, to avoid copying any excess bytes
        read_buf = in_file.read(min(buf_length, (bytes_to_copy-bytes_copied)))
        if len(read_buf) == 0: # if no data was received from file
            break
        out.send(read_buf)  # read bytes are sent to client socket
        bytes_copied += len(read_buf)  # read and sent bytes are added to overall counter
        time.sleep(0.1)  # delay to prevent any errors on client side


"""Actual Prcoess
The functionality of each and every line is stated in the comments
"""
def serverProcess(m):
    global ports
    global numOfServers 
    global refresh_time 
    global fileName
    serverPort = ports[m] # appropriate port number is taken from overall ports list
    server_socket = socket(AF_INET, SOCK_STREAM)
    server_socket.bind((serverIP, serverPort))
    server_socket.listen(5)  # server started, listening for requests from client
    while True:
        try:
            sck, address = server_socket.accept()
            message = sck.recv(4096)
            message = message.decode()
            if message == 'size':  # if size request for file is received from client
                mediaSize = os.path.getsize(fileName)
                mediaSize = str(mediaSize).encode() # string converted to bytes
                sck.send(mediaSize) # size sent back to client through socket
                time.sleep(0.2) # delay to prevent errors on client end
                sck.close() # socket closed, server goes back to listening
                continue
            elif not message: # for blank check messages received from client e.g in checkPorts function
                sck.close() # message is ignored, server goes back to listening
                continue
            range_from, range_to = get_range(message) # if range request is received. Message is decoded to get start and end of byte range request
            # input/output files, socket and range are inputted to function to give only required bytes from file to user
            with open(fileName,'rb') as media_file:  # input media file is opened
                copy_file_range(media_file,sck,range_from,range_to)
            sck.close()
        except (ConnectionResetError, ConnectionRefusedError):
            sck.close()
            continue

"""Main Function"""
if __name__ == "__main__":
    servers = []  # list to store and keep track of all server processes
    thread_input = ''  # used to kill servers with required command
    print('Starting servers. Please wait....')

    server_status = [] # list to keep track of status of all servers
    for n in range(0, numOfServers):
        server_status.append('Alive') # servers marked as alive

    for i in range(0, numOfServers):
        # sub-process/thread for each required server is started and added to servers list
        server_thread = multiprocessing.Process(target=serverProcess, args=(i,))
        servers.append(server_thread)
        server_thread.start()

    time.sleep(0.6)  # delay to make sure all servers have been started properly
    screen = curses.initscr()  # metrics screen initialized
    while True:
        # information for all initialized servers added to screen
        for k in range(0, numOfServers):
            screen.addstr(k, 0,f"Port: {ports[k]}, Status: {server_status[k]}, To Shutdown Server {k + 1} Enter E{k + 1}         ")
            screen.refresh() # screen will only update when refreshed
        # looping input to kill specific server with number, using format e.g 'E1' to kill first server
        screen.addstr(numOfServers+1, 0, "Kill server? Enter the key below: ")
        thread_input = screen.getstr(numOfServers+2, 0).decode()
        screen.addstr(numOfServers+2, 0, "                     ")  # input line blanked for next input
        if thread_input == 'all': # 'all' command can also be inputted instead to instantly kill all servers
            for server in servers:
                server.terminate()  # servers terminated through loop
            for s in server_status:
                s = 'Dead' # all servers marked as dead for metrics
            curses.endwin()
            input('All servers terminated. Press Enter to exit...')
            break  # program exits
        elif thread_input and thread_input != '':
            try:
                kill = int(''.join(list(filter(str.isdigit, thread_input))))-1  # server number to be killed retrieved through parsing integers characters from string input
                servers[kill].terminate()  # required server killed
                server_status[kill] = 'Dead'
                screen.addstr(numOfServers+3, 0, 'Server ' + str(kill+1) + ' killed...                          ')
            except IndexError:  # in event that server does not exist for inputted server
                screen.addstr(numOfServers+3, 0, 'This server doesn\'t exist, please try again                          ')
        curses.napms(refresh_time*100)  # metrics window updated according to user input
