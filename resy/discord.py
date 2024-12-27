import time
from datetime import datetime, timedelta
from discord_webhook import DiscordWebhook, DiscordEmbed
from utils import Utils
import os
from random import randint
import sys

utils = Utils()


class Discord:
    def __init__(self):
        self.webhook_url = ""
        self.logs_webhook_url = ""

        if not os.getenv("WEBHOOK_URL"):
            utils.thread_warn("Not sending discord webhooks, please set .env")
        else:
            self.webhook_url = os.getenv("WEBHOOK_URL")

        if not os.getenv("LOGS_WEBHOOK_URL"):
            utils.thread_error("No logs webhook found")
        else:
            self.logs_webhook_url = os.getenv("LOGS_WEBHOOK_URL")

    def successful_book_wh(self, res_config, party_size):
        if self.webhook_url is not None:
            webhook = DiscordWebhook(url=self.webhook_url)

            embed = DiscordEmbed(
                title="ResMe Engine",
                description=f"New {res_config['name']} Reservation!",
                color="ff38b6",
            )

            embed.set_footer(text=f"Secured @ {datetime.now()}")

            embed.add_embed_field(name="Venue Name", value=res_config["name"])
            embed.add_embed_field(name="Date", value=res_config["date"])
            embed.add_embed_field(name="Party Size", value=party_size)
            embed.add_embed_field(name="Time", value=res_config["res_time"])

            webhook.add_embed(embed)
            
            try:
                webhook.execute()
            except:
                utils.thread_error("Error sending discord webhook")

    def logs_wh(self, message):
        if self.logs_webhook_url is not None:
            webhook = DiscordWebhook(url = self.logs_webhook_url)

            embed = DiscordEmbed(
                title="ResMe System Robot",
                description="New ResMe System Notification",
                color="00f2ff",
            )
            
            embed.set_footer(text=f"Sent @ {datetime.now()}")
            
            embed.add_embed_field(name="Message", value=message)
            
            webhook.add_embed(embed)
            
            webhook.execute()
