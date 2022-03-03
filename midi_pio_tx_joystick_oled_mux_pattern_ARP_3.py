#74HC4067 multiplexer demonstration (16 to 1)
#
#20210224: plan for converting this to micropython
#Setup four digital pins as output: S0-S3.
#Setup one analog pin as input: A1
# 
#
#control pins output table in array form
#see truth table on page 2 of TI 74HC4067 data sheet
#connect 74HC4067 S0~S3 to Arduino D7~D4 respectively
#connect 74HC4067 pin 1 to Arduino A0

#20210405: clean up code. 
# Use joystick to set value and keep it when you stop pushing.
# Reset by clicking joystick.
# Visualize incoming notes and corrections.

#20210413: clean up code. 
# Use joystick to set value and keep it when you stop pushing. Need to scale joystick input! Print muxValues[0]!!!
# Reset by clicking joystick.
# Visualize incoming notes and corrections. Done!

#20210418: replace right joystick (tempo) with linear pots: tempo,...
# left joystick still controls pitch change x-axis and click for arp pattern. y-axis???

#20210421: pot to control arp pattern; muxValues[3]. DONE!

#20210427: draw the complete ARP pattern; indicate position with cursor. Done?

#20210429: create edit mode where ARP patterns can be edited (notes on or off). Default all on. How to enter edit mode? Add one pushbutton? Use joy to set or clear.
#20210511: create "mask" where to enter which steps should be shown and played. Same size as y_values_collection (make copy using [:] and change all values to 1). Started!

#20210609: send notes on all channels on Waves of Fear.


#import machine
from machine import Pin, I2C
import time
from ssd1306 import SSD1306_I2C
import ustruct
from machine import Pin, ADC
import framebuf
import copy
#import utime

# Example using PIO to create a UART TX interface
from rp2 import PIO, StateMachine, asm_pio

#Setup PIO

UART_BAUD = 31250
PIN_BASE = 10
NUM_UARTS = 1

@asm_pio(sideset_init=PIO.OUT_HIGH, out_init=PIO.OUT_HIGH, out_shiftdir=PIO.SHIFT_RIGHT)
def uart_tx():
    # Block with TX deasserted until data available
    pull()
    # Initialise bit counter, assert start bit for 8 cycles
    set(x, 7)  .side(0)       [7]
    # Shift out 8 data bits, 8 execution cycles per bit
    label("bitloop")
    out(pins, 1)              [6]
    jmp(x_dec, "bitloop")
    # Assert stop bit for 8 cycles total (incl 1 for pull())
    nop()      .side(1)       [6]

# Now we add 1 UART TXs, on pins 10 (#to 17#). ##Use the same baud rate for all of them.
uarts = []
for i in range(NUM_UARTS):
    sm = StateMachine(
        i, uart_tx, freq=8 * UART_BAUD, sideset_base=Pin(PIN_BASE + i), out_base=Pin(PIN_BASE + i)
    )
    sm.active(1)
    uarts.append(sm)
#print (uarts)
# We can print characters from each UART by pushing them to the TX FIFO
def pio_uart_print(sm, s):
    sm.put(s)

#Setup 74HC4067 (MUX)

S0_PIN = Pin(12, Pin.OUT, Pin.PULL_DOWN)
S1_PIN = Pin(13, Pin.OUT, Pin.PULL_DOWN)
S2_PIN = Pin(14, Pin.OUT, Pin.PULL_DOWN)
S3_PIN = Pin(15, Pin.OUT, Pin.PULL_DOWN)
analog_in_pin = machine.ADC(28)

#truth table from the TI 74HC4067 datasheet
S0 = [0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1]
S1 = [0,0,1,1,0,0,1,1,0,0,1,1,0,0,1,1]
S2 = [0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1]
S3 = [0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1]

#holds incoming values from 74HC4067                  
muxValues = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

