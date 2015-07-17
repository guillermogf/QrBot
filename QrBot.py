#!/usr/bin/python
# coding: utf-8

# 2015 © Guillermo Gómez Fonfría <guillermo.gf@openmailbox.org>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import urllib2
import sys
import os
import json
import requests
import subprocess


# Load Token
try:
    token_file = open("token")
except:
    print("Token file missing")
    sys.exit(1)

token = token_file.read().rstrip("\n")
token_file.close()

# Telegram API urls
api_url = "https://api.telegram.org/bot"
token_url = api_url + token
getupdates_url = token_url + "/getUpdates"
sendmessage_url = token_url + "/sendMessage"
sendimage_url = token_url + "/sendPhoto"

# Messages content
start_text = "Hi!\nThis bot creates a Qr code containing the text you want\n"

help_text = "List of available commands:\n/help Shows this list of available \
commands\n/qr <your text>Creates a Qr code using the input text."

error_unknown = "Unknown command\n"


def get_input_text(message):
    message = message.split(" ")
    if "/qr@BechdelBot" in message:
        message.remove("/qr@BechdelBot")
    elif "/qr" in message:
        message.remove("/qr")

    input_text = " ".join(message)
    return input_text


def generate_image(message):
    exit_code = subprocess.call(["qrencode", "-s", "5", message, "-o", "/tmp/qrcode.png"])
    if exit_code != 0:
        print("Qr encode failed. Exit code {0}".format(exit_code))
        sys.exit(1)
    return "/tmp/qrcode.png"


while True:
    # Load last update
    try:
        last_update_file = open("lastupdate")
        last_update = last_update_file.read().rstrip("\n")
        last_update_file.close()
    except:
        last_update = "0"  # If lastupdate file not present, read all updates

    getupdates_offset_url = getupdates_url + "?offset=" + str(int(last_update)
                                                              + 1)

    get_updates = requests.get(getupdates_offset_url)
    if get_updates.status_code != 200:
        print(get_updates.status_code)  # For debugging
        continue
    else:
        updates = json.loads(get_updates.content)["result"]

    for item in updates:
        if int(last_update) >= item["update_id"]:
            continue
        # Store last update
        last_update_file = open("lastupdate", "w")
        last_update_file.write(str(item["update_id"]))
        last_update_file.close()

        # Group's status messages don't include "text" key
        try:
            tmp = item["message"]["text"]
        except KeyError:
            continue

        if "/start" == item["message"]["text"]:
            message = requests.get(sendmessage_url + "?chat_id=" +
                                   str(item["message"]["chat"]["id"]) +
                                   "&text=" + start_text + help_text)
        elif "/help" in item["message"]["text"]:
            message = requests.get(sendmessage_url + "?chat_id=" +
                                   str(item["message"]["chat"]["id"]) +
                                   "&text=" + help_text)
        elif "/qr" in item["message"]["text"]:
            message = get_input_text(item["message"]["text"])
            if message == "":
                message = requests.get(sendmessage_url + "?chat_id=" +
                                       str(item["message"]["chat"]["id"]) +
                                       "&text=Write what you want to encode \
                                       after /qr")
                continue
            path = generate_image(message)
            data = {"chat_id": str(item["message"]["chat"]["id"])}
            files = {"photo": (path, open(path, "rb"))}
            requests.post(sendimage_url, data=data, files=files)
            os.remove(path)
        elif item["message"]["chat"]["id"] < 0:
            # If it is none of the above and it's a group, let's guess it was
            # for another bot rather than sending the unknown command message
            continue
        else:
            message = requests.get(sendmessage_url + "?chat_id=" +
                                   str(item["message"]["chat"]["id"]) +
                                   "&text=" + error_unknown + help_text)
