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
import threading
from requests_ip_rotator import ApiGateway
import urllib.parse
from urllib.parse import urlparse, parse_qs
import signal
import mlb

hof_players = "https://www.baseball-reference.com/awards/hof.shtml"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "MLBCompareRedditBot"
}

request_headers= {}

def main():
    response, player_page = url_request(hof_players)
    table_names = ["hof"]
    hof_members = {}

    with requests.Session() as s:
        for table_name in table_names:
            table = player_page.find("table", id=table_name)

            standard_table_rows = table.find("tbody").find_all("tr")
            for row in standard_table_rows:
                classes = row.get("class")
                if (not classes or not "thead" in classes) and hasattr(row, "data-row"):
                    hof_id = str(row.find("td", {"data-stat" : "player"})["data-append-csv"])
                    hof_year = int(row.find("th", {"data-stat" : "year_ID"}).find(text=True))
                    hof_voted_by = str(row.find("td", {"data-stat" : "votedBy"}).find(text=True))
                    hof_inducted_as = row.find("td", {"data-stat" : "category_hof"}).find(text=True)
                    hof_votes = row.find("td", {"data-stat" : "votes"}).find(text=True)
                    if hof_votes:
                        hof_votes = int(float(hof_votes))
                    else:
                        hof_votes = None
                    hof_per = row.find("td", {"data-stat" : "votes_pct"}).get("csk")
                    if hof_per:
                        hof_per = float(str(hof_per))
                    else:
                        hof_per = None

                    player_url = mlb.main_page_url_format.format(hof_id[0], hof_id)

                    try:
                        real_response, real_player_page = url_request(player_url)
                    except requests.exceptions.HTTPError as err:
                        if err.response.status_code == 404:
                            if hof_inducted_as == "Player":
                                raise Exception("#" + str(threading.get_ident()) + "#   " + "Unable to get MLB player page for : " + str(row.find("td", {"data-stat" : "player"}).find(text=True)))
                            continue
                        else:
                            raise

                    player_data = {
                        "id": hof_id
                    }

                    player_data["Player"] = mlb.get_player_name(real_player_page)
                    player_data["Birthday"] = mlb.get_player_birthday(real_player_page)
                    player_data["player_current_team"], player_data["player_current_number"], player_data["player_all_numbers"], player_data["player_team_map"], player_data["numbers_year_map"] = mlb.get_player_current_team_number(hof_id, real_player_page)
                    player_data["player_position"] = mlb.get_player_position(real_player_page)

                    is_mlb_player = False
                    for sub_year in player_data["numbers_year_map"]:
                        year_str = str(sub_year)
                        for team in player_data["numbers_year_map"][sub_year]:
                            if team not in player_data["player_team_map"]:
                                continue
                            team_name = player_data["player_team_map"][team]
                            sleague = mlb.get_team_league(team, sub_year)
                            if sleague in ["AL", "NL"]:
                                is_mlb_player = True
                            break
                        if is_mlb_player:
                            break
                                
                    player_link = mlb.get_mlb_player_link(player_data, s)
                   
                    if not player_link:
                        if is_mlb_player:
                            raise Exception("#" + str(threading.get_ident()) + "#   " + "Unable to get MLB player link for BRef ID : " + player_data["id"])
                        continue
                    else:
                        hof_members[player_link.split('/')[-1]] = {
                            "bref_id" : hof_id,
                            "year" : hof_year,
                            "voted_by" : hof_voted_by,
                            "inducted_as" : hof_inducted_as,
                            "votes" : hof_votes,
                            "per" : hof_per
                        }
    
    with open("hof_members.json", "w") as file:
        file.write(json.dumps(hof_members, indent=4, sort_keys=True))

def url_request(url, timeout=30, retry_403=True):
    gateway_session = requests.Session()
    gateway_session.mount("https://www.baseball-reference.com", gateway)
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
            if e.response.status_code == 404:
                raise
            elif retry_403 and url.startswith("https://www.baseball-reference.com/") and not response.url.startswith("https://www.baseball-reference.com/"):
                url_parsed = urlparse(response.url)
                path = url_parsed.path[1:].split("/")[0]
                if path != "ProxyStage":
                    replaced = url_parsed._replace(path="/ProxyStage" + url_parsed.path)
                    rebuilt_url = urllib.parse.urlunparse(replaced)
                    print("#" + str(threading.get_ident()) + "#   " + "Rebuilt URL on 403 and retrying from " + response.url + " to " + rebuilt_url)
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
        print("#" + str(threading.get_ident()) + "#   " + "Retrying in " + str(retry_failure_delay) + " seconds to allow request to " + url + " to chill")
        time_to_wait = int(math.ceil(float(retry_failure_delay)/float(delay_step)))
        for i in range(retry_failure_delay, 0, -time_to_wait):
            print("#" + str(threading.get_ident()) + "#   " + str(i))
            time.sleep(time_to_wait)
        print("#" + str(threading.get_ident()) + "#   " + "0")

if __name__ == "__main__":
    global gateway
    gateway =  ApiGateway("https://www.baseball-reference.com", verbose=True)
    endpoints = gateway.start(force=True)

    def exit_gracefully(signum, frame):
        sys.exit(signum)
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    try:
        main()
    finally:
        gateway.shutdown(endpoints)
