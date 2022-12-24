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
from requests_ip_rotator import ApiGateway
import urllib.parse
from urllib.parse import urlparse, parse_qs

baseballref_team_ids_url = "https://www.baseball-reference.com/teams"
mlb_teams_url_format = "https://statsapi.mlb.com/api/v1/teams/{}/history"
mlb_teams_url_format_2 = "https://statsapi.mlb.com/api/v1/teams/{}"

max_request_retries = 3
retry_failure_delay = 3

award_results = {}

manual_mappings = {
    "Newark Pepper" : "Newark Peppers",
    "Kansas City Cowboys" : {
        "AA" : "Kansas City Blues",
        "UA" : "Kansas City Unions"
    },
    "Altoona Mountain Citys" : "Altoona Pride",
    "Boston Reds" : {
        "UA" : "Boston Unions"
    },
    "Brooklyn Tip-Tops" : "Brooklyn Feds",
    "Brooklyn Ward's Wonders" : "Brooklyn Wonders",
    "Buffalo Blues" : "Buffalo Feds",
    "St. Paul White Caps" : "St. Paul Saints",
    "Columbus Solons" : "Columbus Colts",
    "Columbus Buckeyes" : "Columbus Colts",
    "Worcester Ruby Legs" : "Worcester Brown Stockings",
    "Milwaukee Grays" : "Milwaukee Cream Citys",
    "Milwaukee Brewers" : {
        "UA" : "Milwaukee Unions"
    },
    "Altoona Mountain City" : "Altoona Pride",
    "Rochester Broncos" : "Rochester Hop Bitters",
    "Richmond Virginians" : "Richmond Virginias",
    "Chicago/Pittsburgh" : "Chicago Unions",
    "Houston Colt .45s" : "Houston Colt 45's",
    "Boston Red Stockings" : "Boston Red Caps",
    "Los Angeles Angels of Anaheim" : "Anaheim Angels",
    "Indianapolis Hoosiers" : {
        "FL" : "Indianapolis Hoosier-Feds"
    }
}

leagues_to_id = {
    "National League" : "NL",
    "American League" : "AL",
    "Federal League" : "FL",
    "American Association" : "AA",
    "Players League" : "PL",
    "Union Association" : "UA",
    "National Association" : "NA",
    "Negro National League" : "NNL",
    "Negro National League II" : "NN2",
    "Negro American League" : "NAL",
    "Eastern Colored League" : "ECL",
    "American Negro League" : "ANL",
    "East-West League" : "EWL",
    "Negro Southern League" : "NSL"
}

request_headers = {
    "User-Agent" : "MLBCompareRedditBot"
}

request_headers= {}

current_year = 2022
add_current_year = False

manual_team_name_maps = {
    "Cleveland Indians" : "Cleveland Guardians"
}

