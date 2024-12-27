import threading
import colorama
from termcolor import colored
from datetime import datetime

colorama.init()

class Utils:
    def __init__(self):
        return

    def thread_log(self, message):
        msg = f"[{threading.current_thread().name}] <{datetime.utcnow()}> {message}"

        print(colored(msg, "cyan"))


    def thread_error(self, message):
        msg = f"[{threading.current_thread().name}] <{datetime.utcnow()}> {message}"

        print(colored(msg, "red"))


    def thread_warn(self, message):
        msg = f"[{threading.current_thread().name}] <{datetime.utcnow()}> {message}"

        print(colored(msg, "yellow"))


    def thread_success(self, message):
        msg = f"[{threading.current_thread().name}] <{datetime.utcnow()}> {message}"
 
        print(colored(msg, "green"))


    def thread_print(self, message):
        print(f"[{threading.current_thread().name}] <{datetime.utcnow()}> {message}")