def read_mux():
    #read bitsetting from S0 to S3 and set which mux pin to read (0-15). Store analog values in the muxValues list.
    for index,(bitS0,bitS1,bitS2,bitS3) in enumerate(zip(S0,S1,S2,S3)):
        S0_PIN.value(bitS0)
        S1_PIN.value(bitS1)
        S2_PIN.value(bitS2)
        S3_PIN.value(bitS3)
        muxValues[index] = analog_in_pin.read_u16()
    return

#get default value for left joystick x axis muxValues[0]
read_mux()
joyLeftX_default = muxValues[0]/8000  #do not touch joystick during startup!!!

#Setup oled
WIDTH_1  = 128                                           # oled display width
HEIGHT_1 = 64                                            # oled display height
buffer=[]

i2c = I2C(1)                                            # Init I2C using I2C1 defaults, SCL=Pin(GP9), SDA=Pin(GP8), freq=400000
oled1 = SSD1306_I2C(WIDTH_1, HEIGHT_1,  i2c, addr=0x3C)      # Init oled_1 display.

# Raspberry Pi logo as 32x32 bytearray
buffer = bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00|?\x00\x01\x86@\x80\x01\x01\x80\x80\x01\x11\x88\x80\x01\x05\xa0\x80\x00\x83\xc1\x00\x00C\xe3\x00\x00~\xfc\x00\x00L'\x00\x00\x9c\x11\x00\x00\xbf\xfd\x00\x00\xe1\x87\x00\x01\xc1\x83\x80\x02A\x82@\x02A\x82@\x02\xc1\xc2@\x02\xf6>\xc0\x01\xfc=\x80\x01\x18\x18\x80\x01\x88\x10\x80\x00\x8c!\x00\x00\x87\xf1\x00\x00\x7f\xf6\x00\x008\x1c\x00\x00\x0c \x00\x00\x03\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")

# Load the Raspberry Pi logo into the framebuffer (the image is 32x32)
fb = framebuf.FrameBuffer(buffer, 32, 32, framebuf.MONO_HLSB)

# Clear the oled display.
oled1.fill(0)
# Blit the image from the framebuffer to the oled display
oled1.blit(fb, 50, 0)

#add text
oled1.text("MicroPython",20,35)
oled1.text("MIDI on the PICO",0,45)

# Finally update the oled display so the image and texts are displayed
oled1.show()

#show image and texts for 2 sec.
time.sleep(2)

#time to show my very own MicroPython MIDI logo
logo = [] #this is where the logo is stored

with open("MicroPyMIDI_LOGO_inv_cut.pbm", "rb") as logo:
  f = logo.read()
  b = bytearray(f)

# Load the MicroPython MIDI logo into the framebuffer (the image is 128x64)
fb_midi = framebuf.FrameBuffer(b, 128, 64, framebuf.MONO_HLSB)

#clear the display
oled1.fill(0)

# Blit the image from the framebuffer to the oled display
oled1.blit(fb_midi, 0, 0)

# Update the oled display so the image is displayed. Wait 2 sec.
oled1.show()
time.sleep(2)


#Setup MIDI

#midi files present on the PICO
midiFileNames = ["midi_cut_0.mid", "midi_cut_1.mid", "midi_cut_2.mid", "midi_cut_3.mid", "midi_cut_4.mid", "midi_cut_5.mid", "midi_cut_6.mid"]
#print (len(midiFileNames))
#rows,cols = (len(midiFileNames),len(midiFileNames))
midi = [] #this is where the midi files are stored
midi_collection = []
#function for reading midi files and adding them to a list
def read_MIDI_file(filename):
    with open(filename, "rb") as f:
        byte = f.read(1)
        while byte:
            #append read bytes to the midi list.
            midi.append(byte)
            byte = f.read(1)
        midi_copy = midi[:] #make a copy of the currently read midi file
        midi_collection.append(midi_copy)
        del midi[:] #clear midi before next file is read
        print (midi)
        f.close()
        #print (midi_copy)
        #print(midi_collection[0])



#add midi files to list
for i in midiFileNames:
    read_MIDI_file(i)

