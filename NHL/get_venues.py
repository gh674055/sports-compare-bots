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
import unidecode
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import threading
from requests_ip_rotator import ApiGateway
import urllib.parse
from urllib.parse import urlparse, parse_qs
import signal

hockeyref_team_ids_url = "https://www.hockey-reference.com/teams"
nhl_teams_url_format = "https://statsapi.web.nhl.com/api/v1/schedule?&season={}&gameType=R,P"

max_request_retries = 3
retry_failure_delay = 3

award_results = {}

request_headers = {
    "User-Agent" : "NHLCompareRedditBot"
}

request_headers= {}

manual_venue_map = {
    "The Arena" : "Laurier Avenue Arena",
    "Montreal Arena" : "Westmount Arena",
    "Jubilee Arena" : "Jubilee Rink",
    "Madison Square Garden (III)" : "Madison Square Garden III",
    "Madison Square Garden (IV)" : "Madison Square Garden",
    "Boardwalk Hall" : "Atlantic City Auditorium",
    "Fairgrounds Coliseum" : "Indiana State Fairgrounds Coliseum",
    "Pittsburgh Civic Arena" : "Civic Arena",
    "Long Beach Convention Center" : "Long Beach Arena",
    "The Spectrum" : "Spectrum",
    "Quebec Coliseum" : "Le Colisee",
    "Capital Center" : "Capital Centre",
    "Coliseum at Richfield" : "Richfield Coliseum",
    "Civic Centre Arena" : "Ottawa Civic Centre",
    "Saskatchewan Place" : "SaskPlace",
    "Arrowhead Pond of Anaheim" : "Arrowhead Pond",
    "Molson Centre" : "Centre Molson",
    "O2 World": "O2 Arena Berlin",
    "Raleigh Entertainment & Sports Arena" : "Entertainment and Sports Arena",
    "Bell Centre" : "Centre Bell",
    "TD Place Stadium" : "Lansdowne Park",
    "Cotton Bowl" : "Cotton Bowl Stadium",
    "The O2 Arena" : "O2 Arena"
}

extra_names = {
    "amalie-arena": [
        "O-Rena"
    ],
    "canadian-tire-centre" : [
        "The Palladium"
    ],
    "commonwealth-stadium" : [
        "Commonwealth Stadium, Edmonton"
    ],
    "ericsson-globe-arena" : [
        "Globe Arena"
    ],
    "bmo-field" : [
        "Exhibition Stadium"
    ],
    "nassau-veterans-memorial-coliseum" : [
        "NYCB Live/Nassau Coliseum"
    ],
    "bbt-center" : [
        "FLA Live Arena"
    ],
    "metropolitan-sports-center" : [
        "Met Center"
    ],
    "great-western-forum" : [
        "The Forum"
    ],
    "staples-center" : [
        "Crypto.com Arena"
    ]
}

manual_arenas = {
    "seattle-ice-arena" : {
        "city": "Seattle",
        "country": "US",
        "state": "WA",
        "time_zone": "America/Los_Angeles",
        "venues": [
            "Seattle Ice Arena"
        ]
    },
    "denman-arena": {
        "city": "Vancouver",
        "country": "CA",
        "state": "BC",
        "time_zone": "America/Vancouver",
        "venues": [
            "Denman Arena"
        ]
    },
    "patrick-arena": {
        "city": "Victoria",
        "country": "CA",
        "state": "BC",
        "time_zone": "America/Vancouver",
        "venues": [
            "Patrick Arena"
        ]
    },
    "saitama-super-arena": {
        "city": "Saitama",
        "country": "JP",
        "state": "Kanto",
        "time_zone": "Asia/Tokyo",
        "venues": [
            "Saitama Super Arena"
        ]
    },
    "target-field": {
        "city": "Minnesota",
        "country": "US",
        "state": "MN",
        "time_zone": "America/Chicago",
        "venues": [
            "Target Field"
        ]
    },
    "bridgestone-arena": {
        "city": "Nashville",
        "country": "US",
        "state": "TN",
        "time_zone": "America/Chicago",
        "venues": [
            "Bridgestone Arena",
            "Gaylord Entertainment Center",
            "Nashville Arena",
            "Sommet Center"
        ]
    },
    "nissan-stadium": {
        "city": "Nashville",
        "country": "US",
        "state": "TN",
        "time_zone": "America/Chicago",
        "venues": [
            "Nissan Stadium"
        ]
    },
    "tim-hortons-field": {
        "city": "Hamilton",
        "country": "CA",
        "state": "ON",
        "time_zone": "America/Toronto",
        "venues": [
            "Tim Hortons Field"
        ]
    },
}

do_check = True
end_year = 2022

