import sys, subprocess

from datetime import datetime
from _datetime import date


# input data ------------------------------------------------------------------
p1_log = 'p1_170811.txt'
rs485_log = 'RS485_170811.txt'


# output data -----------------------------------------------------------------
p1_int_output = 'p1.int.xx.txt'
p1_timeStamp_output = 'p1.ts.xx.csv'


# settings --------------------------------------------------------------------
serial_numbers = ['20237169']
p1_int_limit = 0.5
p1_int_time = 10
date_format = '%Y-%m-%d %H:%M:%S.%f'


# file logger  ----------------------------------------------------------------
# prints to stdout and logfile at the same time
class Logger(object):
    def __init__(self, file_name):
        self.terminal = sys.stdout
        self.log = open(file_name, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        pass    


# global functions ------------------------------------------------------------
def get_time_stamp(l):
    return(l[:26])

def strip_time_stamp(l):
    return(l[27:])

def conv_time(t):
    s = ('20' + t[:2] + '-' + t[2:4] + '-' + t[4:6] +
         ' ' + t[6:8] + ':' + t[8:10] + ':' + t[10:12])
    
    return s


# read p1 messages ------------------------------------------------------------
print('read input files..', end='')
sys.stdout.flush()
def get_compose_time(lines):
    time = 'compose time not found'
    for line in lines:
        if '0-0:1.0.0' in line:
            time = line[37:49]
    return time

f = open(p1_log, 'r')
p1_messages = []
msg = {'lines': [],
       'start': '',
       'end': '',
       'compose_time': ''}

for line in f.readlines(): 
    if 'ELS5' in line:
        msg = {'start': get_time_stamp(line),
               'lines': []}
    if (len(line) == 37 and line[27] == '!'):
        msg['end'] = get_time_stamp(line)
        msg['compose_time'] = get_compose_time(msg['lines'])
        p1_messages.append(msg)
    msg['lines'].append(line)


# read meter readouts from RS485 log ------------------------------------------
f = open(rs485_log, 'r')
sys_readouts = []
meter_readouts = []
data = {'lines': [],
        'start': ''} 

        
def create_new_dataset(line, data, cat):        
    # bkp an allready open dataset
    data['end'] = get_time_stamp(line)
    if cat == 'meter_readout':
        meter_readouts.append(data)
    if cat == 'sys_readout':
        sys_readouts.append(data)
    # create a new dataset
    return {'lines': [],
            'start': get_time_stamp(line)}

cat = 'none'
for line in f.readlines():
    
    # meter readout starts
    if '/2!' in line:
        # bkp open dataset and create a new one
        data = create_new_dataset(line, data, cat)
        cat = 'meter_readout'
    # system readout starts
    if any(sn + '!' in line for sn in serial_numbers):
        # bkp open dataset and create a new one
        data = create_new_dataset(line, data, cat)
        cat = 'sys_readout'
        
    data['lines'].append(line)

print('done')

# analyse data ----------------------------------------------------------------

def get_t_diff(m0, m1):
    t0 = datetime.strptime(m0['start'], date_format)
    t1 = datetime.strptime(m1['start'], date_format)
    diff = t1 - t0
    return float(str(diff.seconds)+'.'+str(diff.microseconds))
    
    
# calc intervals 
print('calc p1 intervals..', end='')
sys.stdout.flush()
for i  in range(1, len(p1_messages)):
    diff = get_t_diff(p1_messages[i-1], p1_messages[i])
    p1_messages[i]['t_int'] = diff
print('done')


# find bad intervals
print('find bad intervals..', end='')
sys.stdout.flush()
p1_int_errors = []
error = p1_int_time * p1_int_limit
upper_limit = p1_int_time + error
lower_limit = p1_int_time - error
for i, m in enumerate(p1_messages):
    try:
        if m['t_int'] < lower_limit or m['_int'] > upper_limit:
            m['last_push'] = p1_messages[i-1]
            p1_int_errors.append(m)
    except KeyError:
        pass
print('done')
    
    
# find sys readouts relating to p1 interval errors
print('find sys readouts relating to p1 interval errors..', end='')
sys.stdout.flush()
for m in p1_int_errors:
    m['sys_com_before'] = sys_readouts[0]
    m['sys_com_after'] = sys_readouts[-1]
    for readout in sys_readouts:
        # find sys readout next to message
        # before

        if get_t_diff(readout, m) < get_t_diff(m['sys_com_before'], m):
            m['sys_com_before'] = readout

        # after
        if get_t_diff(m, readout) > get_t_diff(m['sys_com_after'], m):
            m['sys_com_after'] = readout
print('done')


# find sys readouts during p1 push  
print('find sys readouts during p1 push..', end='')
sys.stdout.flush()
for m in p1_messages:
    m['sys_com_during'] = []
    for r in sys_readouts:
        if r['start'] >= m['start'] and r['start'] <= m['end']:
            m['sys_com_during'].append(r)
print('done')


# write p1 interval output ----------------------------------------------------
output1 = p1_int_output.replace('xx', datetime.now().strftime('%Y%m%d%H%M')[2:])
print('\nprint p1 interval data to %s:' %output1)
# redirect stdout
sys.stdout = Logger(output1)
print('%i p1 messages and %i system readouts analysed..' %(len(p1_messages),
                                                           len(sys_readouts)))
print('%i time interval(s) out of tolerance (+/-%i%%):' 
      %(len(p1_int_errors), int(p1_int_limit * 100)))
for i, m in enumerate(p1_int_errors):
    print('\n%f' %(m['t_int']))
    print('    time push:           %s - %s' %(m['start'], m['end']))
    print('    time last push:      %s - %s' %(m['last_push']['start'],
                                                m['last_push']['end']))
    t = m['compose_time']
    print('    time stamp push:     %s (%s)' %(conv_time(t), t))
    #print('    msg compose time:   %s' %conv_time(m['compose_time']))
    print('    sys readout before:  %s - %s' %(m['sys_com_before']['start'],
                                              m['sys_com_before']['end']))
    print('    sys readout during: ', end='')
    for i in m['sys_com_during']:
        print('%s, ' %i['start'], end='')
    print()
    print('    sys readout after:   %s' %m['sys_com_after']['start'])

sys.stdout = sys.__stdout__


# write p1 timeStamp output ---------------------------------------------------
output2 = p1_timeStamp_output.replace('xx', datetime.now().strftime('%Y%m%d%H%M')[2:])
print('\nprint p1 interval data to %s:' %output1)
# redirect stdout
sys.stdout = Logger(output2)

print('time;timeStamp;timeStamp_converted;diff;')
for m in p1_messages:
    t0 = datetime.strptime(m['start'][:19], '%Y-%m-%d %H:%M:%S')
    t1 = datetime.strptime(conv_time(m['compose_time']), '%Y-%m-%d %H:%M:%S')
    diff = t1 - t0
    #f_diff = float(str(diff.seconds)+'.'+str(diff.microseconds))
    
    print('%s;%s;%s;%s;' %(m['start'][:19], m['compose_time'],
                        conv_time(m['compose_time']), diff))

sys.stdout = sys.__stdout__


# open files in editor --------------------------------------------------------
subprocess.Popen('notepad.exe %s' %output1)
subprocess.Popen('notepad.exe %s' %output2)
