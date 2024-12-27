import random
import os
import sys
from dotenv import load_dotenv
from utils import Utils

load_dotenv()
utils = Utils()
# TODO: add support for non DC proxies

class Proxies:
    def __init__(self):
        self.proxies = []

        # Proxies that are better for speed n shit
        self.book_proxies = []

        # residential proxies
        self.resi_proxies = []
        
        # mobile proxies
        self.mobile_proxies = []

        if (not os.path.isfile("./proxies.txt")) or (not os.path.isfile("./book_proxies.txt") or (not os.path.isfile("./resi_proxies.txt"))):
            utils.thread_error("No proxies.txt or book_proxies.txt or resi_proxies.txt file found, please make sure you have both")
            sys.exit(1)

        with open("./proxies.txt", "r") as file:
            raw_proxies = file.read().splitlines()

            for raw_proxy in raw_proxies:
                proxy_parts = raw_proxy.split(":")

                if len(proxy_parts) == 2:
                    valid_proxy = f"{proxy_parts[0]}:{proxy_parts[1]}"
                else:
                    valid_proxy = f"{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"

                formatted_proxy = {
                    "http": "http://" + valid_proxy + "/",
                    "https": "http://" + valid_proxy + "/",
                }

                self.proxies.append(formatted_proxy)

        with open("./book_proxies.txt", "r") as file:
            raw_proxies = file.read().splitlines()

            for raw_proxy in raw_proxies:
                proxy_parts = raw_proxy.split(":")

                if len(proxy_parts) == 2:
                    valid_proxy = f"{proxy_parts[0]}:{proxy_parts[1]}"
                else:
                    valid_proxy = f"{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"

                formatted_proxy = {
                    "http": "http://" + valid_proxy + "/",
                    "https": "http://" + valid_proxy + "/",
                }

                self.book_proxies.append(formatted_proxy)

        with open("./resi_proxies.txt", "r") as file:
            raw_proxies = file.read().splitlines()

            for raw_proxy in raw_proxies:
                proxy_parts = raw_proxy.split(":")

                if len(proxy_parts) == 2:
                    valid_proxy = f"{proxy_parts[0]}:{proxy_parts[1]}"
                else:
                    valid_proxy = f"{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"

                formatted_proxy = {
                    "http": "http://" + valid_proxy + "/",
                    "https": "http://" + valid_proxy + "/",
                }

                self.resi_proxies.append(formatted_proxy)

        with open("./mobile_proxies.txt", "r") as file:
            raw_proxies = file.read().splitlines()

            for raw_proxy in raw_proxies:
                proxy_parts = raw_proxy.split(":")

                if len(proxy_parts) == 2:
                    valid_proxy = f"{proxy_parts[0]}:{proxy_parts[1]}"
                else:
                    valid_proxy = f"{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"

                formatted_proxy = {
                    "http": "http://" + valid_proxy + "/",
                    "https": "http://" + valid_proxy + "/",
                }

                self.mobile_proxies.append(formatted_proxy)

        self.print_proxy_output()

    def get_proxy(self):
        return random.choice(self.proxies)

    def get_book_proxy(self):
        return random.choice(self.book_proxies)

    def get_resi_proxy(self):
        return random.choice(self.resi_proxies)

    def get_proxy_list(self):
        return self.proxies

    def get_book_proxy_list(self):
        return self.book_proxies

    def get_mobile_proxy(self):
        return random.choice(self.mobile_proxies)

    def print_proxy_output(self):
        utils.thread_log(f"Loaded {len(self.proxies)} proxie(s)")
        utils.thread_log(f"Loaded {len(self.book_proxies)} book proxie(s)")
        utils.thread_log(f"Loaded {len(self.resi_proxies)} residental proxie(s))")
        utils.thread_log(f"Loaded {len(self.mobile_proxies)} mobile proxie(s))")