def main():
    team_venues = {}
    
    geolocator = Nominatim(user_agent="NHLCompareRedditBot")
    tz_finder = TimezoneFinder()

    try:
        response = url_request(hockeyref_team_ids_url)
    except requests.exceptions.HTTPError as err:
        raise

    player_page = BeautifulSoup(response, "html.parser")

    table_names = ["active_franchises", "defunct_franchises"]
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
                if row.get("class") and "full_table" in row.get("class"):
                    if row.find("td", {"data-stat" : "lg_id"}).find(text=True) == "NHL":
                        team_link = row.find("th", {"data-stat" : "franch_name"}).find("a")
                        if team_link:
                            overall_team_abbr = team_link["href"].split("/")[2].upper()
                            print(overall_team_abbr)
                            try:
                                response = url_request("https://www.hockey-reference.com/teams/" + overall_team_abbr + "/head2head.html")
                            except requests.exceptions.HTTPError as err:
                                raise

                            sub_player_page = BeautifulSoup(response, "html.parser")
                            sub_table = sub_player_page.find("table", id="arenas")
                            if not sub_table:
                                sub_comments = sub_player_page.find_all(string=lambda text: isinstance(text, Comment))
                                for c in sub_comments:
                                    temp_soup = BeautifulSoup(c, "html.parser")
                                    temp_table = temp_soup.find("table", id="arenas")
                                    if temp_table:
                                        sub_table = temp_table
                                        break
                            
                            if sub_table:
                                sub_standard_table_rows = sub_table.find("tbody").find_all("tr")
                                for sub_row in sub_standard_table_rows:
                                    if not sub_row.get("class") or not "thead" in sub_row.get("class"):
                                        arena_link = sub_row.find("th", {"data-stat" : "arena_name"}).find("a")
                                        arena_id = arena_link["href"].split("/")[2][:-5]
                                        if arena_id not in team_venues:
                                            arena_location = str(sub_row.find("td", {"data-stat" : "location"}).find(text=True))
                                            arena_names = arena_link["title"].split(",")
                                            for index, value in enumerate(arena_names):
                                                if value in manual_venue_map:
                                                    arena_names[index] = manual_venue_map[value]
                                            
                                            if arena_id in extra_names:
                                                for pot_arena in extra_names[arena_id]:
                                                    if pot_arena not in arena_names:
                                                        arena_names.append(pot_arena)

                                            if arena_location == "Cincinatti, OH":
                                                arena_location = "Cincinnati, OH"
                                            elif arena_location == "Gothenberg":
                                                arena_location = "Gothenburg"

                                        
                                            location = geolocate(geolocator, arena_location)

                                            time_zone = tz_finder.timezone_at(lng=location.longitude, lat=location.latitude)

                                            loc_split = arena_location.split(",")
                                            country = None
                                            state = None
                                            city = None

                                            if len(loc_split) == 1:
                                                city = loc_split[0].strip()
                                                if city == "Tokyo":
                                                    country = "JP"
                                                elif city == "Stockholm":
                                                    country = "SE"
                                                elif city == "Gothenburg":
                                                    country = "SE"
                                                elif city == "London":
                                                    country = "UK"
                                                elif city == "Prague":
                                                    country = "CZ"
                                                elif city == "Helsinki":
                                                    country = "FI"
                                                elif city == "Berlin":
                                                    country = "DE"
                                            else:
                                                city = loc_split[0].strip()
                                                state = loc_split[1].strip()
                                                if state in ["AB", "BC", "MB", "NB", "NL", "NT", "NS", "NU", "ON", "PE", "QC", "SK", "YT"]:
                                                    country = "CA"
                                                else:
                                                    country = "US"

                                            for index, arena_name in enumerate(arena_names):
                                                if arena_name == "O2 Arena":
                                                    if country == "CZ":
                                                        arena_names[index] = "O2 Czech Republic"

                                            for index, arena_name in enumerate(arena_names):
                                                arena_names[index] = arena_name.strip()

                                            if not city or not country or not time_zone or not arena_names:
                                                print("Invalid Arena " + arena_id)
                                            
                                            team_venues[arena_id] = {
                                                "city" : city.strip(),
                                                "state" : state.strip() if state else None,
                                                "country" : country.strip(),
                                                "time_zone" : time_zone.strip(),
                                                "venues" : arena_names
                                            }


    for arena_id in manual_arenas:
        team_venues[arena_id] = manual_arenas[arena_id]
    
    if do_check:
        parsed_venues = set()
        for sub_year in range(1917, end_year + 1):
            print(sub_year)
            year_str = str(sub_year)
            year_str += str(sub_year + 1)

            response = url_request(nhl_teams_url_format.format(year_str))

            data = json.load(response)
            for date in data["dates"]:
                for game in date["games"]:
                    team_name = unidecode.unidecode(game["venue"]["name"]).strip()

                    if team_name not in parsed_venues:
                        has_one_match = False
                        has_multiple_match = False
                        for arena_id in team_venues:
                            if team_name in team_venues[arena_id]["venues"]:
                                if has_one_match:
                                    has_multiple_match = True
                                has_one_match = True

                        if not has_one_match:
                            print("No match for venue " + team_name + " on " + str(game["gamePk"]))
                        elif has_multiple_match:
                            print("Multiple matches for venue " + team_name + " on " + str(game["gamePk"]))
                        parsed_venues.add(team_name)

    with open("team_venues.json", "w") as file:
        file.write(json.dumps(team_venues, indent=4, sort_keys=True))

def url_request(url, timeout=30, retry_403=True):
    gateway_session = requests.Session()
    gateway_session.mount("https://www.hockey-reference.com", gateway)
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
            if retry_403 and url.startswith("https://www.hockey-reference.com/") and not response.url.startswith("https://www.hockey-reference.com/"):
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
    gateway =  ApiGateway("https://www.hockey-reference.com", verbose=True)
    endpoints = gateway.start(force=True)

    def exit_gracefully(signum, frame):
        sys.exit(signum)
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    try:
        main()
    finally:
        gateway.shutdown(endpoints)