#create list of lists to describe the seven ARP patterns. Graphic representation of ARPs.
#syntax example: oled1.hline(10,int(ord(midi_collection[ARP][i*9 + 1])/4)+10,20,1) #x,y,width,colour
#(i*9 + 1) contains the noteOn command.

y_values = []
y_values_collection = [] #store all y-axis values for translated notes from the ARPs. This will be used to draw the ARP graphic representation on the oled.

#step through the ARPS #for i in range(0,10,2):  print(i)
for i in range(0, len(midi_collection)): #iterate over number of rows
    for j in range(1, len(midi_collection[i]), 9): #iterate over length of row i.e. number of commands in the current ARP.
        y_values.append((midi_collection[i][j]))    #SCALE!!! Or perhaps later???  #create list with coordinates for ARP
    y_values_copy = y_values[:]
    y_values_collection.append(y_values_copy)
    del y_values[:]

print(y_values_collection)

y_values_mask = copy.deepcopy(y_values_collection)  #deep copy of list
#set all items in y_values_mask [i][j] to 1.
def SetMOD (MOD):
    for i in range(0, len(y_values_mask)): #iterate over number of rows
        for j in range(0, len(y_values_mask[i])): #iterate over length of row
            if j % MOD == 0: #set to 1 if even divisable with MOD (modulo). % 1 is always 0.
                y_values_mask[i][j] = 1
            else:
                y_values_mask[i][j] = 0

#print(y_values_mask)
#print(y_values_collection)

#Setup joystick switches i.e. when the joystick is pressed.
button_L = Pin(16,Pin.IN, Pin.PULL_UP)
buttonValue_L = 0
#button_R = Pin(17,Pin.IN, Pin.PULL_UP)
#buttonValue_R = 0


