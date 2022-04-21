import os
import sys
from signal import SIGINT
from subprocess import Popen
from time import sleep


PYTHON_PATH = sys.executable
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

def get_subprocess(file_with_args):
    sleep(0.5)
    file_full_path = f"{PYTHON_PATH} {BASE_PATH}/{file_with_args}"
    args = ["gnome-terminal", "--disable-factory", "--", "bash", "-c", file_full_path]
    return Popen(args, preexec_fn=os.setpgrp)


P_LIST = []
while True:
    TEXT_FOR_INPUT = f"Запустить клиентов (s) / Закрыть клиентов (x) / Выйти (q): "
    USER = input(TEXT_FOR_INPUT)

    if USER == 'q':
        break
    elif USER == 's':
        P_LIST.append(get_subprocess("msgr_server.py"))
        sleep(0.2)
        for i in range(2):
            P_LIST.append(get_subprocess(f"msgr_client.py -n test{i+1}"))

    elif USER == 'x':
        while P_LIST:
            victim = P_LIST.pop()
            os.killpg(victim.pid, SIGINT)
