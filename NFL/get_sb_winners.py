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

sb_winners = "https://www.pro-football-reference.com/years"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "NFLCompareRedditBot"
}

request_headers= {}

def main():
    request = urllib.request.Request(sb_winners, headers=request_headers)
    response = url_request(request)
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
        logger.info("Retrying in " + str(retry_failure_delay) + " seconds to allow fangraphs to chill")
        time_to_wait = int(math.ceil(float(retry_failure_delay)/float(delay_step)))
        for i in range(retry_failure_delay, 0, -time_to_wait):
            logger.info(i)
            time.sleep(time_to_wait)
        logger.info("0")

if __name__ == "__main__":
    main()
