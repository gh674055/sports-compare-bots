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
from urllib.parse import urlparse, parse_qs

sb_winners = "https://www.pro-football-reference.com/years"

max_request_retries = 10
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

def url_request(url, timeout=30, failed_counter=0):
    gateway_session = requests.Session()
    gateway_session.mount("https://www.pro-football-reference.com", gateway)
    while(True):
        if failed_counter > 0:
            delay_step = 10
            logger.info("#" + str(threading.get_ident()) + "#   " + "Retrying in " + str(retry_failure_delay) + " seconds to allow request to " + url + " to chill")
            time_to_wait = int(math.ceil(float(retry_failure_delay)/float(delay_step)))
            for i in range(retry_failure_delay, 0, -time_to_wait):
                logger.info("#" + str(threading.get_ident()) + "#   " + str(i))
                time.sleep(time_to_wait)
            logger.info("#" + str(threading.get_ident()) + "#   " + "0")

        try:
            response = gateway_session.get(url, timeout=timeout, headers=request_headers)
            response.raise_for_status()
            text = response.text

            bs = BeautifulSoup(text, "lxml")
            if not bs.contents:
                raise requests.exceptions.HTTPError("Page is empty!")
            return response, bs
        except requests.exceptions.HTTPError as err:
            failed_counter += 1
            if failed_counter > max_request_retries:
                raise
            if err.response.status_code == 403:
                error_string = str(err)
                if error_string.startswith("403 Client Error: Forbidden for url:"):
                    error_split = str(err).split()
                    error_url = error_split[len(error_split) - 1]
                    new_url = "https://www.pro-football-reference.com" + urlparse(error_url).path
                    new_url = new_url.replace("/ProxyStage", "")
                    return url_request(new_url, timeout, failed_counter=failed_counter)
        except requests.exceptions.ConnectionError as err:
            failed_counter += 1
            if failed_counter > max_request_retries:
                raise
            error_url = err.request.url
            error_url = "https://www.pro-football-reference.com" + urlparse(error_url).path
            error_url = error_url.replace("/ProxyStage", "")
            return url_request(error_url, timeout, failed_counter=failed_counter)
        except Exception:
            failed_counter += 1
            if failed_counter > max_request_retries:
                raise

if __name__ == "__main__":
    global gateway
    with ApiGateway("https://www.pro-football-reference.com", verbose=False) as gateway:
        main()
