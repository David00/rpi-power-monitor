from time import sleep

def sleep_for(seconds, stop_flag):
    '''Will sleep for the provided number of seconds, checking to see if stop_flag is set every 5 seconds.'''

    for i in range(0, seconds, 5):
        if stop_flag.is_set():
            break
        if (i + 5) < seconds:
            sleep(5)
        else:
            sleep(seconds - i)