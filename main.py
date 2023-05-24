from machine import Pin, I2C
from neopixel import NeoPixel
from mx1508 import *
from vl53l0x import *
from tcs34725 import *
from time import sleep_ms, sleep
import uasyncio as asio
import aioespnow
import network

#Датчик цвета
i2c_bus = I2C(0, sda=Pin(16), scl=Pin(17))
tcs = TCS34725(i2c_bus)
tcs.gain(4)#gain должен быть 1, 4, 16 или 60
tcs.integration_time(80)
#Дальномер
i2c_bus1 = I2C(1, sda = Pin(21), scl = Pin(22))
tof = VL53L0X(i2c_bus1)
#Светодиод
NUM_OF_LED = 2
Lt = 60
np = NeoPixel(Pin(13), NUM_OF_LED)
color=['Red', 'Yellow', 'White', 'Green', 'Black', 'Cyan', 'Blue', 'Magenta']
#Движение
dir_move = ['Stop', 'Forward', 'Left', 'Right', 'Reverse']
motor_L = MX1508(2, 4)
motor_R = MX1508(19, 18)
Sp = 1023
debug = 0
R_W_count, W_count, col_id, direct, di, dist, busy=0, 0, 0, 0, 0, 500, 0 
R_m_pin = Pin(32, Pin.IN)
L_m_pin = Pin(25, Pin.IN)

motor_R.forward(Sp)
motor_L.forward(Sp)

#WLAN интерфейс
network.WLAN(network.STA_IF).active(True)
e = aioespnow.AIOESPNow()  # Returns AIOESPNow enhanced with async support
e.active(True)
peer = b'\xC8\xF0\x9E\x52\x66\x0C' #C8F09E52660C
e.add_peer(peer)
peer = b'\xC8\xF0\x9E\x4E\x9C\xA8' #C8F09E4E9CA8
e.add_peer(peer)


def R_W_int(pin):
    global W_count, R_W_count
    W_count += 1
    R_W_count += 1
    
def L_W_int(pin):
    global W_count
    W_count -= 1
   
R_m_pin.irq(trigger = Pin.IRQ_FALLING | Pin.IRQ_RISING, handler = R_W_int)
L_m_pin.irq(trigger = Pin.IRQ_FALLING | Pin.IRQ_RISING, handler = L_W_int)

async def synch(int_ms):
    while 1:
        await asio.sleep_ms(int_ms)
        if direct == 0:
            if W_count > 0:
                motor_R.forward(0)
                motor_L.forward(Sp)
            elif W_count < 0:
                motor_R.forward(Sp)
                motor_L.forward(0)
            else:
                motor_R.forward(Sp)
                motor_L.forward(Sp)
        elif direct == 1:
            if W_count > 0:
                motor_R.forward(0)
                motor_L.reverse(Sp)
            elif W_count < 0:
                motor_R.forward(Sp)
                motor_L.reverse(0)
            else:
                motor_R.forward(Sp)
                motor_L.reverse(Sp)
        elif direct == 2:
            if W_count > 0:
                motor_R.reverse(0)
                motor_L.forward(Sp)
            elif W_count < 0:
                motor_R.reverse(Sp)
                motor_L.forward(0)
            else:
                motor_R.reverse(Sp)
                motor_L.forward(Sp)        
        elif direct == 3:
            if W_count > 0:
                motor_R.reverse(0)
                motor_L.reverse(Sp)
            elif W_count < 0:
                motor_R.reverse(Sp)
                motor_L.reverse(0)
            else:
                motor_R.reverse(Sp)
                motor_L.reverse(Sp)
        elif direct == -1:
            motor_R.reverse(0)
            motor_L.reverse(0)

async def W_sp(int_ms):
    global R_W_count, di, dist, direct, col_id
    while 1:
        await asio.sleep_ms(int_ms)
        await color_det()
        await dist_det()
        if 150 < dist < 250:
            if dist % 2:
                if not busy: direct = 1
            else:
                if not busy: direct = 2
            di = 1
            await move(8)
        elif dist < 150:
            if not busy: direct = 3
            di = 2
            await move(16)
        else:
            if not busy: direct = 0
            di = 0
        if col_id == 4:
            if not busy: direct = 2
            await move(16)
        if col_id == 5:
            if not busy: direct = -1
        else:
            motor_R.reverse(Sp)
            motor_L.forward(Sp)
            
async def move(turn):
    global R_W_count, busy
    busy = 1
    R_W_count = 0
    while R_W_count < turn:
        await asio.sleep_ms(0)
    busy = 0

async def color_det():
    global col_id
    rgb = tcs.read(1)
    r, g, b = rgb[0], rgb[1], rgb[2]
    h, s, v = rgb_to_hsv(r, g, b)
    if 0 < h < 60:
        col_id = 0
    elif 61 < h < 120:
        col_id = 1
    elif 121 < h < 180:
        if v > 100:
            col_id = 2
        elif 25 < v < 100:
            col_id = 3
        elif v < 25:
            col_id = 4
    elif 181 < h < 240:
        if v > 40:
            col_id = 5
        else:
            col_id = 6
    elif 241 < h < 360:
        col_id = 7       
            
async def dist_det():
    global dist
    tof.start()
    dist = tof.read()//2
    tof.stop()
            
async def LED_cont(int_ms):
    while 1:
        await asio.sleep_ms(int_ms)
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
        if di==0:
            np[1]=(0,Lt,0)
        elif di==1:
            np[1]=(Lt,Lt,0)
        elif di==2:
            np[1]=(Lt,0,0)
        np.write()
        
async def send(e, period):
    while 1:
        await e.asend(color[col_id]+' '+dir_move[1+direct]+' '+str(dist)) #
        await asio.sleep_ms(period)
        
#инициализируем цикл
loop = asio.get_event_loop()

#создаём задания
loop.create_task(synch(1))
loop.create_task(W_sp(100))
loop.create_task(LED_cont(100))
loop.create_task(send(e, 100))

#запускаем его навсегда
loop.run_forever()
    
