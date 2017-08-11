import serial, time, io, datetime, argparse, re
from serial import Serial



parser = argparse.ArgumentParser(description='log serial port')
parser.add_argument('-o', '--output', type=argparse.FileType('w'))
parser.add_argument('-b', '--baudrate', type=int)
parser.add_argument('-p', '--port', type=str)
parser.add_argument('-pr', '--protocol', type=str, help='use "8N1" or "7E1"')
parser.epilog = 'have fun...'

args = parser.parse_args()

for arg in vars(args).values():
    if arg is None:
        print(parser.print_help())
        exit()



ser = serial.Serial(
    port = args.port,\
    baudrate = args.baudrate)

if args.protocol == '7E1':
    ser.bytesize=7
    ser.parity='E'
    ser.stopbits=1


while True:
    data = ser.readline()
    time = datetime.datetime.now()
    if data:
        data = re.sub("'", '', str(data))
        data = re.sub('b', '', str(data))
        args.output.write('%s %s\n' %(time, data))
        print(time, data)
