from datetime import datetime
from datetime import timedelta

input = open('P1_tt.txt', 'r')

match_str = 'ELS5'

output = 'test.txt'

#date_format = '%Y-%m-%d %H:%M:%S.%f'
date_format = '%H:%M:%S.%f'


cut = 20
# get time stamps
time_table = []

for line in input.readlines():
    if match_str in line:
        #time_table.append(line[:26])
        time_table.append(line[12:24])


# subtract time stamps
p1_intervals = []
for i  in range(cut + 1, len(time_table)):
    t0 = datetime.strptime(time_table[i-1], date_format)
    t1 = datetime.strptime(time_table[i], date_format)
    dif = t1 - t0
    p1_intervals.append(float(str(dif.seconds)+'.'+str(dif.microseconds)))


# output results
out = open(output, 'w')

for i in p1_intervals:
    print(i)
    out.write('%s\n' %(i))


print('count:', len(p1_intervals))
out.write('count: %s\n' %(len(p1_intervals)))
print('max:', max(p1_intervals))
out.write('max: %s\n' %(max(p1_intervals)))
print('min:', min(p1_intervals))
out.write('min: %s\n' %(min(p1_intervals)))

def out_of_tol(t):
    val = False
    upper = 12
    lower = 8
    if t < lower or t > upper:
        val = True
    return val

l = [t for t in p1_intervals if out_of_tol(t)]
print(l)


    