import json
import os
import sys
from utils import Utils
import threading
import time
from dotenv import load_dotenv
from worker import Worker
from monitor import Monitor
from datetime import datetime, timedelta
from acc_preloader import AccPreloader
from pytz import timezone
from discord import Discord
import schedule
import sentry_sdk

# this is to adjust the monitoring recursive limit, its not heavy python can chill
sys.setrecursionlimit(99999)

# load the environment from .env
load_dotenv()

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN")
    )

# Initialize classes
utils = Utils()
discord = Discord()

# Initialize constants

# Constants that are dynamically assigned
# sites we are going to run bots on
resy_bot_lst = []
# sites we are going to run the monitor on
resy_monitor_lst = []
# signals that we are in dev mode
DEV_MODE = os.getenv("DEV_MODE")
# signals that we are in debug mode
DEBUG = os.getenv("DEBUG")

MONITOR_WORKERS = 2
WORKER_CNT = 3
WORKER_LAUNCH_TIME = 10


def file_init():
    # initialize the required files and folders
    if not os.path.isdir("./logs"):
        os.mkdir("./logs")
        utils.thread_success("Created logs folder")

    # create error log file
    if not os.path.isfile("./logs/error.log"):
        open("./logs/error.log", "w+")

    # create general log file
    if not os.path.isfile("./logs/log.log"):
        open("./logs/log.log", "w+")

    # create success log file
    if not os.path.isfile("./logs/success.log"):
        with open("./logs/success.log", "a+") as f:
            f.write("\n")
            f.write("-" * 50)
            f.write("\n")

    if not os.path.isfile("./logs/failed.log"):
        with open("./logs/failed.log", "a+") as f:
            f.write("\n")
            f.write("-" * 50)
            f.write("\n")

    utils.thread_success("Validated file integrity")

def config_init():
    config_path = "./resy.json"

    config_override_path = os.getenv("CONFIG_OVERRIDE")
    if config_override_path and (os.path.isfile(config_override_path)):
        utils.thread_log(f"USING CONFIG OVERRIDE PATH {config_override_path}")
        config_path = config_override_path

    # TODO: move this to the database
    if not os.path.isfile(config_path):
        utils.thread_error("No valid config file found")
        sys.exit(1)

    with open(config_path, "r") as f:
        resy_config = json.load(f)

        for resy_restaurant in resy_config:
            if resy_restaurant["enabled"]:

                resy_bot_lst.append(resy_restaurant)

                if ("forceStart" in resy_restaurant) and (resy_restaurant["forceStart"]):
                    init_bot(resy_restaurant)

            if resy_restaurant["passiveMonitoring"]:
                resy_monitor_lst.append(resy_restaurant)

    utils.thread_success(f"Loaded {len(resy_bot_lst)} resy restaurants to bot")
    utils.thread_success(f"Loaded {len(resy_monitor_lst)} resy restaurants to monitor")


def config_bots():
    for restaurant in resy_bot_lst:
        drop_start_raw = restaurant["monitor"]["drop"]
        drop_start_t = datetime.strptime(drop_start_raw, "%H:%M:%S").time()
        drop_start_dt = datetime.combine(datetime.now(), drop_start_t, tzinfo=timezone("EST"))
        drop_worker_start_dt = drop_start_dt - timedelta(minutes=WORKER_LAUNCH_TIME)

        # if drop time within 10 minutes we want to start it asap no rocky
        if (drop_worker_start_dt < datetime.now(timezone("EST"))) and (datetime.now(timezone("EST")) < drop_start_dt):
            utils.thread_warn(
                f"Drop time for {restaurant['name']} is within {WORKER_LAUNCH_TIME} minutes, starting bot now"
            )
            init_bot_sch(restaurant)

        drop_worker_start = drop_worker_start_dt.strftime("%H:%M:%S")

        schedule.every().day.at(drop_worker_start, "America/New_York").do(
            init_bot_sch, res_config=restaurant
        )

        utils.thread_log(
            f"Scheduled {restaurant['name']} to start at {drop_worker_start} daily"
        )

    while True:
        schedule.run_pending()
        time.sleep(1)

def init_bot_sch(res_config):
    # initialize the botting flow
    utils.thread_success("Starting bot from scheduler!")
    thread_name = f"Master-{res_config['name']}"
    try:
        discord.logs_wh(f"Starting bot from scheduler: {thread_name}")
    except:
        pass
    res_config["parent"] = "scheduled"
    t = threading.Thread(
        target=master_start_worker,
        args=(res_config,),
        name=thread_name,
    )

    t.start()

def init_bot(res_config):
    # initialize the botting flow
    utils.thread_success("Generic starting bot")
    res_config["parent"] = "unknown"
    thread_name = f"Master-{res_config['name']}"
    t = threading.Thread(
        target=master_start_worker,
        args=(res_config,),
        name=thread_name,
    )

    t.start()

def init_preloader():
    thread_name = "AccountPreloader"
    t = threading.Thread(
        target=start_acc_preloader,
        args=(),
        name=thread_name,
    ).start()

def init_monitors():
    # initialize the monitoring flow
    for restaurant in resy_monitor_lst:
        thread_name = f"MonitorMaster-{restaurant['name']}"
        t = threading.Thread(
            target=master_start_monitor,
            args=(restaurant,),
            name=thread_name
        )
        
        t.start()

def master_start_worker(res_config):
    if "date" not in res_config:
        res_config["date"] = (
            datetime.now() + timedelta(days=res_config["offset"])
        ).strftime("%Y-%m-%d")
    
    if "parent" not in res_config:
        res_config["parent"] = "N/A"
    

    minParty = res_config["partyMin"]
    maxParty = res_config["partyMax"]
    grabmax = res_config["grabMax"]
    utils.thread_log(f"Spinning up {(grabmax * len(range(minParty, maxParty + 1))) * WORKER_CNT} Workers")

    for party_config in range(minParty, maxParty + 1):
        for grab_instance in range(grabmax):
            for worker_i in range(0, WORKER_CNT):
                worker_name = f"{res_config['name'].replace(' ', '-')}:{party_config}:{grab_instance}:{worker_i}:{res_config['date']}"
                t = threading.Thread(
                    target=start_worker,
                    args=(res_config, party_config,),
                    name=worker_name,
                )

                t.start()
                time.sleep(0.1)

def master_start_monitor(res_config):
    minParty = res_config["partyMin"]
    maxParty = res_config["partyMax"]

    for party_config in range(minParty, maxParty + 1):
        for monitor_instance in range(0, MONITOR_WORKERS):
            monitor_name = f"{res_config['name'].replace(' ', '-')}:{party_config}:{monitor_instance}:MONITOR"
            t = threading.Thread(
                target=start_montior,
                args=(res_config, party_config,),
                name=monitor_name,
            )
            
            t.start()
            time.sleep(0.2)


def start_worker(res_config, party_config):
    try:
        Worker(res_config, party_config, parent=res_config['parent']).start_bot()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()

def start_montior(res_config, party_config):
    try:
        Monitor(res_config, party_config).start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()

def start_acc_preloader():
    try:
        AccPreloader()
    except (KeyboardInterrupt, SystemExit):
        sys.exit()


if __name__ == "__main__":
    utils.thread_log("Resy Botting Engine, Booting Up")
    discord.logs_wh("Starting up an instance of the Resy engine")

    # run file init
    file_init()

    # run resy config init
    config_init()

    # run monitors
    init_monitors()
    
    init_preloader()

    # config bots
    config_bots()
