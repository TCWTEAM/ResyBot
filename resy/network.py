import requests
import urllib3
from utils import Utils
import os
import time
from random import choice
from proxies import Proxies
import sys


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

utils = Utils()
proxies = Proxies()


class Network:
    def __init__(self, proxy):
        # Config keys
        self.USER_AGENT = (
            "Resy/2.81 (com.resy.ResyApp; build:5433; iOS 17.4.1) Alamofire/5.8.0"
        )

        self.RESY_KEY = 'ResyAPI api_key="AIcdK2rLXG6TYwJseSbmrBAy3RP81ocd"'
        self.RESY_KEY_NORM = 'ResyAPI api_key="VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5"'

        self.normal_user_agents = []

        if not os.path.isfile("./uas.txt"):
            utils.thread_error("No user agent file found")
            sys.exit(1)

        with open("./uas.txt", "r") as f:
            for line in f:
                self.normal_user_agents.append(line.strip())

        # Static Values
        self.MAX_ACC_RETRYS = 5
        self.MAX_INIT_BOOK_RETRYS = 20
        self.ERROR_DELAY = 2
        self.MAX_BOOK_RETRYS = 20
        self.ERROR_DELAY_CAL = 3
        self.ERROR_DELAY_LOGIN = 1

        self.session = requests.Session()
        self.proxies = proxy

    def get_session(self):
        return self.session

    def get_random_ua(self):
        return choice(self.normal_user_agents)

    def update_proxy(self, proxy):
        self.proxies = proxy

    def set_auth_token(self, auth_token):
        self.auth_token = auth_token

    def login(self, email, password):
        # Cant find the password endpoint on mobile

        url = "https://api.resy.com/3/auth/password"

        payload = {"email": email, "password": password}
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": self.RESY_KEY_NORM,
            "Cache-Control": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded",
            "Dnt": "1",
            "Origin": "https://resy.com",
            "Priority": "u=1, i",
            "Referer": "https://resy.com/",
            "User-Agent": self.get_random_ua(),
            "X-Origin": "https://resy.com",
        }

        use_proxies = proxies.get_mobile_proxy()
        response = self.session.post(
            url, data=payload, headers=headers, proxies=use_proxies, verify=False, timeout=10
        )

        return response, use_proxies

    def account_reservations(self):
        url = f"https://api.resy.com/3/user/reservations?limit=1&offset=1&type=upcoming&book_on_behalf_of=false"

        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "Accept-Language": "en-US;q=1.0, fr-US;q=0.9",
            "Authorization": self.RESY_KEY_NORM,
            "Connection": "keep-alive",
            "Host": "api.resy.com",
            "User-Agent": self.get_random_ua(),
            "X-Resy-Auth-Token": self.auth_token,
            "X-Resy-Universal-Auth": self.auth_token,
            "cache-control": "no-cache",
        }
        response = self.session.get(url, headers=headers, proxies=proxies.get_proxy(), verify=False, timeout=10)

        return response

    def find_availability(self, res_config, party_size):
        url = "https://api.resy.com/4/find"

        querystring = {
            "lat": "0",
            "long": "0",
            "day": res_config["date"],
            "party_size": party_size,
            "venue_id": res_config["venueID"],
            "sort_by": "available",
        }

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": self.RESY_KEY_NORM,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Origin": "https://resy.com",
            "Referer": "https://resy.com/",
            "User-Agent": self.get_random_ua(),
            "X-Origin": "https://resy.com"
        }

        use_proxy = choice([proxies.get_resi_proxy(), proxies.get_proxy(), proxies.get_proxy(), proxies.get_proxy()])

        # manually overwrite proxy to avoid RL
        response = self.session.get(
            url, headers=headers, params=querystring, proxies=use_proxy, verify=False, timeout=4
        )

        return response

    def init_book(self, config_id, date, party_size):
        url = "https://api.resy.com/3/details"

        payload = {
            "commit": 1,
            "config_id": config_id,
            "day": date,
            "party_size": party_size
        }

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": self.RESY_KEY,
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "Origin": "https://widgets.resy.com",
            "Referer": "https://widgets.resy.com/",
            "User-Agent": self.get_random_ua(),
            "X-Resy-Auth-Token": self.auth_token,
            "X-Resy-Universal-Auth": self.auth_token,
            "X-Origin": "https://widgets.resy.com"
        }

        response = self.session.get(url, params=payload, headers=headers, proxies=proxies.get_mobile_proxy(), verify=False, timeout=4)

        return response

    def book(self, book_token, payment_method_id):
        url = "https://api.resy.com/3/book"

        payload = {
            "book_token": book_token,
            "struct_payment_method": f'{{"id": {payment_method_id}}}',
            "source_id": "resy.com-venue-details",
        }

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": self.RESY_KEY_NORM,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://widgets.resy.com",
            "Referer": "https://widgets.resy.com/",
            "User-Agent": self.get_random_ua(),
            "X-Resy-Auth-Token": self.auth_token,
            "X-Resy-Universal-Auth": self.auth_token
        }

        response = self.session.post(url, data=payload, headers=headers, proxies=proxies.get_mobile_proxy(), verify=False, timeout=60)

        return response

    def get_calendar(self, res_config, start_date, end_date, party_size):
        url = f"https://api.resy.com/4/venue/calendar?venue_id={res_config['venueID']}&num_seats={party_size}&start_date={start_date}&end_date={end_date}"

        headers = {
            'authority': 'api.resy.com',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': self.RESY_KEY_NORM,
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'origin': 'https://resy.com',
            'referer': 'https://resy.com/',
            'user-agent': self.get_random_ua(),
            'x-origin': 'https://resy.com',
        }

        response = self.session.get(url, headers=headers, proxies=proxies.get_proxy(), verify=False, timeout=10)

        return response    
