from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket
import threading
import sys
import traceback
import os
import time

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    FASTFORWARD = 4
    BACKFORWARD = 5
    DESCRIBE = 6

    requestStr = ["SETUP", "PLAY", "PAUSE", "TEARDOWN", "FASTFORWARD", "BACKFORWARD", "DESCRIBE"]
    acceptState = [INIT, READY, PLAYING, PLAYING, PLAYING, PLAYING, READY]

    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)
        self.createWidgets()
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        self.setupMovie()
        self.countFrame = 0
        self.sizeData = 0
        self.totalTime = 0
        self.timeStamp = 0

    # THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI
    def createWidgets(self):
        """Build GUI."""
        # Create Setup button
        self.setup = Button(self.master, width=15, padx=3, pady=3)
        self.setup["text"] = "DESCRIBE"
        self.setup["command"] = self.describe
        self.setup.grid(row=1, column=2, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.master, width=15, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=0, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=15, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=1, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=15, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        # Create FastForward button
        self.fastForward = Button(self.master, width=15, padx=3, pady=3)
        self.fastForward["text"] = "Fast Forward"
        self.fastForward["command"] = self.fastAction
        self.fastForward.grid(row=2, column=2, padx=2, pady=2)

        # Create BackForward button
        self.backForward = Button(self.master, width=15, padx=3, pady=3)
        self.backForward["text"] = "Back Forward"
        self.backForward["command"] = self.backAction
        self.backForward.grid(row=2, column=1, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4,
                        sticky=W+E+N+S, padx=5, pady=5)

        # create a label to display lost data
        self.lostRate = Label(self.master, text="Lost rate: ")
        self.lostRate.grid(row=3, column=0, columnspan=2, padx=10, pady=2, sticky=W)
        self.videoDataRate = Label(self.master, text="Video data rate: ")
        self.videoDataRate.grid(row=4, column=0, columnspan=2, padx=10, pady=2, sticky=W)

        # Create a label to display video total time
        self.labelTotalTime = Label(self.master, text='Total Time: ')
        self.labelTotalTime.grid(row=5, column=0, padx=1, pady=1)

        # Create a label to display video remaining time
        # self.remainTime = Label(self.master, text='Remaining time: ')
        # self.remainTime.grid(row=6, column=0, padx=1, pady=1)

    def threadListenRtp(self):
        threading.Thread(target=self.listenRtp).start()
        self.playEvent = threading.Event()
        self.playEvent.clear()

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy() # Close the gui window
        # filename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        # if (os.path.exists(filename)):
        #     os.remove(filename) # Delete the cache image from video
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """Play button handler."""
        if self.state == self.READY:
            # self.threadListenRtp()
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)
    
    def describe(self):
        if self.state == self.PLAYING:
            self.pauseMovie()
        self.sendRtspRequest(self.DESCRIBE)

    def fastAction(self):
        if not self.state == self.INIT:
            self.sendRtspRequest(self.PAUSE)
            # self.threadListenRtp()
            self.sendRtspRequest(self.FASTFORWARD)
            self.countFrame = self.countFrame + 9

    def backAction(self):
        if not self.state == self.INIT:
            self.sendRtspRequest(self.PAUSE)
            # self.threadListenRtp()
            self.sendRtspRequest(self.BACKFORWARD)
            if (self.frameNbr - 10 > 0) :
                self.frameNbr = self.frameNbr - 10
                self.countFrame = self.countFrame - 11
            else:
                self.frameNbr = 0
                self.countFrame = 0

    def listenRtp(self):
        """Listen for RTP packets."""
        # print('Start receiving RTP packet\n')
        self.timeStamp = time.time()
        while True:
            try:
                print("listening")
                currentTime = time.time()
                self.totalTime += currentTime - self.timeStamp
                self.timeStamp = currentTime
                videoDataRate = self.sizeData * 1.0 / self.totalTime
                
                
                data = self.rtpSocket.recv(20480)
                self.sizeData += sys.getsizeof(data)
                # print("size of new data " + str(sys.getsizeof(data)))
                # print("video data transmit rate: " + str(self.sizeData * 1.0 / self.totalTime))
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    # lost, rate data
                    currFrameNbr = rtpPacket.seqNum()

                    print ("Current Seq Num: " + str(currFrameNbr))
                    print ("Current Count Num: " + str(self.countFrame))
                    self.countFrame += 1
                    lossRate = (currFrameNbr - self.countFrame) * 1.0 / currFrameNbr
                    print(lossRate)

                    if currFrameNbr > self.frameNbr: # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()), 
                                                            lossRate, 
                                                            videoDataRate, 
                                                            self.totalTime,
                                                        )
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        filename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(filename, "wb")
        file.write(data)
        file.close()
        return filename

    def updateMovie(self, imageFile, lossRate, videoDataRate, totalTime):
        """Update the image file as video frame in the GUI."""
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image = photo, height=288)
        self.label.image = photo

        self.lostRate['text'] = "Lost rate:      {:8.3f}".format(lossRate)
        self.videoDataRate['text'] = "Video data rate:      {:8.3f} bytes/s".format(videoDataRate * 1.0)
        self.labelTotalTime['text'] = "Total Time:      {:8.3f} s".format(totalTime)
        # self.remainTime['text'] = "Remaining Time:      {:8.3f} s".format(remainTime)

    def connectToServer(self):
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        """Connect to the Server. Start a new RTSP/TCP session."""
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print('Connected to server\n')
        except:
            print('Cannot connect to server\n')

    def sendRtspRequest(self, requestCode):  #requestCode is a number
        """Send RTSP request to the server."""
        # -------------
        # TO COMPLETE
        # -------------

        line1 = "%s %s %s\n" % (self.requestStr[requestCode], self.fileName, "RTSP/1.0")
        line2_seq = "CSeq: %d\n" % (self.rtspSeq + 1)
        # line3 for play, pause, teardown. If requestCode is setup, we need to replace
        line3_lastLine = "Session: %d" %self.sessionId
        
        if requestCode == self.SETUP and self.state == self.INIT:
            self.requestSent = self.SETUP
            line3_lastLine = "Transport: RTP/UDP; client_port= %d\n" %self.rtpPort
            threading.Thread(target=self.recvRtspReply).start()

        if (requestCode == self.FASTFORWARD or requestCode == self.BACKFORWARD) and (self.state == self.READY) :
            self.state = self.PLAYING

        if requestCode == self.TEARDOWN:
            if self.state == self.INIT:
                return
        elif self.acceptState[requestCode] != self.state:
            return

        self.rtspSeq += 1
        self.requestSent = requestCode
        request = line1 + line2_seq + line3_lastLine
        print(request)
        self.rtspSocket.send(bytes(request, 'utf-8'))

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            data = self.rtspSocket.recv(1024)
            if data:
                self.parseRtspReply(data.decode('utf-8'))

            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
        if self.requestSent == self.DESCRIBE:
            print(data)
            return

        reply = data.split('\n')
        seq = int(reply[1].split(' ')[1])

        if seq == self.rtspSeq:
            session = int(reply[2].split(' ')[1])

            if self.sessionId == 0:
                self.sessionId = session

            if self.sessionId == session:
                if self.requestSent == self.SETUP:
                    self.state = self.READY
                    self.openRtpPort()

                elif self.requestSent == self.PLAY:
                    self.state = self.PLAYING

                elif self.requestSent == self.PAUSE:
                    self.playEvent.set()
                    self.state = self.READY

                elif self.requestSent == self.TEARDOWN:
                    self.state = self.INIT
                    self.teardownAcked = 1

                elif self.requestSent == self.BACKFORWARD or self.requestSent == self.FASTFORWARD:
                    self.state = self.PLAYING

                print('\n' + data + '\n')

            else:
                print('Unmatch SessionID')

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        # -------------
        # TO COMPLETE
        # -------------
        # Create a new datagram socket to receive RTP packets from the server
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)
        
        try:
        # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind(('',self.rtpPort))
        except:
            tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)
   
    def handler(self):
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else: # When the user presses cancel, resume playing.
            self.playMovie()
