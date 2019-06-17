import sys
import os

try:
    import termios
except ImportError:
    pass


# 中断程序
def interrupt(ostype, msg):
    if ostype == "windows":
        sys.stdout.write(msg + "\r\n")
        sys.stdout.flush()
        os.system("echo Press any key to Exit...")
        os.system("pause > nul")
    if ostype == "linux":
        fd = sys.stdin.fileno()
        old_ttyinfo = termios.tcgetattr(fd)
        new_ttyinfo = old_ttyinfo[:]
        new_ttyinfo[3] &= ~termios.ICANON
        new_ttyinfo[3] &= ~termios.ECHO
        sys.stdout.write(msg + "\r\n" + "Press any key to Exit..." + "\r\n")
        sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSANOW, new_ttyinfo)
        os.read(fd, 7)
        termios.tcsetattr(fd, termios.TCSANOW, old_ttyinfo)
    sys.exit()
