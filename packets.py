import collections
import os
file_path = os.path.join(os.getcwd(), 'user.bin')

command_start = [0x55, 0x55]

FOUND_INIT_STATE = 0
FOUND_START_STATE = 1
FOUND_PACKET_STATE = 2

result = {}


global start
global total
global step

start = 0
total = 16301545
step = 100000


def can_read():
    global start
    global total
    global step

    start += step
    
    if step<100000:
        return False

    if start > total:
        step = 1545
        return True

    return True


with open(file_path, 'rb') as file_access:
    while can_read():
        read_buf = file_access.read(step)

        command_match = collections.deque(maxlen=2)
        packet_type = []
        match_state = FOUND_INIT_STATE
        for value in read_buf:
            if match_state == FOUND_INIT_STATE:
                command_match.append(value)

            if len(command_match) == 2 and command_match[0] == command_start[0] and command_match[1] == command_start[1]:
                match_state = FOUND_START_STATE
                command_match.clear()
                continue

            if match_state == FOUND_START_STATE:
                packet_type.append(value)
                if len(packet_type) >= 2:
                    match_state = FOUND_PACKET_STATE

            if match_state == FOUND_PACKET_STATE:
                key = str(''.join([str(x) for x in packet_type]))
                if result.__contains__(key):
                    result[key] += 1
                else:
                    result[key] = 1

                command_match.clear()
                packet_type = []
                match_state = FOUND_INIT_STATE

print(result)
