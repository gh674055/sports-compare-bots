import requests
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
import requests
import threading

mlb_teams_url_format = "https://statsapi.mlb.com/api/v1/schedule?&season={}&sportId=1&gameType=R,F,D,L,W"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "MLBCompareRedditBot"
}

request_headers= {}

end_year = 2022

country_codes = { 
    "USA" : "US",
    "Canada" : "CA",
    "Japan" : "JP",
    "Puerto Rico" : "PR",
    "Mexico" : "MX",
    "Australia" : "AU",
    "United Kingdom" : "UK"
}

def main():
    year_short = "y"
    year_long = "year"
    try:
        options = getopt.getopt(sys.argv[1:], year_short + ":", [year_long + "="])[0]
    except getopt.GetoptError as err:
        print("Encountered error \"" + str(err) + "\" parsing arguments")
        return
    
    year = None
    for opt, arg in options:
        if opt in ("-" + year_short, "--" + year_long):
            year = int(arg.strip())

    totals = None
    if year:
        with open("team_venues.json", "r") as file:
            team_venues = json.load(file)
    else:
        team_venues = {}

    with requests.Session() as s:
        for sub_year in range(1901, end_year + 1):
            if year and sub_year != year:
                continue

            data = url_request_json(s, mlb_teams_url_format.format(sub_year))
            for date in data["dates"]:
                for game in date["games"]:
                    team_name = unidecode.unidecode(game["venue"]["name"]).strip()
                    venue_id = str(game["venue"]["id"])

                    if venue_id not in team_venues:
                        try:
                            sub_data = url_request_json(s, "https://statsapi.mlb.com" + game["link"])
                        except requests.exceptions.HTTPError as err:
                            if err.response.status_code == 404:
                                continue
                            else:
                                raise

                        if "message" in sub_data:
                            continue

                        team_venues[venue_id] = {
                            "values" : [],
                            "city" : sub_data["gameData"]["venue"]["location"]["city"].strip() if "city" in sub_data["gameData"]["venue"]["location"] else None,
                            "state" : sub_data["gameData"]["venue"]["location"]["stateAbbrev"].strip() if "stateAbbrev" in sub_data["gameData"]["venue"]["location"] else None,
                            "country" : country_codes[sub_data["gameData"]["venue"]["location"]["country"]].strip() if "country" in sub_data["gameData"]["venue"]["location"] else None,
                            "time_zone" : sub_data["gameData"]["venue"]["timeZone"]["id"].strip()
                        }
                    if team_name not in team_venues[venue_id]["values"]:
                        team_venues[venue_id]["values"].append(team_name.strip())

            print(sub_year)

    with open("team_venues.json", "w") as file:
        file.write(json.dumps(team_venues, indent=4, sort_keys=True))

def url_request(url, timeout=30):
    failed_counter = 0
    while(True):
        try:
            response = requests.get(url, timeout=timeout, headers=request_headers)
            response.raise_for_status()
            text = response.text

            bs = BeautifulSoup(text, "lxml")
            if not bs.contents:
                raise requests.exceptions.HTTPError("Page is empty!")
            return response, bs
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 403:
                raise
            else:
                failed_counter += 1
                if failed_counter > max_request_retries:
                    raise
        except Exception:
            failed_counter += 1
            if failed_counter > max_request_retries:
                raise

        delay_step = 10
        print("#" + str(threading.get_ident()) + "#   " + "Retrying in " + str(retry_failure_delay) + " seconds to allow request to " + url + " to chill")
        time_to_wait = int(math.ceil(float(retry_failure_delay)/float(delay_step)))
        for i in range(retry_failure_delay, 0, -time_to_wait):
            print("#" + str(threading.get_ident()) + "#   " + str(i))
            time.sleep(time_to_wait)
        print("#" + str(threading.get_ident()) + "#   " + "0")

if __name__ == "__main__":
    main()