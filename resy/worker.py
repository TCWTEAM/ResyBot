import sys
from utils import Utils
from datetime import datetime, timedelta
import os
from network import Network
from proxies import Proxies
import time
from accounts import Accounts
from random import choice, randint
from database import Database
from aesCipher import AESCipher
from discord import Discord
from pytz import timezone
import threading
import json

utils = Utils()
proxies = Proxies()
accounts = Accounts()
database = Database()
discord = Discord()

aesCiper = AESCipher(os.getenv("ENCRYPTION_KEY"))

START_DELAY = 30

class Worker:
    def __init__(self, res_config, party_size, parent="N/A"):
        self.parent = parent
        self.res_config = res_config
        self.party_size = party_size
        self.network = Network(proxies.get_book_proxy())
        self.end_time = datetime.now(timezone("EST")) + timedelta(
            minutes=res_config["monitor"]["timer"]
        )
        self.drop_time = datetime.combine(
            datetime.now(timezone("EST")),
            datetime.strptime(res_config["monitor"]["drop"], "%H:%M:%S").time(),
            tzinfo=timezone("EST"),
        )
        self.start_time = datetime.now(timezone("EST"))
        if self.is_scheduled():
            end_time = datetime.strptime(res_config["monitor"]["end"], "%H:%M:%S").time()
            if end_time.hour == 0:
                self.end_time = datetime.combine(
                    datetime.now(timezone("EST")) + timedelta(days=1),
                    datetime.strptime(res_config["monitor"]["end"], "%H:%M:%S").time(),
                    tzinfo=timezone("EST"),
                )
            else:
                self.end_time = datetime.combine(datetime.now(timezone("EST")), datetime.strptime(res_config["monitor"]["end"], "%H:%M:%S").time(), tzinfo=timezone("EST"))
            self.start_time = self.drop_time - timedelta(seconds=START_DELAY + randint(1, 30))
            
            utils.thread_log(f"Start time: {self.start_time}, End time: {self.end_time}")

    def start_bot(self):
        if self.is_scheduled() and (datetime.now(tz=timezone("EST")) >= self.end_time):
            utils.thread_error("Drop worker trying to launch post drop, rejecting...")
            sys.exit()

        _, payment_method_id = self.login()
        config_id = self.get_availability()
        book_token = self.init_book(config_id)
        booked, _ = self.book(book_token, payment_method_id)

        if booked:
            return self.successful_worker(config_id)
        else:
            return self.failed_worker(config_id)

    def successful_worker(self, configID):
        with open("./logs/success.log", "a") as f:
            content = f"{self.res_config['date']}|{self.party_size}|{self.res_config['venueID']}|{self.res_config['name']}|{self.account['email']}|{self.account['password']}|{self.account['first_name']}|{self.account['last_name']}|{self.res_config['res_time']}\n"
            f.write(content)

        res_obj = {
            "venue_name": self.res_config["name"],
            "date": self.res_config["date"],
            "party_size": self.party_size,
            "venue_id": self.res_config["venueID"],
            "email": self.account["email"],
            "password": aesCiper.encrypt(self.account["password"]),
            "first_name": self.account["first_name"],
            "last_name": self.account["last_name"],
            "phone_num": self.account["phone_num"],
            "reviewed": False,
            "res_time": self.res_config["res_time"],
            "cancelled": False,
            "createdAt": str(datetime.now(timezone("EST"))),
            "configID": configID,
            "selly": False,
            "parent_process": self.parent
        }

        database.upload_reservation(res_obj)
        database.update_acc(
            {"email": self.account["email"]}, {"$set": {"active": False}}
        )

        utils.thread_success("Booked successfully!")

        try:
            discord.successful_book_wh(self.res_config, self.party_size)
        except:
            utils.thread_error("Error sending discord webhook")
            sys.exit()
        sys.exit()

    def failed_worker(self, config_id):
        # failed_obj = {
        #     "venue_name": self.res_config["name"],
        #     "date": self.res_config["date"],
        #     "party_size": self.party_size,
        #     "venue_id": self.res_config["venueID"],
        #     "res_time": self.res_config["res_time"],
        #     "createdAt": str(datetime.now(timezone("EST"))),
        #     "configID": config_id,
        # }

        # database.upload_failed(failed_obj)

        end_msg = f"Failed to book slot, {threading.active_count()} threads running total, [{config_id}]"
        utils.thread_error(end_msg)
        with open("./logs/failed.log", "a+") as f:
            f.write(f"[{threading.current_thread().name}] {end_msg}\n")

        sys.exit()

    def is_scheduled(self):
        return self.parent.lower() == "scheduled"

    def login(self, retrys=0):
        if retrys > 20:
            utils.thread_error("Login failed on max attempts, killing worker")
            sys.exit()

        self.account = accounts.get_account(self.res_config["accountType"])

        if "auth_token" in self.account:
            # self.network.session.cookies.update(self.account["cookies"])
            self.network.set_auth_token(self.account["auth_token"])

            return self.account["auth_token"], self.account["pmid"]

        try:
            login_res, used_proxy = self.network.login(self.account["email"], self.account["password"])
        except Exception as e:
            utils.thread_error(f"Login failed with exception: {e}")
            return self.login(retrys=retrys + 1)

        if not login_res.ok:
            utils.thread_warn("Login failed, trying new account")

            return self.login(retrys=retrys + 1)
        else:
            if retrys != 0:
                utils.thread_log("Successfully logged into anaccount after retry")

            retrys = 0

        auth_token = login_res.json()["token"]

        self.network.set_auth_token(auth_token)

        payment_method_id = login_res.json()["payment_method_id"]

        is_acc_usable = self.check_acc_usable()
        if not is_acc_usable:
            utils.thread_error("Account is not usable, retrying login with new account")

            return self.login(retrys=retrys + 1)

        return auth_token, payment_method_id

    def check_acc_usable(self):
        try: 
            account_check_res = self.network.account_reservations()
        except Exception as e:
            return False

        if not account_check_res.ok:
            return False

        if account_check_res.status_code == 200:
            if "reservations" in account_check_res.json():
                if len(account_check_res.json()["reservations"]) == 0:
                    return True
        else:
            return False

    # ! TODO: change this from recursion to a while loop
    def get_availability(self, drop_wait=False):
        monitor_delay = self.res_config["monitor"]["delay"]

        # wait until drop
        if self.parent.lower() == "scheduled" and (not drop_wait):
            if datetime.now(tz=timezone("EST")) < self.start_time:
                sleep_time = self.start_time - datetime.now(tz=timezone("EST"))
                if sleep_time.seconds > 1:
                    utils.thread_log(f"Waiting for drop start time {self.start_time}, sleeping for {sleep_time.seconds} second(s)")
                    time.sleep((self.start_time - datetime.now(tz=timezone("EST"))).seconds)
                    drop_wait = True

        if datetime.now(timezone("EST")) > self.end_time:
            utils.thread_error(
                f"Time limit reached, killing thread. {threading.active_count()} threads running total"
            )
            sys.exit()

        try:    
            avail_res = self.network.find_availability(self.res_config, self.party_size)
        except Exception as e:
            utils.thread_error(f"Failed to fetch availability, retrying: {e}")

            return self.get_availability(drop_wait=drop_wait)

        if not avail_res.ok:
            utils.thread_warn(f"Failed to fetch availability, retrying [{avail_res.status_code}]")
            
            if avail_res.status_code == 500:
                time.sleep(0.25)

            return self.get_availability(drop_wait=drop_wait)

        avail_res_json = avail_res.json()

        # bug fix for empty venues
        if len(avail_res_json["results"]["venues"]) == 0:
            time.sleep(monitor_delay)

            return self.get_availability(drop_wait=drop_wait)

        slots = avail_res_json["results"]["venues"][0]["slots"]

        if (len(slots) == 0) or (slots == []) or (slots == "[]"):
            if os.getenv("MODE") and (os.getenv("MODE").lower() == "staging"):
                utils.thread_warn("No slots found, retrying")
            time.sleep(monitor_delay)
            return self.get_availability(drop_wait=drop_wait)

        config_id = self.choose_slot(slots)

        if config_id is None:
            utils.thread_error(slots)
            utils.thread_error(f"Slots found but none matching, killing thread")
            sys.exit()

        res_time = config_id.split("/")[8]

        self.res_config["res_time"] = res_time
        self.res_config["bot_start"] = time.time()
        
        # Disable this for now for speed
        # utils.thread_log(f"Found slot {config_id}")

        return config_id        

    def choose_slot(self, slots):
        if len(slots) == 0:
            return None

        possible_slot = choice(slots)
        slot_config_id = possible_slot["config"]["token"]

        if any(exc in slot_config_id.lower() for exc in self.res_config["monitor"]["exclude"]):
            slots.remove(possible_slot)
            return self.choose_slot(slots)

        if self.res_config["monitor"]["timeFilter"]["enabled"]:
            res_time = int(slot_config_id.split(":")[1].split("/")[-1])
            if res_time <= self.res_config["monitor"]["timeFilter"]["minTime"]:
                slots.remove(possible_slot)
                return self.choose_slot(slots)

            if res_time >= self.res_config["monitor"]["timeFilter"]["maxTime"]:
                slots.remove(possible_slot)
                return self.choose_slot(slots)

        return slot_config_id

    def init_book(self, config_id, retrys=0):
        if retrys > self.network.MAX_INIT_BOOK_RETRYS:
            utils.thread_error("Failed to init book after max attempts, killing thread")
            sys.exit()

        try:
            init_book_res = self.network.init_book(config_id, self.res_config["date"], self.party_size)
        except Exception as e:
            utils.thread_error(f"Failed to init book with exception: {e}")
            return self.init_book(config_id, retrys=retrys + 1)

        if not init_book_res.ok:
            utils.thread_warn(f"Failed to init book, retrying [{init_book_res.status_code}] [{init_book_res.text}]")
            
            if retrys == 10:
                time.sleep(0.3)
            return self.init_book(config_id, retrys=retrys + 1)

        book_token = init_book_res.json()["book_token"]["value"]

        return book_token

    def book(self, book_token, payment_method_id, retrys=0):
        if retrys > self.network.MAX_BOOK_RETRYS:
            return False, None

        try:
            book_res = self.network.book(book_token, payment_method_id)
        except Exception as e:
            utils.thread_error(f"Failed to book with exception: {e}")
            return self.book(book_token, payment_method_id, retrys=retrys + 1)

        if book_res.status_code == 404:
            utils.thread_error("Failed to book, slot already booked up")
            return False, None

        if not book_res.ok:
            utils.thread_error(f"Failed to book, retrying [{book_res.status_code}]")

            return self.book(book_token, payment_method_id, retrys=retrys + 1)

        return True, book_res.text
