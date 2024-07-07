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
import threading
from nameparser import HumanName
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from requests_ip_rotator import ApiGateway
import urllib.parse
from urllib.parse import urlparse, parse_qs
import signal

nfl_venue_ids_url = "https://www.pro-football-reference.com/stadiums"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "NFLCompareRedditBot"
}

request_headers= {}

def main():
    id_val = 1
    team_venues = {}

    geolocator = Nominatim(user_agent="NFLCompareRedditBot")
    tz_finder = TimezoneFinder()

    try:
        response = url_request(nfl_venue_ids_url)
    except requests.exceptions.HTTPError:
        raise

    player_page = BeautifulSoup(response, "html.parser")

    table_names = ["stadiums"]
    comments = None
    for table_name in table_names:
        table = player_page.find("table", id=table_name)
        if not table:
            if not comments:
                comments = player_page.find_all(string=lambda text: isinstance(text, Comment))
            for c in comments:
                temp_soup = BeautifulSoup(c, "html.parser")
                temp_table = temp_soup.find("table", id=table_name)
                if temp_table:
                    table = temp_table
                    break

        if table:
            standard_table_rows = table.find("tbody").find_all("tr")
            for row in standard_table_rows:
                if not row.get("class"):
                    venue_row = row.find("th", {"data-stat" : "stadium_name"})
                    current_name = str(venue_row.find(text=True))
                    city = str(row.find("td", {"data-stat" : "city"}).find(text=True))
                    state = str(row.find("td", {"data-stat" : "state"}).find(text=True))
                    if state == "Mani":
                        state = "MB"

                    if state in ["UK"]:
                        country = "UK"
                        state = None
                    elif state in ["MX"]:
                        country = "MX"
                        state  = None
                    elif state in ["ON", "MB"]:
                        country = "CA"
                    else:
                        country = "US"

                    if state:
                        state_to_use = state
                        if state == "CT":
                            state_to_use = "Connecticut"
                        location = geolocate(geolocator, city + " " + state_to_use + " " + country)
                    else:
                        location = geolocate(geolocator, city + " " + country)

                    time_zone = tz_finder.timezone_at(lng=location.longitude, lat=location.latitude)

                    venue_link = venue_row.find("a")
                    venue_id = venue_link["href"].split("/")[2][:-4].upper()
                    try:
                        response = url_request(nfl_venue_ids_url)
                    except requests.exceptions.HTTPError:
                        raise

                    sub_player_page = BeautifulSoup(response, "html.parser")
                    meta_tag = sub_player_page.find("div", id="meta")
                    if not meta_tag:
                        sub_comments = sub_player_page.find_all(string=lambda text: isinstance(text, Comment))
                        for c in sub_comments:
                            temp_soup = BeautifulSoup(c, "html.parser")
                            temp_table = temp_soup.find("div", id="meta")
                            if temp_table:
                                meta_tag = temp_table
                                break

                    paragraphs = meta_tag.find_all("p")
                    venues = [current_name.strip()]
                    for paragraph in paragraphs:
                        paragraph_text = str(paragraph.find(text=True))
                        if paragraph_text.startswith("Known As:"):
                            paragraph.find("b").decompose()
                            paragraph_text = str(paragraph.find(text=True)).strip()
                            text_split = paragraph_text.split(",")
                            for venue_text in text_split:
                                venue_name = re.search(r"(.+) \(\d{4}-\d{4}\)", venue_text.strip()).group(1).strip()
                                if venue_name not in venues:
                                    venues.append(venue_name.strip())
                            break

                    if not city or not country or not time_zone or not venues:
                        print("Invalid arena " + venue_id)

                    team_venues[venue_id] = {
                        "city" : city.strip(),
                        "state" : state.strip() if state else None,
                        "country" : country.strip(),
                        "time_zone" : time_zone.strip(),
                        "venues" : venues
                    }

                    print(venue_id)
    
    with open("team_venues.json", "w") as file:
        file.write(json.dumps(team_venues, indent=4, sort_keys=True))

def url_request(url, timeout=30, retry_403=True):
    gateway_session = requests.Session()
    gateway_session.mount("https://www.pro-football-reference.com", gateway)
    failed_counter = 0
    while(True):
        try:
            response = gateway_session.get(url, timeout=timeout, headers=request_headers)
            response.raise_for_status()
            text = response.content

            bs = BeautifulSoup(text, "lxml")
            if not bs.contents:
                raise requests.exceptions.HTTPError("Page is empty!")
            return response, bs
        except requests.exceptions.HTTPError as e:
            if retry_403 and url.startswith("https://www.pro-football-reference.com/") and not response.url.startswith("https://www.pro-football-reference.com/"):
                url_parsed = urlparse(response.url)
                path = url_parsed.path[1:].split("/")[0]
                if path != "ProxyStage":
                    replaced = url_parsed._replace(path="/ProxyStage" + url_parsed.path)
                    rebuilt_url = urllib.parse.urlunparse(replaced)
                    logger.info("#" + str(threading.get_ident()) + "#   " + "Rebuilt URL on 403 and retrying from " + response.url + " to " + rebuilt_url)
                    return url_request(rebuilt_url, timeout=timeout, retry_403=False)
                else:
                    failed_counter += 1
                    if failed_counter > max_request_retries:
                        raise
            else:
                failed_counter += 1
                if failed_counter > max_request_retries:
                    raise
        except Exception as e:
            failed_counter += 1
            if failed_counter > max_request_retries:
                raise
        
        delay_step = 10
        logger.info("#" + str(threading.get_ident()) + "#   " + "Retrying in " + str(retry_failure_delay) + " seconds to allow request to " + url + " to chill")
        time_to_wait = int(math.ceil(float(retry_failure_delay)/float(delay_step)))
        for i in range(retry_failure_delay, 0, -time_to_wait):
            logger.info("#" + str(threading.get_ident()) + "#   " + str(i))
            time.sleep(time_to_wait)
        logger.info("#" + str(threading.get_ident()) + "#   " + "0")

def geolocate(geolocator, location):
    failed_counter = 0
    while(True):
        try:
            return geolocator.geocode(location, timeout=30)
        except Exception:
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
    global gateway
    gateway =  ApiGateway("https://www.pro-football-reference.com", verbose=True)
    endpoints = gateway.start(force=True)

    def exit_gracefully(signum, frame):
        sys.exit(signum)
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    try:
        main()
    finally:
        gateway.shutdown(endpoints)