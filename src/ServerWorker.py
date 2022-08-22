from random import randint
import sys
import traceback
import threading
import socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket


class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    FASTFORWARD = 'FASTFORWARD'
    BACKFORWARD = 'BACKFORWARD'
    DESCRIBE = 'DESCRIBE'

    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    fastFlag = False
    backFlag = False
    clientInfo = {}

    def __init__(self, clientInfo):
        self.clientInfo = clientInfo

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:
            data = connSocket.recv(256)
            if data:
                print("Data received:\n" + data.decode("utf-8") + '\n')
                self.processRtspRequest(data.decode("utf-8"))

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        # Get the request type
        request = data.split('\n')
        line1 = request[0].split(' ')
        requestType = line1[0]

        # Get the media file name
        filename = line1[1]

        # Get the RTSP sequence number
        seq = request[1].split(' ')

        # Process SETUP request
        if requestType == self.SETUP:
            if self.state == self.INIT:
                print("processing SETUP\n")
                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                except IOError:
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])

                # Generate a randomized RTSP session ID
                self.clientInfo['session'] = randint(100000, 999999)
                self.clientInfo['videoName'] = filename
                # Send RTSP reply
                self.replyRtsp(self.OK_200, seq[1])

                # Get the RTP/UDP port from the last line
                self.clientInfo['rtpPort'] = request[2].split(' ')[3]

        # Process PLAY request
        elif (requestType == self.PLAY) or (requestType == self.FASTFORWARD) or (requestType == self.BACKFORWARD):
            if self.state == self.READY:
                if requestType == self.PLAY:
                    print("processing PLAY\n")
                elif requestType == self.FASTFORWARD:
                    print("processing FASTFORWARD\n")
                    self.fastFlag = True
                else:
                    print("processing BACKFORWARD\n")
                    self.backFlag = True

                self.state = self.PLAYING

                # Create a new socket for RTP/UDP
                self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                self.replyRtsp(self.OK_200, seq[1])

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
                self.clientInfo['worker'].start()

        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY

                self.clientInfo['event'].set()

                self.replyRtsp(self.OK_200, seq[1])

        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")

            if (self.state != self.INIT):
                self.clientInfo['event'].set()
                self.clientInfo['rtpSocket'].close()
			
            self.replyRtsp(self.OK_200, seq[1])
        
        # elif (requestType == self.FASTFORWARD) or (requestType == self.BACKFORWARD):
        #     if self.state == self.READY:

        #         if requestType == self.FASTFORWARD:
        #             print("processing FASTFORWARD\n")
        #             self.fastFlag = True
        #         else:
        #             print("processing BACKFORWARD\n")
        #             self.backFlag = True

        #         self.state = self.PLAYING

        #         # Create a new socket for RTP/UDP
        #         self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #         # self.clientInfo['event'].set()
        #         self.replyRtsp(self.OK_200, seq[1])

        #         # Create a new thread and start sending RTP packets
        #         self.clientInfo['event'] = threading.Event()
        #         self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
        #         self.clientInfo['worker'].start() 
        #     else:
        #         print("not run:::::::))))\n")
            
        elif requestType == self.DESCRIBE:
            print("processing DESCRIBE\n")
            
            # reply = "\nFile name: %s\nProtocol: %s\nSession: %s\n" %("movie.Mjpeg", "RTSP/RTP 1.0", str(self.clientInfo['session']))
            mes2 = '\n\nm = video ' + str(self.clientInfo['rtpPort']) + ' RTP/AVP 26' \
                    + '\na = rtpmap: 26 JPEG / 90000' \

            mes1 = '\nContent-Base: ' + str(self.clientInfo['videoName']) \
                + '\nContent-Type: ' + 'application/sdp' \
                + '\nContent-Length: ' + str(len(mes2))

            reply = mes1+mes2
            self.replyRtsp(self.OK_200, seq[1])
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())

    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = bytes()

            if self.fastFlag == True:
                data = self.clientInfo['videoStream'].next10Frame()
                self.fastFlag = False

            elif self.backFlag == True:
                data = self.clientInfo['videoStream'].back10Frame()
                self.backFlag = False
            else:
                data = self.clientInfo['videoStream'].nextFrame()
            
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber), (address, port))
                    print('Sent frame number ' + str(frameNumber))
                except Exception as e:
                    print(e)
                    break

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()

        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)

        return rtpPacket.getPacket()

    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())

        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
