import urllib.request
import urllib.parse
from bs4 import BeautifulSoup, Comment
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import time
import math
import socket
import getopt
import datetime
import re
import statistics
import numbers
import unidecode
from nameparser import HumanName
from urllib.parse import urlparse

mlb_teams_url_format = "https://statsapi.mlb.com/api/v1/teams/{}"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "MLBCompareRedditBot"
}

def main():
    team_venues = {}

    for id_val in range(1, 806):
        request = urllib.request.Request(mlb_teams_url_format.format(id_val), headers=request_headers)
        try:
            response = url_request(request)
        except urllib.error.HTTPError as err:
            if err.status == 404:
                print(id_val)
                continue
            else:
                raise

        data = json.load(response)
        for team in data["teams"]:
            if team["sport"]["id"] == 1 and "name" in team["league"]:
                venue_id = team["venue"]["id"]
                team_name = unidecode.unidecode(team["venue"]["name"])

                team_venues[venue_id] = team_name

        request = urllib.request.Request(mlb_teams_url_format.format(id_val) + "/history", headers=request_headers)
        try:
            response = url_request(request)
        except urllib.error.HTTPError as err:
            if err.status == 404:
                print(id_val)
                continue
            else:
                raise

        data = json.load(response)
        for team in data["teams"]:
            if team["sport"]["id"] == 1 and "name" in team["league"]:
                venue_id = team["venue"]["id"]
                if venue_id not in team_venues:
                    team_name = unidecode.unidecode(team["venue"]["name"])

                    team_venues[venue_id] = team_name

        print(id_val)

    with open("team_venues.json", "w") as file:
        file.write(json.dumps(team_venues, indent=4, sort_keys=True))

def url_request(request):
    failed_counter = 0
    while(True):
        try:
            return urllib.request.urlopen(request)
        except urllib.error.HTTPError as err:
            if err.status == 404:
                raise
            failed_counter += 1
            if failed_counter > max_request_retries:
                raise
        except urllib.error.URLError:
            failed_counter += 1
            if failed_counter > max_request_retries:
                raise

        delay_step = 10
        print("Retrying in " + str(retry_failure_delay) + " seconds to allow fangraphs to chill")
        time_to_wait = int(math.ceil(float(retry_failure_delay)/float(delay_step)))
        for i in range(retry_failure_delay, 0, -time_to_wait):
            print(i)
            time.sleep(time_to_wait)
        print("0")

if __name__ == "__main__":
    main()