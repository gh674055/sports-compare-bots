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

sb_winners = "https://www.pro-football-reference.com/years"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "NFLCompareRedditBot"
}

request_headers= {}

def main():
    response = url_request(sb_winners)
    table_names = ["years"]
    player_page = BeautifulSoup(response, "html.parser")
    champs = {}

    for table_name in table_names:
        table = player_page.find("table", id=table_name)

        standard_table_rows = table.find("tbody").find_all("tr")
        for row in standard_table_rows:
            classes = row.get("class")
            if (not classes or not "thead" in classes) and hasattr(row, "data-row"):
                winner_row = row.find("td", {"data-stat" : "summary"})
                winner_text = winner_row.find(text=True)
                if winner_text:
                    winner_text = winner_text.strip()
                    date_row = row.find("th", {"data-stat" : "year_id"})
                    year = int(date_row.find(text=True))
                    winners = []
                    winner_links = []
                    if winner_text.startswith("Super Bowl"):
                        winner_links = [winner_row.find("a")]
                    else:
                        winner_links = winner_row.find_all("a")
                    for winner_link in winner_links:
                        winners.append(winner_link["href"].split("/")[2].upper())
                    champs[year] = winners
    
    with open("champs.json", "w") as file:
        file.write(json.dumps(champs, indent=4, sort_keys=True))

def url_request(url, timeout=30, retry_403=True):
    gateway_session = requests.Session()
    gateway_session.mount("https://www.pro-football-reference.com", gateway)
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
        sys.exit(0)
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    try:
        main()
    finally:
        gateway.shutdown(endpoints)
