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
import unidecode

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

def main():
    team_info = {}
    team_abr = {}
    team_name_info = {}
    team_main_abbr = {}

    request = urllib.request.Request(hockeyref_team_ids_url, headers=request_headers)
    try:
        response = url_request(request)
    except urllib.error.HTTPError as err:
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
                            team_abbr = team_link["href"].split("/")[2].upper()
                            request = urllib.request.Request("https://www.hockey-reference.com" + team_link["href"], headers=request_headers)
                            try:
                                response = url_request(request)
                            except urllib.error.HTTPError as err:
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
                                            sub_team_row_abbr = sub_team_row.find("a")["href"].split("/")[2].upper()
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

    for id_val in range(1, 102):
        request = urllib.request.Request(awards_url_format.format(id_val), headers=request_headers)
        try:
            response = url_request(request)
        except urllib.error.HTTPError as err:
            if err.status == 404:
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
