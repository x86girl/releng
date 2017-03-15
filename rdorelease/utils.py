
import datetime


def review_time_fmt(time):
    time_obj = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f000')
    return time_obj.strftime("%s")


def log_message(category, msg, logfile, stdout_only=False):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = "%s - %s: %s" % (now, category, msg)
    print(log_msg)
    if not stdout_only:
        f = open(logfile, 'a+')
        f.write(log_msg + '\n')
