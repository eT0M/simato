#!/usr/bin/env python
"""
Simple Magnetic Card Reader/Writer Tool for Omron 3S4YR-MVFW1JD
(C) 2013 Th. Frisch
Licensed under the terms of the GNU GPLv3+
"""

import sys, os, serial, threading,  getopt

# Card Reader Control Symbols
DLE = 0x10  #Transparent Mode control code in text
STX = 0x02  #Start of Text
ETX = 0x03  #End of text
ENQ = 0x05  #Execution 
ACK = 0x06  #Positive Response
NAK = 0x15  #Negative Response
EOT = 0x04  #Interruption

EXITCHARCTER = '\x1d'   # GS/CTRL+]

import sys, os

class Cardreader(object):
    def __init__(self, port, baudrate, parity, rtscts, xonxoff, echo=False):
        try:
            self.serial = serial.serial_for_url(port, baudrate, parity=parity, rtscts=rtscts, xonxoff=xonxoff, timeout=1)
        except AttributeError:
            # happens when the installed pyserial is older than 2.5. use the
            # Serial class directly then.
            self.serial = serial.Serial(port, baudrate, parity=parity, rtscts=rtscts, xonxoff=xonxoff, timeout=1)
        self.echo = echo
        self.busy = 0
        self.dtr_state = True
        self.rts_state = True
        self.break_state = False
        self.in_cmd = 0
        self.buffer = ""
        self.readdata =""
        self.currentcommand = ""
        self.trackmemory=["<empty>",  "<empty>",  "<empty>"]
     
    def user_command(self,  command):
        self.in_cmd = 1
        self.send_command('C%s' %command)
    
    def clear_trackmemory(self):
        self.trackmemory=["<empty>",  "<empty>",  "<empty>"]
        
    def send_command(self,  command):
        buffer = chr(DLE) + chr(STX)
        pos = 0 
        bcc = 0
        for i in command:
            buffer+=command[pos]
            bcc^=ord(command[pos])
            if ord(command[pos]) == DLE:
                buffer+=command[pos]
            pos+=1
        buffer += chr(DLE) 
        buffer += chr(ETX)
        bcc ^= ETX
        buffer += chr(bcc)    
        # print map(ord,  buffer)   #Debug Output
        self.serial.write(buffer)
        self.serial.flush()   
        self.busy = 1

    def start(self):
        """Start reader thread"""
        self.alive = True
        # start serial->console thread
        self.receiver_thread = threading.Thread(target=self.reader)
        self.receiver_thread.setDaemon(True)
        self.receiver_thread.start()
   
    def stop(self):
        self.serial.close()
        self.alive = False

    def join(self):
        self.receiver_thread.join()
    
    def process_incomming(self,  rxpos):
        self.pos = 2
        self.cmd = [0, 0]
        self.readdata =""
        if self.buffer[self.pos] == 'P':
             sys.stderr.write("positive response received\n")
             self.pos=self.pos+1
             self.cmd[0] = self.buffer[self.pos]
             self.pos=self.pos+1
             self.cmd[1] = self.buffer[self.pos]
             self.pos=self.pos+1
             sys.stderr.write("command was %s%s\n" %(self.buffer[self.pos-2] , self.buffer[self.pos-1]))
             self.currentcommand = self.buffer[self.pos-2] + self.buffer[self.pos-1]
             if self.buffer[self.pos]=='0' and self.buffer[self.pos+1] == '0':
                sys.stdout.write("no card present\n")
             elif self.buffer[self.pos]=='0' and self.buffer[self.pos+1] == '1':
                sys.stdout.write("card at takeout\n")
             elif self.buffer[self.pos]=='0' and self.buffer[self.pos+1] == '2':
                sys.stdout.write("card present\n")
             else:
                sys.stdout.write("status is %s%s\n" %(self.buffer[self.pos] , self.buffer[self.pos+1]))
        
         
        elif self.buffer[self.pos] == 'N':
             sys.stderr.write("negative response received\n")
             self.pos=self.pos+1
             sys.stderr.write("command was %s%s" %(self.buffer[self.pos-2] , self.buffer[self.pos-1]))
             
             self.pos += 2
             if self.buffer[self.pos]=='0' and self.buffer[self.pos+1] == '0':
                sys.stderr.write("undefined command\n")
             elif self.buffer[self.pos]=='0' and self.buffer[self.pos+1] == '1':
                sys.stderr.write("command sequence error\n")
             elif self.buffer[self.pos]=='0' and self.buffer[self.pos+1] == '2':
                sys.stderr.write("command data error\n")
             elif self.buffer[self.pos]=='0' and self.buffer[self.pos+1] == '3':
                sys.stderr.write("write track setting error\n")
             elif self.buffer[self.pos]=='4' and self.buffer[self.pos+1] == '0':
                sys.stderr.write("SS read error\n")
             elif self.buffer[self.pos]=='4' and self.buffer[self.pos+1] == '1':
                sys.stderr.write("ES read error\n")
             elif self.buffer[self.pos]=='4' and self.buffer[self.pos+1] == '2':
                sys.stderr.write("VRC read error\n")
             elif self.buffer[self.pos]=='4' and self.buffer[self.pos+1] == '3':
                sys.stderr.write("LRC read error\n")
             elif self.buffer[self.pos]=='4' and self.buffer[self.pos+1] == '4':
                sys.stderr.write("No encode read error\n")
             elif self.buffer[self.pos]=='4' and self.buffer[self.pos+1] == '5':
                sys.stderr.write("No data read error\n")
             elif self.buffer[self.pos]=='4' and self.buffer[self.pos+1] == '6':
                sys.stderr.write("Jitter read error\n")
             else:
                sys.stdout.write("unknown status %s%s\n" %(self.buffer[self.pos] , self.buffer[self.pos+1]))
            
        self.pos += 2
        if  self.pos < rxpos-3:
            if self.cmd[0] == '6' and self.cmd[1] == 'A':
                sys.stdout.write("No support for reception of multitrack for now...")
            else:
                while self.pos < rxpos-3:
                     self.readdata += self.buffer[self.pos] 
                     self.pos+=1  
                if self.currentcommand == "61":
                    self.trackmemory[0] = self.readdata
                elif self.currentcommand == "62":
                    self.trackmemory[1] = self.readdata
                elif self.currentcommand == "63":
                    self.trackmemory[2] = self.readdata
        self.busy = 0
        
    
    def reader(self):
        try:
            while self.alive:
                data = self.serial.read(1)
                self.buffer += data
                rxlen = len(self.buffer) 
                if (rxlen== 2 and self.buffer[0] == chr(DLE) and self.buffer[1] == chr(ACK) and self.in_cmd == 1):
                    print"received ACK"
                    self.serial.write(chr(DLE))
                    self.serial.write(chr(ENQ))
                    self.in_cmd = 0
                    self.buffer=""
                if (rxlen > 2 and self.buffer[rxlen-3] == chr(DLE) and self.buffer[rxlen-2] == chr(ETX)):
                    self.process_incomming(rxlen)
                    self.in_cmd = 0
                    self.buffer=""
                #if len(data) == 1:                               #Debug Output
                    # sys.stdout.write(str(ord(data)))    #Debug Output
                    # sys.stdout.write("\n")                    #Debug Output
                sys.stdout.flush()
        except serial.SerialException, e:
            self.alive = False
            raise

   

