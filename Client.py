from socket import *
import threading
import time
import os
import curses
import argparse

####initial inputs/global variables####
Buffer_size = 8192  # maximum number of bytes that can be transferred in one instance
mediaSize = 0  # known size of media file, initialized
threads = []  # array to store all client threads
end = False  # boolean variable to tell curses metrics screen to exit
totalDownloaded = 0  # total downloaded bytes from all servers combined of file
serverSize = []  # bytes to be downloaded of file from each server
downloadedSize = []  # bytes downloaded so far of file from each server

# .............................. inputs for running the script file ........................... #

# adding module description
parser = argparse.ArgumentParser(
    description="Client: Downloads a video file simultaneously from multiple servers by applying load division, multithreading and file segmentation/recombination."
)

# adding parameters through command-line flags
parser.add_argument('-i', '--timeInterval', help="Time Interval for refresh", type=int, default=1)
parser.add_argument('-o', '--outputLocation', help="File/ Directory of copied file with extension", default="new.mp4")
parser.add_argument('-p', '--portsList', nargs='+', help="Port Numbers for all servers", type=int,default=[12000, 13000, 14000, 15000, 16000])
parser.add_argument('-a', '--serverIP', help="IP Address of Server",default=gethostname())
parser.add_argument('-r', '--resume', help="Resume Interrupted download or not", type=bool,default=True)

args = parser.parse_args()  # command-line arguments are parsed to be stored into appropriate variables
ports = args.portsList  # ports list supplied of all possible servers
timeInterval = args.timeInterval  # time interval in seconds after which metrics screen is to be updated
output_location = args.outputLocation  # location of output video file
serverIP = args.serverIP  # ip address of server to connect to
resume = args.resume  # if true, interrupted download from server will be resumed, otherwise the whole segment for that server will be redownloaded


""" Initializing the download Size arrays and the server size arrays"""
for i in range(0, len(ports)): 
    serverSize.append(0)
    downloadedSize.append(0)


"""Function to check all known servers
returns : Servers that are alive
"""
def checkPorts(ports):  
    while True:
        try:
            livePorts = []  # array to store all servers known to be working so far
            for i in ports: # all known ports checked
                check = socket(AF_INET,SOCK_STREAM)
                result = check.connect_ex((serverIP,i))  # blank check message sent to each known server
                #if the server is alive then append it to the list of live ports
                if result == 0:  
                    livePorts.append(i) 
                check.close()
                time.sleep(0.1)
            break
        except (ConnectionResetError,ConnectionRefusedError):
            continue
    return livePorts

"""
Functionailty:  formats headers in the following way: 'bytes=0-1023', where 0 is start and 1023 is end of byte range"""
def formatHeaders(numOfServers,start,end):
    headers = [] # list to store all byte requests for current instance
    if start == 0: # in event of initial segmentation in main function
        chunkSize = int(mediaSize / numOfServers) # whole file is segmented into even chunks
    else: # in event of sub-segmentation in error handling/load balancing
        chunkSize = int((end-start)/numOfServers) # required portion is segmented into even chunks
    for i in range(0, numOfServers): # generating range requests for all required servers
        if i == numOfServers - 1: # in event that last allocated server is found in current division instance
            headers.append('bytes=' + str(start) + '-' + str(end)) # all excess part of the current segment is given to last server
        else: # in event of any other allocated server in current division instance
            headers.append('bytes=' + str(start) + '-' + str(start + chunkSize))  # divided part of segment is given to current server
        start += chunkSize + 1 # jumping to next portion of divided segment
    return headers # range requests returned


"""Recombination function
Functionality: Recombines all binary segments and removes them
Returns: the original ".mp4" file
"""
def fileRecombining():  
    with open(output_location, 'wb') as newFile: # output media file opened for writing into
        for i in range(0,numOfServers):  # all segments from initial segmentation taken in required order
            file = open(f"fileRecv{i}.bin", "rb")  # required binary file opened for reading
            newFile.write(file.read()) # content written into mp4 file
            file.close() # file closed
            os.remove(f"fileRecv{i}.bin") # original binary file(portion) deleted to avoid redundancies and errors


