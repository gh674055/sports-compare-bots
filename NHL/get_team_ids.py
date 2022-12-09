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
import threading
from requests_ip_rotator import ApiGateway
from urllib.parse import urlparse, parse_qs

awards_url_format = "https://statsapi.web.nhl.com/api/v1/teams/{}"
hockeyref_team_ids_url = "https://www.hockey-reference.com/teams"

max_request_retries = 3
retry_failure_delay = 3

award_results = {}

manual_mappings = {
    "Quebec Athletic Club/Bulldogs" : "Quebec Bulldogs",
    "Chicago Black Hawks" : "Chicago Blackhawks",
    "Mighty Ducks of Anaheim" : "Anaheim Ducks",
}

request_headers = {
    "User-Agent" : "NHLCompareRedditBot"
}

request_headers= {}

def main():
    team_info = {}
    team_abr = {}
    team_name_info = {}
    team_main_abbr = {}
    team_venue_history = {}

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
                            team_abbr = team_link["href"].split("/")[2].upper()
                            try:
                                response = url_request("https://www.hockey-reference.com" + team_link["href"])
                            except requests.exceptions.HTTPError as err:
                                raise

                            sub_player_page = BeautifulSoup(response, "html.parser")
                            sub_table = sub_player_page.find("table", id=team_abbr)
                            if not sub_table:
                                sub_comments = sub_player_page.find_all(string=lambda text: isinstance(text, Comment))
                                for c in sub_comments:
                                    temp_soup = BeautifulSoup(c, "html.parser")
                                    temp_table = temp_soup.find("table", id=team_abbr)
                                    if temp_table:
                                        sub_table = temp_table
                                        break
                            
                            if sub_table:
                                sub_standard_table_rows = sub_table.find("tbody").find_all("tr")
                                for sub_row in sub_standard_table_rows:
                                    if not sub_row.get("class") or not "thead" in sub_row.get("class"):
                                        sub_team_row = sub_row.find("td", {"data-stat" : "team_name"})
                                        if sub_team_row:
                                            sub_team_row_link = sub_team_row.find("a")["href"]
                                            sub_team_row_abbr = sub_team_row_link.split("/")[2].upper()
                                            sub_team_row_name = sub_team_row.find(text=True)
                                            if sub_team_row_name in manual_mappings:
                                                sub_team_row_name = manual_mappings[sub_team_row_name]

                                            sub_team_row_year = int(re.sub("[^0-9]", "", sub_row.find("th").find(text=True).split("-")[0]))

                                            if str(sub_team_row_year) not in team_main_abbr:
                                                team_main_abbr[str(sub_team_row_year)] = {}
                                            team_main_abbr[str(sub_team_row_year)][sub_team_row_abbr] = overall_team_abbr
                                            
                                            if sub_team_row_name == "Winnipeg Jets":
                                                if sub_team_row_year < 2011:
                                                    sub_team_row_name = "Winnipeg Jets (1979)"
                                            elif sub_team_row_name == "Ottawa Senators":
                                                if sub_team_row_year < 1992:
                                                    sub_team_row_name = "Ottawa Senators (1917)"

                                            if sub_team_row_name not in team_name_info:
                                                team_name_info[sub_team_row_name] = {}
                                            if sub_team_row_abbr not in team_name_info[sub_team_row_name]:
                                                team_name_info[sub_team_row_name][sub_team_row_abbr] = []
                                            if sub_team_row_year not in team_name_info[sub_team_row_name][sub_team_row_abbr]:
                                                team_name_info[sub_team_row_name][sub_team_row_abbr].append(sub_team_row_year)
                                            

                                            try:
                                                response = url_request("https://www.hockey-reference.com" + sub_team_row_link)
                                            except requests.exceptions.HTTPError:
                                                raise

                                            sub_sub_player_page = BeautifulSoup(response, "html.parser")

                                            team_info_dir = sub_sub_player_page.find("div", {"id" : "meta"})
                                            if team_info_dir:
                                                stadium_item = team_info_dir.find("strong", text="Primary Arena:")
                                                if stadium_item:
                                                    stadium_parent = stadium_item.parent
                                                    if stadium_parent:
                                                        stadium_link = stadium_parent.find("a")
                                                        if stadium_link:
                                                            stadium_id = stadium_link["href"].split("/")[2][:-5]
                                                            
                                                            if overall_team_abbr not in team_venue_history:
                                                                team_venue_history[overall_team_abbr] = {}
                                                            if stadium_id not in team_venue_history[overall_team_abbr]:
                                                                team_venue_history[overall_team_abbr][stadium_id] = []
                                                            if sub_team_row_year not in team_venue_history[overall_team_abbr][stadium_id]:
                                                                team_venue_history[overall_team_abbr][stadium_id].append(sub_team_row_year)

    for id_val in range(1, 102):
        try:
            response = url_request(awards_url_format.format(id_val))
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                continue
            else:
                raise

        data = json.load(response)

        team = unidecode.unidecode(data["teams"][0]["name"])
        if team not in team_name_info:
            print("Skipping NHL team : " + team + " (" + str(id_val) + ")")
            continue

        abbr = unidecode.unidecode(data["teams"][0]["abbreviation"])
        team_info[team] = id_val
        team_abr[abbr] = team
    
    with open("team_ids.json", "w") as file:
        file.write(json.dumps(team_info, indent=4, sort_keys=True))
    
    with open("team_abr.json", "w") as file:
        file.write(json.dumps(team_abr, indent=4, sort_keys=True))

    with open("team_name_info.json", "w") as file:
        file.write(json.dumps(team_name_info, indent=4, sort_keys=True))

    with open("team_main_abbr.json", "w") as file:
        file.write(json.dumps(team_main_abbr, indent=4, sort_keys=True))

    with open("team_venue_history.json", "w") as file:
        file.write(json.dumps(team_venue_history, indent=4, sort_keys=True))

def url_request(url, timeout=30, allow_403_retry=True):
    failed_counter = 0
    gateway_session = requests.Session()
    gateway_session.mount("https://www.hockey-reference.com", gateway)
    while(True):
        try:
            response = gateway_session.get(url, timeout=timeout, headers=request_headers)
            response.raise_for_status()
            return response.content
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 403 and allow_403_retry:
                error_string = str(err)
                if error_string.startswith("403 Client Error: Forbidden for url:"):
                    error_split = str(err).split()
                    error_url = error_split[len(error_split) - 1]
                    new_url = "https://www.hockey-reference.com" + urlparse(error_url).path
                    new_url = new_url.replace("/ProxyStage", "")
                    return url_request(new_url, timeout, allow_403_retry=False)
                else:
                    failed_counter += 1
                    if failed_counter > max_request_retries:
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
    global gateway
    with ApiGateway("https://www.hockey-reference.com", verbose=False) as gateway:
        main()
