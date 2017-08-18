import sys, subprocess

from operator import itemgetter
from datetime import datetime
from _datetime import date


# input data ------------------------------------------------------------------
p1_log = 'p1_170816.txt'
rs485_log = 'RS485_170816.txt'
input_list = [p1_log, rs485_log]

# output data -----------------------------------------------------------------
p1_int_output = 'p1.int.xx.txt'
p1_timeStamp_output = 'p1.ts.xx.csv'
p1_irregular_lenght_output = 'p1.lenght.changed.xx.txt'
p1_missing_value_output = 'p1.missing.val.xx.txt'
debug_output = 'debug.xx.txt'

# settings --------------------------------------------------------------------
serial_numbers = ['20237169']
p1_int_limit = 0.5
p1_int_time = 10
date_format = '%Y-%m-%d %H:%M:%S.%f'    # don't dare to change this!! ;-)


# file logger  ----------------------------------------------------------------
# prints to stdout and logfile at the same time
class Logger(object):
    def __init__(self, file_name, verbose=False):
        self.verbose = verbose
        self.terminal = sys.stdout
        self.log = open(file_name, "w")

    def write(self, message):
        if self.verbose:
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


# read input files  -----------------------------------------------------------
print('read input files..', end='')
sys.stdout.flush()

p1_messages = []
sys_readouts = []
meter_readouts = []


def create_new_dataset(line, data, cat):        
    # bkp an allready open dataset
    data['end'] = get_time_stamp(line)
    if cat == 'mtr_readout':
        meter_readouts.append(data)
    if cat == 'sys_readout':
        sys_readouts.append(data)
    if cat == 'p1_message':
        p1_messages.append(data)
            
    # create a new dataset
    return {'lines': [],
            'start': get_time_stamp(line)}


for filename in input_list:
    
    f = open(filename, 'r')
    # create first dataset
    data = {'lines': [],
            'start': ''}
    
    cat = 'undefined'
    for line in f.readlines():

        # meter readout starts (read service list)
        if '/2!\\r\\n' in line:
            # bkp open dataset and create a new one
            data = create_new_dataset(line, data, cat)
            cat = 'mtr_readout'
            data['cat'] = cat
        # system readout starts (meter is addressed by serial)
        if any(sn + '!' in line for sn in serial_numbers):
            # bkp open dataset and create a new one
            data = create_new_dataset(line, data, cat)
            cat = 'sys_readout'
            data['cat'] = cat
        # p1 message starts (parse 'ELS5')
        #if 'ELS5' in line and len(line) == 37:
        if 'ELS5\\r\\n' in line:
            # bkp open dataset and create a new one
            data = create_new_dataset(line, data, cat)
            cat = 'p1_message'
            data['cat'] = cat
            
        data['lines'].append(line)
    
print('done')


# analyse data ----------------------------------------------------------------

print('indexing messages..', end='')
sys.stdout.flush()  
unsorted = [m for m in p1_messages] + [m for m in meter_readouts] + \
           [m for m in sys_readouts]

timeLine = sorted(unsorted, key=itemgetter('start'))
for i, m in enumerate(timeLine):
    m['idx_timeline'] = i
print('done')



def get_t_diff(m0, m1):
    t0 = datetime.strptime(m0['start'], date_format)
    t1 = datetime.strptime(m1['start'], date_format)
    diff = t1 - t0
    return float(str(diff.seconds)+'.'+str(diff.microseconds))
    
    
# get compose time for p1 messages
print('read compose time for p1 messages..', end='')    
sys.stdout.flush()
time = 'compose time not found'
for m in p1_messages:
    for line in m['lines']:
        if '0-0:1.0.0' in line:
            time = line[37:49]
        m['compose_time'] = time
print('done')

    
# calc p1 intervals 
print('calc p1 intervals..', end='')
sys.stdout.flush()
for i  in range(1, len(p1_messages)):
    diff = get_t_diff(p1_messages[i-1], p1_messages[i])
    p1_messages[i]['t_int'] = diff
print('done')


# find bad p1 intervals
print('find bad intervals..', end='')
sys.stdout.flush()
p1_int_errors = []
error = p1_int_time * p1_int_limit
upper_limit = p1_int_time + error
lower_limit = p1_int_time - error
for i, m in enumerate(p1_messages[1:]):
    if m['t_int'] < lower_limit or m['t_int'] > upper_limit:
        m['last_push'] = p1_messages[i-1]
        p1_int_errors.append(m)
print('done')



def build_msg_relations(l):
# run through a given list of p1 messages and link nearby sys- and mtr-readouts
    for m in (l):
        if m['cat'] == 'p1_message':
            sys_readout_before_found = False
            mtr_readout_before_found = False
            sys_readout_after_found = False
            mtr_readout_after_found = False
            # search backward
            idx = m['idx_timeline']
            i = idx
            while not(sys_readout_before_found \
            and mtr_readout_before_found) and i:
                msg_check = timeLine[i-1]
                if msg_check['cat'] == 'sys_readout' and sys_readouts \
                and not sys_readout_before_found:
                    m['sys_readout_before'] = msg_check
                    sys_readout_before_found = True
                if msg_check['cat'] == 'mtr_readout' and meter_readouts \
                and not mtr_readout_before_found:
                    m['mtr_readout_before'] = msg_check
                    mtr_readout_before_found = True
                i -= 1
            # search foreward
            i = idx
            while not(sys_readout_after_found and mtr_readout_after_found) \
            and i < len(timeLine)-1:
                msg_check = timeLine[i+1]
                if msg_check['cat'] == 'sys_readout' and sys_readouts \
                and not sys_readout_after_found:
                    m['sys_readout_after'] = msg_check
                    sys_readout_after_found = True
                if msg_check['cat'] == 'mtr_readout' and meter_readouts \
                and not mtr_readout_after_found:
                    m['mtr_readout_after'] = msg_check
                    mtr_readout_after_found = True
                i += 1



