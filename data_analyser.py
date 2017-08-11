from datetime import datetime
from datetime import timedelta

p1_log = 'p1_2.txt'
rs485_log = 'RS485_2.txt'

serial_numbers = ['20237169']

date_format = '%Y-%m-%d %H:%M:%S.%f'

p1_int_limit = 0.5
p1_int_time = 10


def get_time_stamp(l):
    return(l[:26])

def strip_time_stamp(l):
    return(l[27:])

def conv_time(t):
    s = ('20' + t[:2] + '-' + t[2:4] + '-' + t[4:6] +
         ' ' + t[6:8] + ':' + t[8:10] + ':' + t[10:12])
    
    return s

# read p1 messages ------------------------------------------------------------
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
    
# -----------------------------------------------------------------------------


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
# -----------------------------------------------------------------------------


# analyse data ----------------------------------------------------------------

def get_t_diff(m0, m1):
    t0 = datetime.strptime(m0['start'], date_format)
    t1 = datetime.strptime(m1['start'], date_format)
    diff = t1 - t0
    return float(str(diff.seconds)+'.'+str(diff.microseconds))
    
# calc intervals 
for i  in range(1, len(p1_messages)):
    diff = get_t_diff(p1_messages[i-1], p1_messages[i])
    p1_messages[i]['t_int'] = diff


# find bad intervals
p1_int_errors = []
error = p1_int_time * p1_int_limit
upper_limit = p1_int_time + error
lower_limit = p1_int_time - error
for m in p1_messages:
    try:
        if m['t_int'] < lower_limit or m['_int'] > upper_limit:
            p1_int_errors.append(m)
    except KeyError:
        pass
    
# find sys readouts relating to p1 interval errors
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


# find sys readouts during p1 push   
for m in p1_messages:
    m['sys_com_during'] = []
    for r in sys_readouts:
        if r['start'] >= m['start'] and r['start'] <= m['end']:
            m['sys_com_during'].append(r)

 
# -----------------------------------------------------------------------------

print('%i p1 messages and %i system readouts analysed..' %(len(p1_messages),
                                                           len(sys_readouts)))
print('%i time interval(s) out of tolerance (+/-%i%%):' 
      %(len(p1_int_errors), int(p1_int_limit * 100)))
for m in p1_int_errors:
    print('\n%f' %(m['t_int']))
    print('    msg push time:      %s' %m['start'])
    #print('    msg compose time:   %s' %conv_time(m['compose_time']))
    print('    sys readout before: %s - %s' %(m['sys_com_before']['start'],
                                              m['sys_com_before']['end']))
    print('    sys readout during: ', end='')
    for i in m['sys_com_during']:
        print('%s, ' %i['start'], end='')
    print()
    print('    sys readout after:  %s' %m['sys_com_after']['start'])