#Main loop.
# Print midi commands from the UART.
# Use left joystick x-axis for pitch change.
# Use first pot for tempo change.
# Use second pot for ARP selection. 
while True:
    read_mux()
    ARP = int(muxValues[3]/10000) #scale pot reading to get an integer from 0 to 6. muxValues[3] goes from 0 to 65536.
    MOD = int(muxValues[4]/10000 + 1) #scale pot reading to get an integer from 1 to 7. muxValues[4] goes from 0 to 65536.
    SetMOD(MOD) #calls function to set number of notes to be played (1 in y_values_mask)
    x_cursor = 2 #the whole ARP is played through so reset x_cursor to start value
    maskPosition = -1 #position in the mask, i.e. play or not play note.
    for u in uarts:
        for i in range(len(midi_collection[ARP])/9): #nine bytes read for each loop
            #print (i)
            maskPosition += 1
            read_mux()
            #print (muxValues[3])
            #print (midi[i*9])
            #Send noteOn if mask = 1. Send noteOff if mask = 0.
            pio_uart_print(u, midi_collection[ARP][i*9]) #is this noteOn? Yes!
            #    pio_uart_print(u, b'C') #noteOff ch 2. Byte? Hex?
            pio_uart_print(u, (ord(midi_collection[ARP][i*9 + 1]) - int(muxValues[0]/8000)).to_bytes(1,"big")) #change note value depending on muxValues[0] (left joystick x axis)
            if y_values_mask[ARP][maskPosition]:             #if 1 then play note.
                pio_uart_print(u, midi_collection[ARP][i*9 + 2])
                #print("hello")
            else:
                pio_uart_print(u, 0x00) # else set velocity to 0.
                print ("hello")
            #read 2 for delay. Only one used.[i*9+4]
            ##pio_uart_print(u, midi[i*9 + 3])
            ##pio_uart_print(u, midi[i*9 + 4])
            #print(ord(midi[i*9 + 4]))
            #time.sleep(0.1)
            time.sleep(((ord(midi_collection[ARP][i*9 + 4])/120)  - muxValues[2]/70000)) #use bpm pot i.e muxValues[2]
            #print(str((ord(midi[i*9 + 4]))/100) + "  " + str(66000 - muxValues[2]) + "  " + str((ord(midi[i*9 + 4])/100) + (ord(midi[i*9 + 4])/100) * ((66000 - muxValues[2])/(66000 + muxValues[2]))))
            #print(muxValues[2]/66000)
            #print(((ord(midi_collection[ARP][i*9 + 4])/120)  - muxValues[2]/70000)) #time.sleep from above
            #print (muxValues[3])
            #print 3
            pio_uart_print(u, midi_collection[ARP][i*9 + 5])
            pio_uart_print(u, midi_collection[ARP][i*9 + 6])
            pio_uart_print(u, midi_collection[ARP][i*9 + 7])
            #read 1 for delay
            ##pio_uart_print(u, midi[i*9 + 8])
            #print(ord(midi[i*9 + 8]))
            time.sleep(ord(midi_collection[ARP][i*9 + 8])/110)
            #print(ord(midi[i*9 + 8])/110)
            buttonValue_L += 1-button_L.value()  #pressing joystick sets button_L.value() to 0
            #buttonValue_R += 1-button_R.value()
            if (buttonValue_L == 4):
                buttonValue_L = 0
            #if (buttonValue_R == 3):
            #    buttonValue_R = 0
            oled1.fill(0) #needed? Slow? Currently erases x_cursor and the entire ARP pattern...
            oled1.text("Arp " + str(ARP),0,5)
            oled1.text("MOD " + str(MOD),0,5)
            oled1.text("BPM " + str(int(10*muxValues[2]/8000)),80,5) #20210419; fix tempo and bpm!


            #change y-value according to note value from muxValues[0]
            #Draw one line for original note value and one line for transposed note value.
            #Also draw the next three notes.

            #Draw ARP. x-values is +4 between lines, e.g first line starts at x = 2 then the next line starts at x = 6
            #Only draw ARP line if the mask value is 1 = On.
            #TO DO: only draw line when ARP is changed.
            x = 2   #startposition for first line
            for m, y in zip(y_values_mask[ARP], y_values_collection[ARP]):
                print (m, y)
                if m:                                          #draw line if m = 1.
                    oled1.hline(x, int((ord(y)/4)) + 20, 4, 1) #horizontal line: x,y,width,colour
                x += 4  #add 4 to get new startposition


            ###Need to add cursor. Also show how much joyLeftX changes the pitch of the note.
            ###Cursor drawn at bottom of screen.
            oled1.hline(x_cursor, 60 , 4, 1) #horizontal line: x,y,width,colour
            x_cursor += 4

            #oled1.hline(10,int(ord(midi_collection[ARP][i*9 + 1])/4) + 2*int(joyLeftX_default - muxValues[0]/8000)+10,20,1) #x,y,width,colour
            ##print (joyLeftX_default - muxValues[0]/8000) #20210418: log value; scale to linear.
            #oled1.hline(10,int(ord(midi_collection[ARP][i*9 + 1])/4)+10,20,1) #x,y,width,colour
            #if (i <= len(midi)/9): #was -29
            #    oled1.hline(30,int(ord(midi_collection[ARP][i*9 + 10])/4) + 2*int(joyLeftX_default - muxValues[0]/8000)+10,20,1) #x,y,width,colour
            #    oled1.hline(30,int(ord(midi_collection[ARP][i*9 + 10])/4)+10,20,1) #x,y,width,colour
            #    oled1.hline(50,int(ord(midi_collection[ARP][i*9 + 19])/4) + 2*int(joyLeftX_default - muxValues[0]/8000)+10,20,1) #x,y,width,colour
            #    oled1.hline(50,int(ord(midi_collection[ARP][i*9 + 19])/4)+10,20,1) #x,y,width,colour
            #    oled1.hline(70,int(ord(midi_collection[ARP][i*9 + 28])/4) + 2*int(joyLeftX_default - muxValues[0]/8000)+10,20,1) #x,y,width,colour
            #    oled1.hline(70,int(ord(midi_collection[ARP][i*9 + 28])/4)+10,20,1) #x,y,width,colour
            oled1.show()