# find sys readouts relating to p1 interval errors
print('find sys readouts relating to p1 interval errors..', end='')
sys.stdout.flush()
build_msg_relations(p1_int_errors)
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


# analyze p1 message lenght
print('check lenght of p1 messages..', end='')
sys.stdout.flush()
for i, m in enumerate(p1_messages[1:]):
    last_message = p1_messages[i-1]
    if len(m['lines']) != len(last_message['lines']):
        m['lenght_changed'] = True
    len(m['lines'])
print('done')


# search missing p1 values
print('search for missing p1 values..', end='')
sys.stdout.flush()
for m in p1_messages:
    for l in m['lines']:
        if '()' in l:
            m['missing_value'] = True
print('done')


def print_msg_relations(msg):
    t = m['compose_time']
    print('    time-stamp push:      %s (%s)' %(conv_time(t), t))
    
    print('    time push:            %s - %s' %(m['start'], m['end']))
    print('    time last push:       %s - %s' %(m['last_push']['start'],
                                                m['last_push']['end']))
  
    try:
        print('    sys readout before:   %s - %s' %(m['sys_readout_before']['start'],
                                                    m['sys_readout_before']['end']))
    except KeyError:
        print('    sys readout before: none')
    
    try:
        print('    sys readout after:    %s - %s' %(m['sys_readout_after']['start'],
                                                    m['sys_readout_after']['end']))
    except KeyError:
        print('    sys readout after:')
    
    try:
        print('    meter readout before: %s - %s' %(m['mtr_readout_before']['start'],
                                                    m['mtr_readout_before']['end']))
    except KeyError:
        print('    meter readout before:')
    
    try:
        print('    meter readout after:  %s - %s' %(m['mtr_readout_after']['start'],
                                                    m['mtr_readout_after']['end']))
    except KeyError:
        print('    meter readout after:')

    print()

'''
# write debug output ----------------------------------------------------
output0 = debug_output.replace('xx', datetime.now().strftime('%Y%m%d%H%M')[2:])
print('\nprint debug info to %s..' %output0)
# redirect stdout
sys.stdout = Logger(output0, verbose=False)
print('debug info:')
for m in p1_int_errors:
    print(m['start'])
    print('    ', m['mtr_readout_before'])
sys.stdout = sys.__stdout__
print('done')
subprocess.Popen('notepad.exe %s' %output0)

'''


# write p1 interval output ----------------------------------------------------
output1 = p1_int_output.replace('xx', datetime.now().strftime('%Y%m%d%H%M')[2:])
print('\nprint p1 interval data to %s..' %output1)
# redirect stdout
sys.stdout = Logger(output1, verbose=False)
print('%i p1 messages and %i system readouts analysed..' %(len(p1_messages),
                                                           len(sys_readouts)))
print('%i time interval(s) out of tolerance (+/-%i%%):' 
      %(len(p1_int_errors), int(p1_int_limit * 100)))
for i, m in enumerate(p1_int_errors):
    print('\nbad interval (%fs):' %(m['t_int']))
    print_msg_relations(m)
sys.stdout = sys.__stdout__
print('done')
subprocess.Popen('notepad.exe %s' %output1)

'''
# write p1 timeStamp output ---------------------------------------------------
output2 = p1_timeStamp_output.replace('xx', datetime.now().strftime('%Y%m%d%H%M')[2:])
print('\nprint p1 interval data to %s..' %output1)
# redirect stdout
sys.stdout = Logger(output2, verbose=False)
print('time;timeStamp;timeStamp_converted;diff;')
for m in p1_messages:
    t0 = datetime.strptime(m['start'][:19], '%Y-%m-%d %H:%M:%S')
    t1 = datetime.strptime(conv_time(m['compose_time']), '%Y-%m-%d %H:%M:%S')
    diff = t1 - t0
    #f_diff = float(str(diff.seconds)+'.'+str(diff.microseconds))
    
    print('%s;%s;%s;%s;' %(m['start'][:19], m['compose_time'],
                        conv_time(m['compose_time']), diff))

sys.stdout = sys.__stdout__
print('done')
subprocess.Popen('notepad.exe %s' %output2)
'''

# write irregular messages lenght ouput ---------------------------------------
output3 = p1_irregular_lenght_output.replace('xx', datetime.now().strftime('%Y%m%d%H%M')[2:])
print('\nprint missing p1 values information to %s..' %output3)
# redirect stdout
sys.stdout = Logger(output3, verbose=False)
cnt = 0
for m in p1_messages:
    try:
        if m['lenght_changed']:
            print('%s lenght changed to %i lines' %(m['start'], len(m['lines'])))
            cnt += 1
    except KeyError:
        pass
if cnt == 0:
    print('all logged p1 messages have the same lenght (%i lines)' %len(m['lines']))
sys.stdout = sys.__stdout__
print('done')
subprocess.Popen('notepad.exe %s' %output3)

'''
# write missing values ouput ---------------------------------------
output4 = p1_missing_value_output.replace('xx', datetime.now().strftime('%Y%m%d%H%M')[2:])
print('\nprint p1 interval data to %s..' %output4)
# redirect stdout
sys.stdout = Logger(output4, verbose=False)
cnt = 0
for m in p1_messages:
    try:
        if m['missing_value']:
            print('missing value(s):')
            print('    %s' %(m['start']))
            cnt += 1
    except KeyError:
        pass
if cnt == 0:
    print('no missing values detected..')
sys.stdout = sys.__stdout__
print('done')
subprocess.Popen('notepad.exe %s' %output4)

'''