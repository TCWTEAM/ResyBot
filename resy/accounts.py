import random
from utils import Utils
from database import Database
import sys
import os
import redis
import json

database = Database()
utils = Utils()

# TODO: rewrite this using keep track of inactive accounts and redis pool
class Accounts:
    def __init__(self, source="worker"):
        self.accounts = []
        self.elite_accounts = []
        self.source = source

        self.redis = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), decode_responses=True, db=0)

        self.load_accounts()
        self.load_elite_accounts()

        if len(self.accounts) <= 0:
            utils.thread_error("No normal accounts loaded, killing program")
            sys.exit(1)
        elif len(self.elite_accounts) <= 0:
            utils.thread_error("No elite accounts loaded, killing program")
            sys.exit(1)

        utils.thread_success(f"Loaded {len(self.accounts)} resy accounts")
        utils.thread_success(f"Loaded {len(self.elite_accounts)} resy elite accounts")

    def load_accounts(self):
        normal_accs = database.get_normal_accounts()
        for normal_acc in normal_accs:
            # patch for faker lib using prefixes as names
            if len(normal_acc["first_name"]) > 4:
                self.accounts.append(normal_acc)

        random.shuffle(self.accounts)

    def load_elite_accounts(self):
        elite_accs = database.get_elite_accounts()
        for elite_acc in elite_accs:
            if len(elite_acc["first_name"]) > 4:
                self.elite_accounts.append(elite_acc)

        random.shuffle(self.elite_accounts)

    def get_account(self, account_type="normal"):
        account_type = account_type.lower()
        if account_type == "elite":
            return self.get_elite_account()
        else:
            return self.get_normal_account()

    def get_preloaded_cnt(self):
        return self.redis.scard("resy-engine:preload-acc-normal") + self.redis.scard("resy-engine:preload-acc-elite")
    def get_normal_account(self):
        if (self.source != "monitor"):
            if (self.get_preloaded_cnt() > 0 ):
                random_preload = self.redis.srandmember('resy-engine:preload-acc-normal')

                if random_preload is not None:
                    self.redis.srem("resy-engine:preload-acc-normal", random_preload)

                    utils.thread_log("Using preloaded account")

                    unwrapped_item = json.loads(random_preload)

                    return unwrapped_item

        if len(self.accounts) <= 0:
            utils.thread_error("No Accounts Left In Pool")
            sys.exit(1)

        chosen_acc = random.choice(self.accounts)
        self.accounts.remove(chosen_acc)

        return chosen_acc

    def get_elite_account(self):
        if (self.source != "monitor"):
            if (self.get_preloaded_cnt() > 0 ):
                random_preload= self.redis.srandmember('resy-engine:preload-acc-elite')

                if random_preload is not None:
                    self.redis.srem("resy-engine:preload-acc-elite", random_preload)

                    utils.thread_log("Using preloaded account")

                    unwrapped_item = json.loads(random_preload)

                    return unwrapped_item

        if len(self.elite_accounts) <= 0:
            utils.thread_error("No Accounts Left In Pool")
            sys.exit(1)

        chosen_acc = random.choice(self.elite_accounts)
        self.elite_accounts.remove(chosen_acc)

        return chosen_acc

    def get_count(self):
        return {
            "normal": len(self.accounts),
            "elite": len(self.elite_accounts)
        }
