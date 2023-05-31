from machine import Pin, I2C
import uasyncio as asio
from neopixel import NeoPixel
from mx1508 import *
from vl53l0x import *
from tcs34725 import *
from time import sleep_ms, sleep
import aioespnow
import network

#Датчик цвета
i2c_bus = I2C(0, sda=Pin(16), scl=Pin(17))
tcs = TCS34725(i2c_bus)
tcs.gain(4)
tcs.integration_time(80)
#Дальномер
i2c_bus1 = I2C(1, sda = Pin(21), scl = Pin(22))
tof = VL53L0X(i2c_bus1)
dist = 500
#Светодиод
NUM_OF_LED = 1
Lt = 60
np = NeoPixel(Pin(14), NUM_OF_LED)
color = ['Red', 'Yellow', 'White', 'Green', 'Black', 'Cyan', 'Blue', 'Magenta']
col_id = 2
#Движение
dir_move = ['Stop', 'Forward', 'Left', 'Right', 'Reverse']
motor_L = MX1508(2, 4)
motor_R = MX1508(19, 18)
Sp = 1000
motor_R.reverse(Sp)
motor_L.forward(Sp)

network.WLAN(network.STA_IF).active(True)
e = aioespnow.AIOESPNow()  # Returns AIOESPNow enhanced with async support
e.active(True)
peer = b'\xC8\xF0\x9E\x52\x66\x0C' #C8F09E52660C
#'\\x'+mac[0:2]+'\\x'+mac[2:4]+'\\x'+mac[4:6]+'\\x'+mac[6:8]+'\\x'+mac[8:10]+'\\x'+mac[10:12]
e.add_peer(peer)
peer = b'\xC8\xF0\x9E\x4E\x9C\xA8' #C8F09E4E9CA8
e.add_peer(peer)
peer = b'\xCC\xDB\xA7\x56\x9C\x0C' #CCDBA7569C0C
e.add_peer(peer)

async def LED_cont():
    global col_id, Lt
    while 1:
        await asio.sleep_ms(100)
        if col_id==0:
            np[0]=(Lt,0,0)
        elif col_id==1:
            np[0]=(Lt,Lt,0)
        elif col_id==2:
            np[0]=(Lt,Lt,Lt)
        elif col_id==3:
            np[0]=(0,Lt,0)
        elif col_id==4:
            np[0]=(0,0,0)
            np.write()
            await asio.sleep_ms(300)
            np[0]=(Lt,0,0)
            np.write()
            await asio.sleep_ms(300)
        elif col_id==5:
            np[0]=(0,Lt,Lt)
        elif col_id==6:
            np[0]=(0,0,Lt) 
        elif col_id==7:
            np[0]=(Lt,0,Lt)
        np.write()

async def rotate(grad):
    go = 1500
    motor_R.forward(Sp)
    motor_L.reverse(Sp)

    sleep_ms(go)

    motor_R.reverse(Sp)
    motor_L.reverse(Sp)
    
    sleep_ms(10*grad)
        
    motor_R.reverse(Sp)
    motor_L.forward(Sp)

async def move():
    global dist, col_id
    while 1:
        await asio.sleep_ms(100)
        await color_det()
        await dist_det()
        if dist < 150:
            await rotate(83)
        elif col_id == 4:
            await rotate(135)
        elif (col_id != 4)and(col_id != 2):
            motor_R.reverse(Sp//2)
            motor_L.forward(Sp//2)
            await asio.sleep_ms(1000)
            motor_R.reverse(Sp)
            motor_L.forward(Sp)
        else:
            motor_R.reverse(Sp)
            motor_L.forward(Sp)

async def dist_det():
    global dist
    tof.start()
    dist = tof.read()
    tof.stop()
    
async def color_det():
    global col_id
    rgb = tcs.read(1)
    r, g, b = rgb[0], rgb[1], rgb[2]
    h, s, v = rgb_to_hsv(r, g, b)
    if (r > 500)and(g > 500)and(b > 500):
        col_id = 2
    elif (r < 60)and(g < 60)and(b < 60):
        col_id = 4
    elif (r > g)and(r > b):
        col_id = 0
    elif (g > r)and(g > b)and(g - r < g - b):
        col_id = 1
    elif (g > r)and(g > b)and(g - r > g - b):
        col_id = 3
    elif (b > r)and(g < b)and(g - r < b - g):
        col_id = 7
    elif (b > r)and(g < b)and(g - r > b - g):
        col_id = 6
        
async def send(e, period):
    while 1:
        await asio.sleep_ms(period)
        if busy_col:
            await e.asend(str(col_id))
            
        
async def resive(e,int_ms):
    global col_sel_r
    while 1:
        async for mac, msg in e:
            col_sel_r = int.from_bytes(msg,'big')-48
            await asio.sleep_ms(int_ms)
        
loop = asio.get_event_loop()

loop.create_task(move())
loop.create_task(LED_cont())
loop.create_task(send(e,100))
loop.create_task(resive(e,100))

loop.run_forever()
