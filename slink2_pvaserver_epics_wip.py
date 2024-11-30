import serial
import time
import signal
from multiprocessing import Process, shared_memory
from pvaccess import PvaServer, PvObject, DOUBLE, ULONG
import struct
import re

#printing the commands has a weird effect on the trigger enabled output to lead to non-trigger output

class slink2_operator:
    def __init__(self, port='COM3', br=921600, parity=serial.PARITY_NONE, sbits=1, tout=0.01, xonxoff=False):
        self.port = port
        self.baudrate = br
        self.parity = parity
        self.stopbits = sbits
        self.write_timeout = tout
        self.xonxoff = xonxoff
        self.s = None
        
    def send_cmd(self,cmd):
        #print(cmd)
        self.s.write(cmd.encode('utf-8'))
             
    def set_polling_mode(self):
        self.send_cmd('*VNM\n')

    def enable_external_trigger(self, channel):
        cmd = '*ET' + str(channel) + '1'
        self.send_cmd(cmd)

    def set_datascale(self, channel, scale):
        padding = 0
        init_pad_0 = ""
        ds_str = str(scale)
        if len(ds_str) <= 2 and scale > 0:
           padding = 2 - len(ds_str)
           init_pad_0 = "0" * padding
        else:
           print('incorrect sampling size'+ds_str)
           return -1
        cmd = '*SC' + str(channel) + init_pad_0 + ds_str + '\n'
        self.send_cmd(cmd)
        return 0
        
    def reset_slink_device(self):
        self.send_cmd('*RST\n')

    def get_version(self):
        self.send_cmd('*VER\n')
        print(self.s.read_until())

    def set_ASCII_mode(self, channel, sampling_size):
        padding = 0
        init_pad_0 = ""
        ss_str = str(sampling_size)
        if len(ss_str) <= 3 and sampling_size > 0:
           padding = 3 - len(ss_str)
           init_pad_0 = "0" * padding
        else:
           print('incorrect sampling size'+ss_str)
           return -1
        cmd = '*SS' + str(channel) + init_pad_0 + ss_str + '\n'
        self.send_cmd(cmd)
        return 0        

    def set_wavelength(self, channel, wavelength):
        wavestr = str(wavelength)
        padding = 0
        init_pad_0 = ""
        if len(wavestr) <= 5 and wavelength > 0:
           padding = 5 - len(wavestr)
           init_pad_0 = "0" * padding
        else:
           print('incorrect sampling size'+wavestr)
           return -1
        init_pad_0 = "0" * padding
        cmd = '*PW'+ str(channel) + init_pad_0 + wavestr + '\n'
        self.send_cmd(cmd)

    def start_internal_acquisition(self, channel):
        cmd = '*CA' + str(channel) + '\n'
        self.send_cmd(cmd)
        
    def stop_internal_acquisition(self, channel):
        cmd = '*CS' + str(channel) + '\n'
        self.send_cmd(cmd)

    def start_data_collection(self, channel, wave, datascale, external_trigger, shm_name):
        pv = PvObject({'energy' : DOUBLE, 'src_ts' : ULONG})
        self.pvaServer = PvaServer('pair', pv)
        signal.signal(signal.SIGINT, handler)
        self.s = serial.Serial(self.port, baudrate=self.baudrate, bytesize=8, parity=self.parity, stopbits=self.stopbits, write_timeout = self.write_timeout, xonxoff=self.xonxoff)
        self.reset_slink_device()
        self.get_version()
        self.set_ASCII_mode(channel, 1)        
        self.set_wavelength(channel, wave)
        self.set_datascale(channel, datascale)
        self.set_polling_mode()
        if external_trigger == 1:
            self.enable_external_trigger(channel)
        self.start_internal_acquisition(channel)
        existing_shm = shared_memory.SharedMemory(name=shm_name)
        count = 0
        prev_ts = 0
        diff_ts = 0
        while existing_shm.buf[0] != 1:
            self.s.write('*CV1\n'.encode('utf-8'))
            val = self.s.read_until()
            ts = time.perf_counter_ns()
            value = float(val.decode('utf-8').split(":")[1].split('\r')[0])
            print(value)
            print(type(ts))
            current_pv = PvObject({'energy' : DOUBLE, 'src_ts' : ULONG}, {'energy' : value, 'src_ts': ts})
            self.pvaServer.update(current_pv)
            if count > 0:
                diff_ts = ts - prev_ts
                print(str(count)+': '+str(ts)+': '+str(val)+','+str(diff_ts))
            prev_ts = ts
            count = count + 1
        print('child stopping data collection')
        self.stop_internal_acquisition(channel)
        self.s.reset_input_buffer()
        self.s.reset_output_buffer()
        self.s.close()
        existing_shm.close()

def handler(signum, frame):
    shm = shared_memory.SharedMemory(name="stop_run")
    shm.buf[0] = 1
    print('stop data collection message sent', shm.buf[0])    
    
def main():
    shm = shared_memory.SharedMemory(name="stop_run", create=True, size=1)
    shm.buf[0] = 0
    sl = slink2_operator(port='COM3', br=921600, parity=serial.PARITY_NONE, sbits=1, tout=2.0, xonxoff=False)
    p = Process(target=sl.start_data_collection, args=(1, 1064, 18, 1,shm.name))
    p.start()
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    p.join()
    shm.close()
    shm.unlink() 

if __name__ == '__main__':
    main() 