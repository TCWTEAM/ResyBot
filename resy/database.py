# Collection of DB calls and helpers

from pymongo import MongoClient
import os
from bson.json_util import dumps, loads
from aesCipher import AESCipher
from dotenv import load_dotenv
import sys
from utils import Utils

load_dotenv()

aesCiper = AESCipher(os.getenv("ENCRYPTION_KEY"))
utils = Utils()

class Database:
    def __init__(self):
        if not os.getenv("DB_URL"):
            utils.thread_error("DB_URL not set")
            return sys.exit(1)

        self.db = MongoClient(host=os.getenv("DB_URL"))

    def get_db(self):
        return self.db.resme

    def get_normal_accounts(self):
        # TODO: only load accounts marked as usable
        accs = self.get_db().resy_accounts.find({"acc_type": "normal", "active": True, "suspended": False})
        accs = loads(dumps(accs))

        for acc in accs:
            acc["password"] = aesCiper.decrypt(acc["password"])

        return accs

    def get_elite_accounts(self):
        accs = self.get_db().resy_accounts.find(
            {"acc_type": "elite", "active": True, "suspended": False}
        )
        accs = loads(dumps(accs))

        for acc in accs:
            acc["password"] = aesCiper.decrypt(acc["password"])

        return accs
    
    def get_random_sexy_accounts(self, acc_type="normal"):
        # run an aggregation pipeline to get a random record
        pipeline = [
            {"$match": {"acc_type": acc_type, "active": True, "suspended": False}},
            {"$sample": {"size": 1}},
        ]
        
        accs = self.get_db().resy_accounts.aggregate(pipeline)
        accs = loads(dumps(accs))
        
        for acc in accs:
            acc["password"] = aesCiper.decrypt(acc["password"])
        
        return accs

    def update_acc(self, query, exec):
        collection = self.get_db().resy_accounts
        collection.update_one(query, exec)        

    def upload_reservation(self, reservation):
        collection = self.get_db().resy_reservations
        collection.insert_one(reservation)
    
    def upload_failed(self, reservation):
        collection = self.get_db().resy_failures
        collection.insert_one(reservation)