def main():
    id_val = 1
    team_info = {}
    team_abr = {}
    team_name_info = {}
    teams_to_league = {}
    team_main_abbr = {}
    team_venue_history = {}

    for league in leagues_to_id:
        team_info[leagues_to_id[league]] = {}
        team_abr[leagues_to_id[league]] = {}

    try:
        response = url_request(baseballref_team_ids_url)
    except requests.exceptions.HTTPError:
        raise

    player_page = BeautifulSoup(response, "html.parser")

    table_names = ["teams_active", "teams_defunct", "teams_na"]
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
                    team_link = row.find("td", {"data-stat" : "franchise_name"}).find("a")
                    if team_link:
                        overall_team_abbr = team_link["href"].split("/")[2].upper()
                        try:
                            response = url_request(overall_team_abbr)
                        except requests.exceptions.HTTPError:
                            raise

                        sub_player_page = BeautifulSoup(response, "html.parser")
                        sub_table = sub_player_page.find("table", id="franchise_years")
                        if not sub_table:
                            sub_comments = sub_player_page.find_all(string=lambda text: isinstance(text, Comment))
                            for c in sub_comments:
                                temp_soup = BeautifulSoup(c, "html.parser")
                                temp_table = temp_soup.find("table", id="franchise_years")
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
                                        sub_team_row_name = unidecode.unidecode(sub_team_row.find(text=True))
                                        sub_team_row_league = sub_row.find("td", {"data-stat" : "lg_ID"}).find(text=True).split()[0]
                                        if sub_team_row_name in manual_mappings:
                                            og_sub_team_row_name = sub_team_row_name
                                            sub_team_row_name = manual_mappings[sub_team_row_name]
                                            if isinstance(sub_team_row_name, dict):
                                                if sub_team_row_league in sub_team_row_name:
                                                    sub_team_row_name = sub_team_row_name[sub_team_row_league]
                                                else:
                                                    sub_team_row_name = og_sub_team_row_name

                                        sub_team_row_year = int(re.sub("[^0-9]", "", sub_row.find("th").find(text=True).split("-")[0]))

                                        if sub_team_row_league not in team_main_abbr:
                                            team_main_abbr[sub_team_row_league] = {}
                                        if str(sub_team_row_year) not in team_main_abbr[sub_team_row_league]:
                                            team_main_abbr[sub_team_row_league][str(sub_team_row_year)] = {}
                                        team_main_abbr[sub_team_row_league][str(sub_team_row_year)][sub_team_row_abbr] = overall_team_abbr

                                        if sub_team_row_name == "Washington Senators":
                                            if sub_team_row_league == "AL":
                                                if sub_team_row_year < 1961:
                                                    sub_team_row_name = "Washington Senators (1901)"
                                            elif sub_team_row_league == "NL":
                                                if sub_team_row_year < 1891:
                                                    sub_team_row_name = "Washington Senators (1886)"
                                        elif sub_team_row_name == "Baltimore Orioles":
                                            if sub_team_row_league == "AA":
                                                if sub_team_row_year < 1890:
                                                    sub_team_row_name = "Baltimore Orioles (1882)"
                                            elif sub_team_row_league == "AL":
                                                if sub_team_row_year < 1903:
                                                    sub_team_row_name = "Baltimore Orioles (1901)"
                                        elif sub_team_row_name == "Cincinnati Reds":
                                            if sub_team_row_league == "NL":
                                                if sub_team_row_year < 1882:
                                                    sub_team_row_name = "Cincinnati Reds (1876)"
                                        elif sub_team_row_name == "Columbus Colts":
                                            if sub_team_row_league == "AA":
                                                if sub_team_row_year < 1889:
                                                    sub_team_row_name = "Columbus Colts (1883)"
                                        elif sub_team_row_name == "Milwaukee Brewers":
                                            if sub_team_row_league == "AL":
                                                if sub_team_row_year < 1968:
                                                    sub_team_row_name = "Milwaukee Brewers (1901)"
                                        elif sub_team_row_name == "Washington Nationals":
                                            if sub_team_row_league == "NL":
                                                if sub_team_row_year < 1890:
                                                    sub_team_row_name = "Washington Senators (1886)"
                                        elif sub_team_row_name == "Cleveland Blues":
                                            if sub_team_row_league == "NL":
                                                if sub_team_row_year < 1880:
                                                    sub_team_row_name = "Cleveland Spiders (1879)"

                                        if sub_team_row_name not in team_name_info:
                                            team_name_info[sub_team_row_name] = {}
                                        if sub_team_row_abbr not in team_name_info[sub_team_row_name]:
                                            team_name_info[sub_team_row_name][sub_team_row_abbr] = {}
                                        if sub_team_row_league not in team_name_info[sub_team_row_name][sub_team_row_abbr]:
                                            team_name_info[sub_team_row_name][sub_team_row_abbr][sub_team_row_league] = []
                                        if sub_team_row_year not in team_name_info[sub_team_row_name][sub_team_row_abbr][sub_team_row_league]:
                                            team_name_info[sub_team_row_name][sub_team_row_abbr][sub_team_row_league].append(sub_team_row_year)

                                        if sub_team_row_abbr not in teams_to_league:
                                            teams_to_league[sub_team_row_abbr] = {}
                                        if sub_team_row_league not in teams_to_league[sub_team_row_abbr]:
                                            teams_to_league[sub_team_row_abbr][sub_team_row_league] = []
                                        if sub_team_row_year not in teams_to_league[sub_team_row_abbr][sub_team_row_league]:
                                            teams_to_league[sub_team_row_abbr][sub_team_row_league].append(sub_team_row_year)

                                        if sub_team_row_year == current_year - 1 and add_current_year:
                                            sub_team_row_year += 1
                                            if sub_team_row_name in manual_team_name_maps:
                                                sub_team_row_name = manual_team_name_maps[sub_team_row_name]
                                                if sub_team_row_name not in team_name_info:
                                                    team_name_info[sub_team_row_name] = {}
                                                if sub_team_row_abbr not in team_name_info[sub_team_row_name]:
                                                    team_name_info[sub_team_row_name][sub_team_row_abbr] = {}
                                                if sub_team_row_league not in team_name_info[sub_team_row_name][sub_team_row_abbr]:
                                                    team_name_info[sub_team_row_name][sub_team_row_abbr][sub_team_row_league] = []

                                            if str(sub_team_row_year) not in team_main_abbr[sub_team_row_league]:
                                                team_main_abbr[sub_team_row_league][str(sub_team_row_year)] = {}
                                            team_main_abbr[sub_team_row_league][str(sub_team_row_year)][sub_team_row_abbr] = overall_team_abbr
                                            if sub_team_row_year not in team_name_info[sub_team_row_name][sub_team_row_abbr][sub_team_row_league]:
                                                team_name_info[sub_team_row_name][sub_team_row_abbr][sub_team_row_league].append(sub_team_row_year)
                                            if sub_team_row_year not in teams_to_league[sub_team_row_abbr][sub_team_row_league]:
                                                teams_to_league[sub_team_row_abbr][sub_team_row_league].append(sub_team_row_year)
    

    for id_val in range(1, 806):
        try:
            response = url_request(mlb_teams_url_format.format(id_val))
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                continue
            else:
                raise

        data = json.load(response)
        last_season = None
        for index, team in enumerate(data["teams"]):
            if team["sport"]["id"] == 1 and "name" in team["league"]:
                team_str = unidecode.unidecode(team["name"])
                league = leagues_to_id[team["league"]["name"]]

                season = team["season"]

                if id_val not in team_venue_history:
                     team_venue_history[id_val] = []

                if last_season == None:
                    team_venue_history[id_val].append({
                        "start_year" : season,
                        "end_year" : None,
                        "venue" : team["venue"]["id"]
                    })
                elif index == len(data["teams"]) - 1:
                     team_venue_history[id_val].append({
                        "start_year" : None,
                        "end_year" : last_season - 1,
                        "venue" : team["venue"]["id"]
                    })
                else:
                    team_venue_history[id_val].append({
                        "start_year" : season,
                        "end_year" : last_season - 1,
                        "venue" : team["venue"]["id"]
                    })
                
                last_season = season

                if team_str == "Washington Senators":
                    if league == "AL":
                        if int(team["firstYearOfPlay"]) < 1961:
                            team_str = "Washington Senators (1901)"
                    elif league == "NL":
                        if int(team["firstYearOfPlay"]) < 1891:
                            team_str = "Washington Senators (1886)"
                elif team_str == "Baltimore Orioles":
                    if league == "AA":
                        if int(team["firstYearOfPlay"]) < 1890:
                            team_str = "Baltimore Orioles (1882)"
                    elif league == "AL":
                        if team["teamCode"] == "blo":
                            team_str = "Baltimore Orioles (1901)"
                elif team_str == "Cincinnati Reds":
                    if league == "NL":
                        if int(team["firstYearOfPlay"]) < 1882:
                            team_str = "Cincinnati Reds (1876)"
                elif team_str == "Cleveland Spiders":
                    if league == "NL":
                        if int(team["firstYearOfPlay"]) < 1887:
                            team_str = "Cleveland Spiders (1879)"
                elif team_str == "Columbus Colts":
                    if league == "AA":
                        if int(team["firstYearOfPlay"]) < 1889:
                            team_str = "Columbus Colts (1883)"
                elif team_str == "Milwaukee Brewers":
                    if league == "AL":
                        if int(team["firstYearOfPlay"]) < 1968:
                            team_str = "Milwaukee Brewers (1901)"

                if team_str not in team_name_info:
                    print("Skipping MLB team : " + team_str + " (" + str(id_val) + ")")
                    continue

                abbr = unidecode.unidecode(team["abbreviation"])
                if team_str in team_info[league]:
                    if team["id"] == team_info[league][team_str]:
                        continue
                    else:
                        print("Bad team " + team_str + " : " + str(team["id"]) + " (" + str(team_info[league][team_str]) + ")")
                        continue
                team_info[league][team_str] = id_val
                team_abr[league][abbr] = team_str
    
    for id_val in range(1, 806):
        try:
            response = url_request(mlb_teams_url_format_2.format(id_val))
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                continue
            else:
                raise

        data = json.load(response)
        for team in data["teams"]:
            if team["sport"]["id"] == 1 and "name" in team["league"] and team["active"]:
                team_str = unidecode.unidecode(team["name"])
                league = leagues_to_id[team["league"]["name"]]

                if team_str == "Washington Senators":
                    if league == "AL":
                        if int(team["firstYearOfPlay"]) < 1961:
                            team_str = "Washington Senators (1901)"
                    elif league == "NL":
                        if int(team["firstYearOfPlay"]) < 1891:
                            team_str = "Washington Senators (1886)"
                elif team_str == "Baltimore Orioles":
                    if league == "AA":
                        if int(team["firstYearOfPlay"]) < 1890:
                            team_str = "Baltimore Orioles (1882)"
                    elif league == "AL":
                        if team["teamCode"] == "blo":
                            team_str = "Baltimore Orioles (1901)"
                elif team_str == "Cincinnati Reds":
                    if league == "NL":
                        if int(team["firstYearOfPlay"]) < 1882:
                            team_str = "Cincinnati Reds (1876)"
                elif team_str == "Cleveland Spiders":
                    if league == "NL":
                        if int(team["firstYearOfPlay"]) < 1887:
                            team_str = "Cleveland Spiders (1879)"
                elif team_str == "Columbus Colts":
                    if league == "AA":
                        if int(team["firstYearOfPlay"]) < 1889:
                            team_str = "Columbus Colts (1883)"
                elif team_str == "Milwaukee Brewers":
                    if league == "AL":
                        if int(team["firstYearOfPlay"]) < 1968:
                            team_str = "Milwaukee Brewers (1901)"

                if team_str not in team_name_info:
                    print("Skipping MLB team : " + team_str + " (" + str(id_val) + ")")
                    continue

                abbr = unidecode.unidecode(team["abbreviation"])
                if team_str in team_info[league] and team_info[league][team_str] == id_val:
                    team_abr[league][abbr] = team_str

    with open("team_ids.json", "w") as file:
        file.write(json.dumps(team_info, indent=4, sort_keys=True))
    
    with open("team_abr.json", "w") as file:
        file.write(json.dumps(team_abr, indent=4, sort_keys=True))

    with open("team_name_info.json", "w") as file:
        file.write(json.dumps(team_name_info, indent=4, sort_keys=True))
    
    with open("teams_to_league.json", "w") as file:
        file.write(json.dumps(teams_to_league, indent=4, sort_keys=True))

    with open("team_main_abbr.json", "w") as file:
        file.write(json.dumps(team_main_abbr, indent=4, sort_keys=True))

    with open("team_venue_history.json", "w") as file:
        file.write(json.dumps(team_venue_history, indent=4, sort_keys=True))

def url_request(url, timeout=30, retry_403=True):
    gateway_session = requests.Session()
    gateway_session.mount("https://www.baseball-reference.com", gateway)
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
            if retry_403 and url.startswith("https://www.baseball-reference.com/") and not response.url.startswith("https://www.baseball-reference.com/"):
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
    gateway = ApiGateway("https://www.baseball-reference.com", verbose=False)
    endpoints = gateway.start()
    try:
        main()
    finally:
        gateway.shutdown(endpoints)