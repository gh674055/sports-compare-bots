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

footballref_team_ids_url = "https://www.pro-football-reference.com/teams"

max_request_retries = 3
retry_failure_delay = 3

award_results = {}

request_headers = {
    "User-Agent" : "NFLCompareRedditBot"
}

def main():
    team_venue_history = {}

    request = urllib.request.Request(footballref_team_ids_url, headers=request_headers)
    try:
        response = url_request(request)
    except urllib.error.HTTPError:
        raise

    player_page = BeautifulSoup(response, "html.parser")

    table_names = ["teams_active", "teams_inactive"]
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
                    team_link = row.find("th", {"data-stat" : "team_name"}).find("a")
                    if team_link:
                        overall_team_abbr = team_link["href"].split("/")[2].upper()
                        print(overall_team_abbr)
                        request = urllib.request.Request("https://www.pro-football-reference.com" + team_link["href"], headers=request_headers)
                        try:
                            response = url_request(request)
                        except urllib.error.HTTPError:
                            raise

                        sub_player_page = BeautifulSoup(response, "html.parser")
                        sub_table = sub_player_page.find("table", id="team_index")
                        if not sub_table:
                            sub_comments = sub_player_page.find_all(string=lambda text: isinstance(text, Comment))
                            for c in sub_comments:
                                temp_soup = BeautifulSoup(c, "html.parser")
                                temp_table = temp_soup.find("table", id="team_index")
                                if temp_table:
                                    sub_table = temp_table
                                    break
                        
                        if sub_table:
                            sub_standard_table_rows = sub_table.find("tbody").find_all("tr")
                            for sub_row in sub_standard_table_rows:
                                if not sub_row.get("class") or not "thead" in sub_row.get("class"):
                                    sub_team_row = sub_row.find("td", {"data-stat" : "team"})
                                    if sub_team_row:
                                        sub_team_row_link = sub_team_row.find("a")["href"]
                                        sub_team_row_year = int(re.sub("[^0-9]", "", sub_row.find("th").find(text=True).split("-")[0]))

                                        request = urllib.request.Request("https://www.pro-football-reference.com" + sub_team_row_link, headers=request_headers)
                                        try:
                                            response = url_request(request)
                                        except urllib.error.HTTPError:
                                            raise

                                        sub_sub_player_page = BeautifulSoup(response, "html.parser")

                                        team_info = sub_sub_player_page.find("div", {"id" : "meta"})
                                        if team_info:
                                            stadium_item = team_info.find("strong", text="Stadium:")
                                            if stadium_item:
                                                stadium_parent = stadium_item.parent
                                                if stadium_parent:
                                                    stadium_link = stadium_parent.find("a")
                                                    if stadium_link:
                                                        stadium_id = stadium_link["href"].split("/")[2][:-4].upper()
                                                        
                                                        if overall_team_abbr not in team_venue_history:
                                                            team_venue_history[overall_team_abbr] = {}
                                                        if stadium_id not in team_venue_history[overall_team_abbr]:
                                                            team_venue_history[overall_team_abbr][stadium_id] = []
                                                        if sub_team_row_year not in team_venue_history[overall_team_abbr][stadium_id]:
                                                            team_venue_history[overall_team_abbr][stadium_id].append(sub_team_row_year)
                                        

    with open("team_venue_history.json", "w") as file:
        file.write(json.dumps(team_venue_history, indent=4, sort_keys=True))

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