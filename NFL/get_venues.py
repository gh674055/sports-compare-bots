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
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

nfl_venue_ids_url = "https://www.pro-football-reference.com/stadiums"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "NFLCompareRedditBot"
}

def main():
    id_val = 1
    team_venues = {}

    geolocator = Nominatim(user_agent="NFLCompareRedditBot")
    tz_finder = TimezoneFinder()

    request = urllib.request.Request(nfl_venue_ids_url, headers=request_headers)
    try:
        response = url_request(request)
    except urllib.error.HTTPError:
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
                        country = "England"
                    elif state in ["MX"]:
                        country = "Mexico"
                    elif state in ["ON", "Mani"]:
                        country = "Canada"
                    else:
                        country = "USA"

                    location = geolocator.geocode(city + " " + state + " " + country)

                    time_zone = tz_finder.timezone_at(lng=location.longitude, lat=location.latitude)

                    venue_link = venue_row.find("a")
                    venue_id = venue_link["href"].split("/")[2][:-4].upper()
                    request = urllib.request.Request(nfl_venue_ids_url + "/" + venue_id + ".htm", headers=request_headers)
                    try:
                        response = url_request(request)
                    except urllib.error.HTTPError:
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
                    venues = [current_name]
                    for paragraph in paragraphs:
                        paragraph_text = str(paragraph.find(text=True))
                        if paragraph_text.startswith("Known As:"):
                            paragraph.find("b").decompose()
                            paragraph_text = str(paragraph.find(text=True)).strip()
                            text_split = paragraph_text.split(",")
                            for venue_text in text_split:
                                venue_name = re.search(r"(.+) \(\d{4}-\d{4}\)", venue_text.strip()).group(1).strip()
                                if venue_name not in venues:
                                    venues.append(venue_name)
                            break

                    team_venues[venue_id] = {
                        "city" : city,
                        "state" : state,
                        "country" : country,
                        "time_zone" : time_zone,
                        "venues" : venues
                    }

                    print(venue_id)
    
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