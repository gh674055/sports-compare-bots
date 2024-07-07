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
import threading
from requests_ip_rotator import ApiGateway
import urllib.parse
from urllib.parse import urlparse, parse_qs
import signal

awards_url_format = "https://www.hockey-reference.com/awards/voting-{}.html"

max_request_retries = 3
retry_failure_delay = 3

award_results = {}

request_headers = {
    "User-Agent" : "NHLCompareRedditBot"
}

request_headers= {}

def main():
    for season in range(1924, 2022):
        if season != 2004:
            print(season)
            award_results[season] = {}

            response = url_request(awards_url_format.format(str(season + 1)))

            player_page = BeautifulSoup(response, "html.parser")

            awards = ["AllStar", "Hart", "Selke", "Norris", "Vezina"]
            for award in awards:
                award_results[season][award] = {}
                table_name = (award.lower() if award != "AllStar" else "AS") + "_stats"

                table = player_page.find("table", id=table_name)
                if not table:
                    comments = player_page.find_all(string=lambda text: isinstance(text, Comment))
                    for c in comments:
                        temp_soup = BeautifulSoup(c, "html.parser")
                        temp_table = temp_soup.find("table", id=table_name)
                        if temp_table:
                            table = temp_table
                            break

                if table:
                    standard_table_rows = table.find("tbody").find_all("tr")
                    total_votes = 0
                    total_first_place = 0
                    total_second_place = 0
                    total_third_place = 0
                    total_fourth_place = 0
                    total_fifth_place = 0
                    for row in standard_table_rows:
                        if not row.get("class") or "thead" not in row.get("class"):
                            player_url = row.find("td", {"data-stat" : "player"}).find("a").get("href")
                            player_id = player_url.split("/")[3].split(".")[0]
                            vote_share = row.find("td", {"data-stat" : "votes"}).find(text=True)
                            if vote_share:
                                award_results[season][award][player_id] = float(vote_share)
                                total_votes += award_results[season][award][player_id]
                            
                            first_place_votes = row.find("td", {"data-stat" : "first"}).find(text=True)
                            if first_place_votes:
                                total_first_place += float(first_place_votes)
                            second_place_votes = row.find("td", {"data-stat" : "second"}).find(text=True)
                            if second_place_votes:
                                total_second_place += float(second_place_votes)
                            third_place_votes = row.find("td", {"data-stat" : "third"}).find(text=True)
                            if third_place_votes:
                                total_third_place += float(third_place_votes)
                            fourth_place_votes = row.find("td", {"data-stat" : "fourth"}).find(text=True)
                            if fourth_place_votes:
                                total_fourth_place += float(fourth_place_votes)
                            fifth_place_votes = row.find("td", {"data-stat" : "fifth"}).find(text=True)
                            if fifth_place_votes:
                                total_fifth_place += float(fifth_place_votes)
                        
                    if not total_first_place:
                        vote_denom = total_votes
                    else:
                        if total_fourth_place:
                            vote_denom = total_first_place * 10
                        else:
                            if third_place_votes:
                                vote_denom = total_first_place * 5
                            else:
                                vote_denom = total_votes
                    award_results[season][award]["vote_denom"] = vote_denom
    
    with open("award_results.json", "w") as file:
        file.write(json.dumps(award_results, indent=4, sort_keys=True))

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
