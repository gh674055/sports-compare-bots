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
import atexit

nfl_venue_ids_url = "https://www.pro-football-reference.com/stadiums"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "NFLCompareRedditBot"
}

request_headers= {}

gateway = ApiGateway("https://www.pro-football-reference.com", verbose=False)
gateway.start()

gateway_session = requests.Session()
gateway_session.mount("https://www.pro-football-reference.com", gateway)

def exit_handler():
    gateway.shutdown()

atexit.register(exit_handler)

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

def url_request(url, timeout=30):
    failed_counter = 0
    while(True):
        try:
            response = gateway_session.get(url, timeout=timeout, headers=request_headers)
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
    main()