def main(argv):
    
    port = "/dev/ttyUSB0"
    baudrate = 9600
    parity = "N"
    rtscts = False
    xonxoff = True
    echo = False
    session = 1
    debug = 0
    
    try:
      opts, args = getopt.getopt(argv,"hp:", ["port="])
    except getopt.GetoptError:
      print 'simato.py -p <serial port>'
      sys.exit(2)
    for opt, arg in opts:
      if opt == '-h':
         print 'simato.py -p <serial port>'
         sys.exit()
      elif opt in ("-p"):
         port = arg
          
    try:
        cardreader = Cardreader(
            port,
            baudrate,
            parity,
            rtscts,
            xonxoff,
            echo,
        )
    except serial.SerialException, e:
        sys.stderr.write("could not open port %r: %s\n" % (port, e))
        sys.exit(1)


    sys.stderr.write('--- cardreader on %s: %d,%s,%s,%s ---\n' % (
        cardreader.serial.portstr,
        cardreader.serial.baudrate,
        cardreader.serial.bytesize,
        cardreader.serial.parity,
        cardreader.serial.stopbits,
    ))   

    cardreader.start()
    
    print"Simple Magnetic Card Reader/Writer Tool for Omron 3S4YR-MVFW1JD"
    print "Author: Thomas Frisch 2013 <dev@e-tom.de>"
    
    print"Menu:"
    print "1. Reset Reader"
    print "2. Insert permit request (checks for right orientation of mag. stripe)"
    print "3. Eject Card"
    print "4. Read Card"
    print "5. Write Card from command line input"
    print "6. Write Card from track memory"
    print "7. Raw Command"
    print "8. Show Track Memorys"
    print "9. Read all tracks to track memory"
    print "0. Exit"
    print ""
    
    while session == 1:
        n = raw_input("Command: ")
        if n=="0":
            session = 0
            cardreader.stop()
        elif n=="1":
            cardreader.user_command("00")
            while (cardreader.busy):
                    pass
        elif n=="2":
            cardreader.user_command(":2")
            while (cardreader.busy):
                    pass
            sys.stdout.write("Insert Card...\n")
        elif n=="3":
            cardreader.user_command("30")
            while (cardreader.busy):
                    pass
        elif n=="4":
            sys.stdout.write("Reads data to Track-Memory x")
            n = raw_input("Track Nr. (1-3): ")
            if n in ("1",  "2",  "3"):
                cardreader.user_command("6"+ n)  
                while (cardreader.busy):
                    pass
                sys.stdout.write("Stored data in Trackmemory %s:\n" %n)
                for c in cardreader.trackmemory[int(n)-1]:
                    if (ord(c) > 31 and ord(c) < 128):
                        sys.stdout.write("%s" %c)
                    else:
                        sys.stdout.write("<%d>" %ord(c))
                sys.stdout.write("\n")                                      
            else:
                sys.stderr.write("invalid command")
        elif n=="5":
            sys.stdout.write("")
            n = raw_input("Track Nr. (1-3, only Track 1 supports alphanumeric characters): ")
            if n in ("1",  "2",  "3"):
                data = raw_input("Data: ")
                cardreader.user_command("7"+ n +data)
            else: 
                sys.stderr.write("invalid command")
            while (cardreader.busy):
                    pass
        elif n=="6":
            sys.stdout.write("Write track memory to card")
            n = raw_input("Track Nr. (1-3): ")
            if n in ("1",  "2",  "3"):
                if cardreader.trackmemory[int(n)-1] == "<empty>":
                    sys.stderr.write("Selected memory is empty")
                else:
                    cardreader.user_command("7"+ n +cardreader.trackmemory[int(n)-1])
            else: 
                sys.stderr.write("invalid command")
            while (cardreader.busy):
                    pass 
        elif n=="7":
            n = raw_input("Raw Command: ")
            cardreader.user_command(n)
        
        elif n=="8":
            for i in [1,  2,  3]:           
                sys.stdout.write("Track %d Data:\n" %i)
                for c in cardreader.trackmemory[i-1]:
                        if (ord(c) > 31 and ord(c) < 128):
                            sys.stdout.write("%s" %c)
                        else:
                            sys.stdout.write("<%d>" %ord(c))
                sys.stdout.write("\n") 
            
        elif n=="9":
            sys.stdout.write("Reads all tracks to track memory\n")
            cardreader.clear_trackmemory()
            for i in [1,  2,  3]:  
                sys.stdout.write("Reading Track %d: ...\n " %i)
                cardreader.user_command("6"+ str(i))                  
                while (cardreader.busy):
                    pass                
            for i in [1,  2,  3]:     
                sys.stdout.write("Stored data for Track %d: " %i)
                for c in cardreader.trackmemory[i-1]:
                    if (ord(c) > 31 and ord(c) < 128):
                        sys.stdout.write("%s" %c)
                    else:
                        sys.stdout.write("<%d>" %ord(c))
                sys.stdout.write("\n")
                if cardreader.trackmemory[i-1] == "<empty>":
                    sys.stderr.write("Track %d is empty or not readable\n" %i)         
            sys.stdout.write("done\n")
        else:
            print"Menu:"
            print "1. Reset Reader"
            print "2. Insert permit request (checks for right orientation of mag. stripe)"
            print "3. Eject Card"
            print "4. Read Card"
            print "5. Write Card from command line input"
            print "6. Write Card from track memory"
            print "7. Raw Command"
            print "8. Show Track Memorys"
            print "9. Read all tracks to track memory"
            print "0. Exit"
            print ""
            
    
                
    try:
        cardreader.join()
    except KeyboardInterrupt:
        pass
    sys.stderr.write("\n--- exit ---\n")
    cardreader.join()
    
if __name__ == '__main__':
    main(sys.argv[1:])
