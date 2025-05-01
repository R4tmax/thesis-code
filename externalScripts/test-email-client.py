# TODO: Figure out, how to correctly pass this as ENV variable on GCP
import os
import requests


def send_simple_message():
    return requests.post(
        "https://api.mailgun.net/v3/sandbox24b32b935d29466eb58b1de94ff343ff.mailgun.org/messages",
        auth=("api", ''), # be sure to hide API key for commits
        data={"from": "Mailgun Sandbox <postmaster@sandbox24b32b935d29466eb58b1de94ff343ff.mailgun.org>",
              "to": "Martin Kadlec <kadlec.m.90@gmail.com>",
              "subject": "Hello Martin Kadlec",
              "text": "Congratulations Martin Kadlec, you just sent an email with Mailgun! You are truly awesome!"})



print(send_simple_message())