""" Cleanup fucntion
Functionailty: remove any existing binary file 
returns: Clean the directory ( Removes binary files)
"""
def cleanUp():  
    directory = './'  # current folder
    files_in_directory = os.listdir(directory) # list of all files in current folder taken
    filtered_files = [file for file in files_in_directory if file.endswith(".bin")] # files filtered out with '.bin' extension
    for file in filtered_files: # every found redundant binary file is deleted
        path_to_file = os.path.join(directory, file)
        os.remove(path_to_file)


def curses_thread():  # threading function to ensure continuous interval-based refreshing of metrics in background
    while not end:
        screen.addstr(len(ports), 0, f'Total downloaded: {totalDownloaded}/{mediaSize} bytes')
        screen.refresh()
        curses.napms(timeInterval*100)


####main client process####
# takes port number for server, instance number and required byte request string/header to be sent to server as parameters
def client_process(port_num, i,header):
    try:
        global totalDownloaded
        serverNum = ports.index(port_num)  # taking note of what overall server we are receiving information from in this process for metrics
        client_socket = socket(AF_INET, SOCK_STREAM)
        client_socket.connect((serverIP, port_num))
        message = header
        client_socket.send(message.encode()) # message is sent to server side
        start = int(header.split('-')[0].split('=')[1]) # information of start, end range from message extracted
        end = int(header.split('-')[1])
        # size calculated from sent message for byte range, added to amount of bytes to be downloaded from that server
        size = end-start
        serverSize[serverNum] += size + 1
        speed = 0  # downloading speed initialized
        previous = 0 # value for storing data received in previous interval
        screen.addstr(serverNum,10,f'0/{serverSize[serverNum]} bytes, download speed = {speed} kb/s   ')  # request for updating metrics info
        recv_file = open(f"fileRecv{i}.bin", "ab")  # binary file to write segment into opened
        file_part = client_socket.recv(Buffer_size)  # data is read from server side through socket
        while file_part: # same process looped while information is received from server
            recv_file.write(file_part)  # received information written into file
            speed = round((len(file_part) - previous/1000),3)  # download speed calculated, rounded as 3 decimal places
            previous = len(file_part)
            downloadedSize[serverNum] += len(file_part)  # bytes read currently from server recorded as downloaded from server so far
            if speed < 0: # in event that speed is negative, it is assumed as 0
                speed = 0.000
            screen.addstr(serverNum, 10, f'{downloadedSize[serverNum]}/{serverSize[serverNum]} bytes, download speed = {speed} kb/s   ')
            totalDownloaded += len(file_part)  # bytes read currently from server added into total download count for overall media file
            file_part = client_socket.recv(Buffer_size)
        recv_file.close()  # if all required data is successfully received from server, files are closed and thread is closed
        client_socket.close()
    except (ConnectionRefusedError, ConnectionResetError):  # in event that connection to server is broken while connecting to or reading data from it
        screen.addstr(serverNum, 10, 'Dead!                                                                           ')
        time.sleep(1)
        screen.addstr(len(ports) + 1, 0, 'Finding servers...                                                          ')
        time.sleep(3) # delay introduced to compensate for any other further server failures/resumptions
        if resume: # in event that interrupted download is to be resumed
            offset = recv_file.tell()  # to record how many bytes of data were written into binary file before connection was broken
            duplicate = (start+offset) - start  # bytes that have been written into binary file in the context of the initial range request
            start = start + offset # to calculate start for new range request to be sent after division
            serverSize[serverNum] = duplicate  # information lost is removed from total received count
        else: # in event that whole segment has to be redownloaded, previous data discarded
            os.remove(f"fileRecv{i}.bin") # file segment deleted
            serverSize[serverNum] = 0  # total received count is reset
        recv_file.close()
        client_socket.close()
        while True: # continues until at least one server is found for recovery
            subLivePorts = checkPorts(ports)  # current live servers are checked that can be used to recover data
            subNumOfServers = len(subLivePorts)
            if subNumOfServers == 0: # in event that no live servers are found
                screen.addstr(len(ports) + 2, 0, 'Trying again...                  ')
                continue
            else: # if at least one server is found, loop breaks
                break
        screen.addstr(len(ports) + 1, 0, f'Found! Distributing remaining load between {subNumOfServers} server(s)')
        screen.addstr(len(ports) + 2, 0, '                                                                       ')
        subHeaders = formatHeaders(subNumOfServers,start,end)  # range requests for sub-fragments of fragment prepared for load balancing
        subThreads = [] # to keep track of sub-threads within current thread
        for j in range(0,subNumOfServers): # sub-threads created and added to sub-threads list for all found live servers
            subName = str(i) + '.' + str(j + 1)  # file name for sub-fragment to be combined with main fragment
            new = threading.Thread(target=client_process, args=(subLivePorts[j],subName,subHeaders[j]))
            subThreads.append(new)
            new.start()
        for y in subThreads:  # after all sub-threads are completed, sub-fragments are written back in order to main segment
            y.join()
        recv_file2 = open(f"fileRecv{i}.bin", "ab") # main fragment '.bin' file is opened
        recv_file2.seek(start)  # I/O pointer is sent to point where new information is to be written from
        for j in range(0,subNumOfServers): # all available sub-fragments for current instance are to be considered
            screen.addstr(len(ports) + 1, 0, 'Downloading and recombining fragments...                                               ')
            subName = str(i) + '.' + str(j + 1)  # file name for sub-fragment to be combined with main fragment
            subFile = open(f"fileRecv{subName}.bin", "rb") # sub-fragment file opened
            recv_file2.write(subFile.read()) # sub-fragment contents written into main fragment file
            subFile.close()  # sub-fragment file closed and deleted to avoid redundancies
        recv_file2.close()  # main fragment file closed


