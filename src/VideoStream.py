from ast import Constant

class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        self.openFile()

    def openFile(self):
        try:
            self.file = open(self.filename, 'rb')
        except:
            raise IOError
        self.frameNum = 0

    def nextFrame(self):
        """Get next frame."""
        data = self.file.read(5)  # Get the framelength from the first 5 bits
        if data:
            framelength = int(data)
            # Read the current frame
            data = self.file.read(framelength)
            self.frameNum += 1
        return data

    def next10Frame(self):

        for i in range(9):
            self.nextFrame()
        return self.nextFrame()

    def back10Frame(self):
        length = self.frameNum - 10
        
        if length < 0: 
            length = 0
            
        self.file.close()
        self.openFile()

        for i in range(length-2):
            self.nextFrame()

        return self.nextFrame()
    
    def frameNbr(self):
        """Get frame number."""
        return self.frameNum
