from dotenv import load_dotenv
import time
import random
import json
from utils import Utils
from database import Database
import sys
from network import Network
from proxies import Proxies
from discord import Discord
import threading
import redis
import os

load_dotenv()

PRELOAD_NUM_NORM = 1000
PRELOAD_NUM_ELITE = 250
MAX_ACCS = 1750
CHECK_POOL_INTERVAL = 60

ONE_DAY_EPOCH = 86400

FLUSH_INTERVAL = ONE_DAY_EPOCH

if os.getenv("MODE") and (os.getenv("MODE").lower() == "staging"):
    PRELOAD_NUM_NORM = 1000
    PRELOAD_NUM_ELITE = 250
    MAX_ACCS = 1750
    CHECK_POOL_INTERVAL = 60

proxies = Proxies()
database = Database()
utils = Utils()
discord = Discord()

# give this the queue and it will manage it
class AccPreloader:
    def __init__(self):
        self.redis = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), decode_responses=True, db=0)

        # flush redis if its been over a day
        if self.check_need_flush():
            utils.thread_error("Flushing redis db")
            discord.logs_wh("Flushing redis db")
            self.flush_db()

        while True:
            self.check_pool()

            utils.thread_warn(f"Account Preloader has {self.get_preloaded_cnt()} accounts loaded")
            time.sleep(CHECK_POOL_INTERVAL)

    def check_pool(self):
        if self.check_need_flush():
            utils.thread_error("Flushing redis db")
            discord.logs_wh("Flushing redis db")
            self.flush_db()

        current_preload_cnt = self.get_preloaded_cnt()

        if (current_preload_cnt <= 0):
            utils.thread_error("Preload queue is empty, preloading accounts")
            threading.Thread(target=self.preload_accounts, args=(PRELOAD_NUM_NORM, "normal",), name="PreloadThreadNorm").start()
            threading.Thread(target=self.preload_accounts, args=(PRELOAD_NUM_ELITE, "elite",), name="PreloadThreadElite").start()
        elif (current_preload_cnt < MAX_ACCS):
            utils.thread_warn("Preload queue is low, preloading accounts")
            threading.Thread(target=self.preload_accounts, args=(PRELOAD_NUM_NORM, "normal",), name="PreloadThreadNorm").start()
            threading.Thread(target=self.preload_accounts, args=(PRELOAD_NUM_ELITE, "elite",), name="PreloadThreadElite").start()

    def check_need_flush(self):
        if not os.path.isfile("./logs/redis_flush.log"):
            # Just so we can have this fresh
            return True

        with open("./logs/redis_flush.log", "r") as f:
            last_flush = f.read()
            if len(last_flush) == 0:
                return True

            if (time.time() - float(last_flush)) > (FLUSH_INTERVAL):
                return True
            else:
                return False

    def flush_db(self):
        with open("./logs/redis_flush.log", "w+") as f:
            f.write(str(time.time()))

        self.redis.flushdb()

    def get_preloaded_cnt(self):
        return self.redis.scard("resy-engine:preload-acc-normal") + self.redis.scard("resy-engine:preload-acc-elite")

    def preload_accounts(self, num, acc_type="normal"):
        if num <= 0:
            return

        retrys_needed = 0
        for _ in range(num):
            if self.get_preloaded_cnt() > MAX_ACCS:
                return
            auth_token, pmid, network, chosen_acc = self.login(acc_type)

            if auth_token is None:
                retrys_needed += 1
                continue
            else:
                chosen_acc["auth_token"] = auth_token
                chosen_acc["pmid"] = pmid
                del chosen_acc["_id"]

                self.redis.sadd(
                    f"resy-engine:preload-acc-{acc_type}", json.dumps(chosen_acc)
                )

        if retrys_needed > 0:
            utils.thread_warn(f"Retrying {retrys_needed} accounts to preload")
            return self.preload_accounts(retrys_needed, acc_type=acc_type)

    # login and checkAccUsable are stolen from accounts.py, we move diff with these
    def login(self, acc_type, retrys=0):
        network = Network(proxies.get_book_proxy())
        if retrys > 20:
            utils.thread_error("Login failed on max attempts, giving up")
            return None, None, None, None 

        account = database.get_random_sexy_accounts(acc_type)[0]

        try:
            login_res, used_proxy = network.login(account["email"], account["password"])
        except Exception as e:
            utils.thread_error(f"Login failed with exception: {e}")
            return self.login(acc_type=acc_type, retrys=retrys + 1)

        if not login_res.ok:
            utils.thread_warn(
                f"Login failed, trying new account [{login_res.status_code}] <{used_proxy}>"
            )

            return self.login(acc_type=acc_type, retrys=retrys + 1)
        else:
            retrys = 0

        auth_token = login_res.json()["token"]

        network.set_auth_token(auth_token)

        payment_method_id = login_res.json()["payment_method_id"]

        is_acc_usable = self.check_acc_usable(network)
        if not is_acc_usable:

            return self.login(acc_type, retrys=retrys + 1)

        return auth_token, payment_method_id, network, account

    def check_acc_usable(self, network):
        try: 
            account_check_res = network.account_reservations()
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
