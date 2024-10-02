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

def main():
    team_name_history = {}

    #try:
    #    player_page = url_request(footballref_team_ids_url)[1]
    #except requests.exceptions.HTTPError:
    #    raise

    player_page_file = "C:/Users/jhark/Downloads/List of all the Pro Football Franchises _ Pro-Football-Reference.com.html"
    with open(player_page_file, "r") as the_file:
        player_page = BeautifulSoup(the_file, "lxml")

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
            last_overall_team_row = None

            has_sub_teams = False
            for row in standard_table_rows:
                if not row.get("scope"):
                    overall_team_abbr = None
                    if not row.get("class"):
                        team_link = row.find("th", {"data-stat" : "team_name"}).find("a")
                        if team_link:
                            overall_team_abbr = team_link["href"].split("/")[4].upper()
                    
                    if overall_team_abbr:
                        if last_overall_team_row and not has_sub_teams:
                            name = str(last_overall_team_row.find("th", {"data-stat" : "team_name"}).find(text=True))
                            start_year = int(last_overall_team_row.find("td", {"data-stat" : "year_min"}).find(text=True))
                            end_year = int(last_overall_team_row.find("td", {"data-stat" : "year_max"}).find(text=True))
                            last_overall_team_abbr = last_overall_team_row.find("th", {"data-stat" : "team_name"}).find("a")["href"].split("/")[4].upper()

                            if not last_overall_team_abbr in team_name_history:
                                team_name_history[last_overall_team_abbr] = []
                            team_name_history[last_overall_team_abbr].append({
                                "start_year" : start_year,
                                "end_year" : end_year,
                                "name" : name
                            })

                        last_overall_team_row = row
                        has_sub_teams = False
                    else:
                        team_row = row.find("th", {"data-stat" : "team_name"})
                        if team_row and team_row.get("scope") == "row":
                            name = str(team_row.find(text=True))
                            start_year = int(row.find("td", {"data-stat" : "year_min"}).find(text=True))
                            end_year = int(row.find("td", {"data-stat" : "year_max"}).find(text=True))
                            last_overall_team_abbr = last_overall_team_row.find("th", {"data-stat" : "team_name"}).find("a")["href"].split("/")[4].upper()

                            if not last_overall_team_abbr in team_name_history:
                                team_name_history[last_overall_team_abbr] = []
                            team_name_history[last_overall_team_abbr].append({
                                "start_year" : start_year,
                                "end_year" : end_year,
                                "name" : name
                            })

                            has_sub_teams = True
    
    with open("team_name_history.json", "w") as file:
        file.write(json.dumps(team_name_history, indent=4, sort_keys=True))

if __name__ == "__main__":
    main()