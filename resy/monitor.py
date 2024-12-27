import sys
from utils import Utils
import time
from network import Network
# from accounts import Accounts
from proxies import Proxies
from datetime import datetime, timedelta
import copy
from random import randint
from worker import Worker
import threading
from pytz import timezone

proxies = Proxies()
utils = Utils()
# accounts = Accounts("monitor")

# match this to resy.py
WORKER_CNT = 2

class Monitor:
    def __init__(self, res_config, party_size):
        self.network = Network(proxies.get_proxy())
        self.max_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        self.start_date = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
        self.old_cal = {}
        self.initialized_cal = False
        self.res_config = res_config
        self.party_size = party_size

    def start(self):
        # _, _ = self.login()
        self.monitor()

    # def login(self, retrys=0):
    #     if retrys > 20:
    #         utils.thread_error("Login failed on max attempts, killing worker")
    #         sys.exit()

    #     self.account = accounts.get_account(self.res_config["accountType"])

    #     try:
    #         login_res = self.network.login(self.account["email"], self.account["password"])
    #     except Exception as e:
    #         utils.thread_error(f"Login failed with exception: {e}")
    #         time.sleep(self.network.ERROR_DELAY_LOGIN)
    #         return self.login(retrys=retrys + 1)

    #     if not login_res.ok:
    #         utils.thread_warn("Login failed, trying new account")

    #         time.sleep(self.network.ERROR_DELAY_LOGIN)

    #         return self.login(retrys=retrys + 1)
    #     else:
    #         if retrys != 0:
    #             utils.thread_log("Successfully logged into anaccount after retry")

    #         retrys = 0

    #     auth_token = login_res.json()["token"]

    #     self.network.set_auth_token(auth_token)

    #     payment_method_id = login_res.json()["payment_method_id"]

    #     is_acc_usable = self.check_acc_usable()
    #     if not is_acc_usable:
    #         utils.thread_error("Account is not usable, retrying login with new account")

    #         return self.login(retrys=retrys + 1)

    #     return auth_token, payment_method_id

    # def check_acc_usable(self):
    #     account_check_res = self.network.account_reservations()

    #     if not account_check_res.ok:
    #         return False

    #     if account_check_res.status_code == 200:
    #         if "reservations" in account_check_res.json():
    #             if len(account_check_res.json()["reservations"]) == 0:
    #                 return True
    #     else:
    #         return False

    def monitor(self):
        rate_limited_prev = False
        rate_limited_cnt = 0
        while True:
            try:
                new_cal_res = self.network.get_calendar(self.res_config, self.start_date, self.max_date, self.party_size)
            except Exception as e:
                utils.thread_error(f"Failed to get calendar, trying again: {e}")
                continue

            if (not new_cal_res) or (not new_cal_res.ok):
                if new_cal_res.status_code == 500:
                    if rate_limited_cnt > 30:
                        utils.thread_error("Rate limited over 30 times, something might be wrong")
                        time.sleep(10)
                    elif rate_limited_cnt == 10:
                        # TODO: see if this works
                        self.network = Network(proxies.get_proxy())
                        time.sleep(10)
                    else:
                        time.sleep(0.1)
                    # TODO Change this for non rotating
                    rate_limited_cnt += 1
                    rate_limited_prev = True
                    # time.sleep(0.1)
                    continue

                utils.thread_error(f"Failed to get calendar for unknown reason, trying again: {new_cal_res.status_code}")
                time.sleep(1)
                continue

            if (new_cal_res.status_code == 200) or (new_cal_res.status_code == 201) or (new_cal_res.status_code == 204):
                if rate_limited_prev and (rate_limited_cnt > 50):
                    utils.thread_success(f"Successfully fetched calendar after {rate_limited_cnt} attempts")

                new_cal = new_cal_res.json()

                if self.initialized_cal:
                    new_dates = self.get_calendar_positive_diff(new_cal)

                    if (len(new_dates) != 0) and (new_dates != []):
                        for date in new_dates:
                            temp_config = copy.deepcopy(self.res_config)
                            temp_config["date"] = date
                            temp_config["partyMin"] = self.party_size
                            temp_config["partyMax"] = self.party_size
                            temp_config["monitor"]["timer"] = 0.5

                            self.master_start_worker(temp_config)

                        utils.thread_success(
                            f"Passive monitor found availability on {', '.join(new_dates)}"
                        )
                    
                    self.old_cal = new_cal
                
                    if rate_limited_prev:
                        rate_limited_prev = False
                        rate_limited_cnt = 0
                else:
                    utils.thread_log("Initialized first calendar")
                    self.initialized_cal = True
                    self.old_cal = new_cal

            # wait monitor delay
            time.sleep(randint(1,10))

    def get_calendar_positive_diff(self, latest_cal):
        new_dates = []
        if latest_cal != self.old_cal:
            # if new date available send right away
            if latest_cal["last_calendar_day"] != self.old_cal["last_calendar_day"]:
                utils.thread_success("Calendar new last date available!!!!!!!!")
                return [latest_cal["last_calendar_day"]]

            # now we iterate for differences    s s s    s
            # probably a better way to do this but this is O(n) so im ok
            idx = 0
            for date in latest_cal["scheduled"]:
                # sanity check comparison, otherwise just pass on giving a diff tbh
                old_date = self.old_cal["scheduled"][idx]
                if date["date"] != old_date["date"]:
                    utils.thread_error("Date mismatch in calendar, something is wrong")
                    return [new_dates]

                if (date["inventory"]["reservation"] == "available") and (
                    old_date["inventory"]["reservation"] != "available"
                ):
                    utils.thread_success(f"Found new date available!!!")
                    new_dates.append(date["date"])

                idx += 1

            return new_dates

        return []

    def master_start_worker(self, res_config):
        offset_day = (datetime.now() + timedelta(days=res_config["offset"])).strftime("%Y-%m-%d")

        # TODO: add a check to see if its within 5 minutes of drop
        if res_config["date"] == offset_day:
            if (datetime.now(timezone('EST')).hour <= 13) or ((datetime.now(timezone('EST')).hour == 23) or (datetime.now(timezone("EST")).hour == 0)):
                utils.thread_error("Drop day worker trying to launch from monitor inside of drop times, refusing")
                return

        minParty = res_config["partyMin"]
        maxParty = res_config["partyMax"]
        grabmax = res_config["grabMax"]
        utils.thread_log(
            f"Spinning up {(grabmax * len(range(minParty, maxParty + 1))) * WORKER_CNT} Workers"
        )

        for party_config in range(minParty, maxParty + 1):
            for grab_instance in range(grabmax):
                for worker_i in range(0, WORKER_CNT):
                    worker_name = f"{res_config['name'].replace(' ', '-')}:{party_config}:{grab_instance}:{worker_i}:{res_config['date']}"
                    threading.Thread(
                        target=self.start_worker,
                        args=(
                            res_config,
                            party_config,
                        ),
                        name=worker_name,
                    ).start()
                    
    # these are copied from the main script, i forgot to abstract and this is easier
    def start_worker(self, res_config, party_config):
        try:
            Worker(res_config, party_config, parent="monitor").start_bot()
        except (KeyboardInterrupt, SystemExit):
            sys.exit()
