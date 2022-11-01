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
from requests_ip_rotator import ApiGateway

footballref_team_ids_url = "https://www.pro-football-reference.com/teams"

max_request_retries = 3
retry_failure_delay = 3

award_results = {}

request_headers = {
    "User-Agent" : "NFLCompareRedditBot"
}

request_headers= {}

def main():
    team_venue_history = {}

    try:
        response = url_request(footballref_team_ids_url)
    except requests.exceptions.HTTPError:
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
                        try:
                            response = url_request("https://www.pro-football-reference.com" + team_link["href"])
                        except requests.exceptions.HTTPError:
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

                                        try:
                                            response = url_request("https://www.pro-football-reference.com" + sub_team_row_link)
                                        except requests.exceptions.HTTPError:
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

def url_request(url, timeout=30):
    failed_counter = 0
    gateway_session = requests.Session()
    gateway_session.mount("https://www.pro-football-reference.com", gateway)
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
                error_string = str(err)
                if error_string.startswith("403 Client Error: Forbidden for url:"):
                    error_split = str(err).split()
                    error_url = error_split[len(error_split) - 1]
                    new_url = "https://www.pro-football-reference.com" + urlparse(error_url).path
                    return url_request(new_url, timeout)
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
    with ApiGateway("https://www.pro-football-reference.com", verbose=False) as gateway:
        main()