cleanUp()  # before executing program, any existing '.bin' fragments are deleted to avoid errors
screen = curses.initscr() # 'curses' library dymanic screen for metrics initialized
curses.curs_set(0) # blinking cursor disabled
screen.addstr(1, 0, f'Looking for available servers...') # request for updating info on screen entered into buffer queue
screen.refresh() # updates are only made to screen when screen is refreshed
while True:  # looped until at least one live server is found
    try:
        livePorts = checkPorts(ports) # checking for live servers/ports from initial port list
        numOfServers = len(livePorts) # number of live current servers displayed
        screen.addstr(2, 0, f'{numOfServers} server(s) available.                                                       ')
        screen.refresh()
        if len(livePorts) == 0: # if no live servers are found, loop is repeated
            curses.napms(750)  # slight time delay introduced for sake of efficient display of information
            screen.addstr(2, 23, f'Trying again...') # information displayed
            screen.refresh()
            continue
        else: # if at least one live server is found
            media_socket = socket(AF_INET, SOCK_STREAM)
            media_socket.connect((serverIP, livePorts[0])) # first available server is pinged for size of media file
            media_socket.send('size'.encode())
            mediaSize = media_socket.recv(4096).decode()
            mediaSize = int(mediaSize)
            media_socket.close()
            break
    except (ConnectionResetError,ConnectionRefusedError): # in event that connection with server is broken when retrieving size information
        continue

screen.clear() # screen is cleared
headers = formatHeaders(numOfServers,0,mediaSize) # byte request strings for initial load division prepared for each available server
for i in range(0,len(ports)): # server metric lines initialized
    screen.addstr(i, 0, f'Server {int(i)+1}:')
screen.addstr(len(ports),0,f'Total downloaded: {totalDownloaded}/{mediaSize} bytes')
cu = threading.Thread(target=curses_thread) # separate thread for metric screen refreshing started
cu.start()

for i in range(0,numOfServers): # threads for all available servers with appropriate byte requests started
    server_thread = threading.Thread(target=client_process, args=(livePorts[i], i,headers[i]))
    threads.append(server_thread)
    server_thread.start()

for x in threads:  # waiting for all threads to finish before file is recombined to avoid errors
    x.join()
screen.addstr(len(ports) + 1, 0, 'File recombination in process..')
end = True  # signaling metrics screen thread to exit
screen.refresh()
fileRecombining()  # fragments of file recombined into final mp4 file
curses.napms(3000)
curses.endwin()  # metrics window closed
cleanUp()  # ran after code has been run to ensure all binary fragments have been removed
input('The downloading process has finished. Please press Enter to exit..')


