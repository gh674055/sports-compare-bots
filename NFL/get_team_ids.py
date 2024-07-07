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
import urllib.parse
from urllib.parse import urlparse, parse_qs
import signal

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