import requests
from bs4 import BeautifulSoup, Comment
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import time
import math
import socket
import re
import getopt
import datetime
import threading
import lxml
import cchardet
import ssl
from requests_ip_rotator import ApiGateway
import urllib.parse
from urllib.parse import urlparse, parse_qs
import signal

league_totals_url = "https://www.hockey-reference.com/{}/NHL_{}_{}.html"
current_year_stats_url = "https://www.hockey-reference.com/{}/NHL_{}.html"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "NHLCompareRedditBot"
}

request_headers= {}

logname = "nhl-constants.log"
logger = logging.getLogger("nhl-constants")
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler = TimedRotatingFileHandler(logname, when="midnight", interval=1)
handler.suffix = "%Y%m%d"
handler.setFormatter(formatter)
logger.addHandler(handler)
streamhandler = logging.StreamHandler(sys.stdout)
streamhandler.setLevel(logging.DEBUG)
logger.addHandler(streamhandler)

start_year = 1917
end_year = 2022
current_year_playoffs_started = False

year_games_played = [
    {
        "start_year" : start_year,
        "end_year" : 1924,
        "roster" : 9
    },
    {
        "start_year" : 1925,
        "end_year" : 1928,
        "roster" : 12
    },
    {
        "start_year" : 1929,
        "end_year" : 1931,
        "roster" : 15
    },
    {
        "start_year" : 1932,
        "end_year" : 1937,
        "roster" : 14
    },
    {
        "start_year" : 1938,
        "end_year" : 1941,
        "roster" : 15
    },
    {
        "start_year" : 1942,
        "end_year" : 1948,
        "roster" : 14
    },
    {
        "start_year" : 1949,
        "end_year" : 1950,
        "roster" : 17
    },
    {
        "start_year" : 1951,
        "end_year" : 1951,
        "roster" : 15
    },
    {
        "start_year" : 1952,
        "end_year" : 1952,
        "roster" : 15.5
    },
    {
        "start_year" : 1953,
        "end_year" : 1953,
        "roster" : 16
    },
    {
        "start_year" : 1954,
        "end_year" : 1959,
        "roster" : 17
    },
    {
        "start_year" : 1960,
        "end_year" : 1970,
        "roster" : 16
    },
    {
        "start_year" : 1971,
        "end_year" : 1981,
        "roster" : 17
    },
    {
        "start_year" : 1982,
        "end_year" : end_year,
        "roster" : 18
    }
]

ssl._create_default_https_context = ssl._create_unverified_context

def main():
    year_short = "y"
    year_long = "year"
    try:
        options = getopt.getopt(sys.argv[1:], year_short + ":", [year_long + "="])[0]
    except getopt.GetoptError as err:
        logger.error("Encountered error \"" + str(err) + "\" parsing arguments")
        return

    year = None
    for opt, arg in options:
        if opt in ("-" + year_short, "--" + year_long):
            year = int(arg.strip())

    totals = None
    if year:
        with open("yearly_totals.json", "r") as file:
            totals = json.load(file)
        get_totals(year, totals)
    else:
        totals = get_totals(None, None)

    with open("yearly_totals.json", "w") as file:
        file.write(json.dumps(totals, indent=4, sort_keys=True))

def get_totals(specific_year, totals):
    logger.info("Getting league total data for year " + str(specific_year))

    format_strs = {
        "Skater" : "skaters",
        "Goalie" : "goalies"
    }

    if not totals:
        totals = {
            "Standard" : {
                "Skater" : {
                    "F" : {},
                    "D" : {}
                },
                "Goalie" : {
                    "G" : {}
                },
                "TOT" : {}
            },
            "Playoffs" : {
                "Skater" : {
                    "F" : {},
                    "D" : {}
                },
                "Goalie" : {
                    "G" : {}
                },
                "TOT" : {}
            }
        }
    elif specific_year:
        for over_key in totals:
            for key in totals[over_key]:
                if key == "TOT":
                    totals[over_key][key][str(specific_year)] = {}
                else:
                    for pos in totals[over_key][key]:
                        totals[over_key][key][pos][str(specific_year)] = {}

    headers_to_read = {
        "Skater" : {
            "GP",
            "G",
            "A",
            "PTS",
            "+/-",
            "PIM",
            "PPG",
            "SHG",
            "PPA",
            "S",
            "TOI"
        },
        "Goalie" : {
            "GP",
            "W",
            "L",
            "T/O",
            "GA",
            "SA",
            "SV",
            "SO",
            "TOI",
            "G",
            "A",
            "PTS",
            "PIM"
        }
    }

    years = None
    if specific_year:
        years = [specific_year]
    else:
        years = range(start_year, end_year + 1)

    team_map_by_year = {}
    for over_key in totals:
        logger.info("Getting league total game data for " + over_key)
        current_percent = 10
        count = 0
        for year in years:
            if over_key == "Playoffs" and year == end_year and not current_year_playoffs_started:
                logger.info("Skipping current year " + str(year) + " as playoffs have not stared yet")
                continue

            team_map_by_year_val = calculate_year_games_by_team(year, over_key == "Playoffs")
            if not over_key in team_map_by_year:
                team_map_by_year[over_key] = {}

            team_map_by_year[over_key][str(year)] = team_map_by_year_val
            
            count += 1
            percent_complete = 100 * (count / len(years))
            if not specific_year and count != 1 and percent_complete >= current_percent:
                logger.info(str(current_percent) + "%")
                current_percent += 10

    for over_key in totals:
        for key in totals[over_key]:
            if key == "TOT":
                continue
            
            logger.info("Getting league total data for " + over_key + " : " + key)
            current_percent = 10
            count = 0
            for year in years:
                if over_key == "Playoffs" and year == end_year and not current_year_playoffs_started:
                    logger.info("Skipping current year " + str(year) + " as playoffs have not stared yet")
                    continue

                try:
                    response, player_page = url_request(league_totals_url.format("playoffs" if over_key == "Playoffs" else "leagues", year + 1, format_strs[key]))
                except requests.exceptions.HTTPError as err:
                    if err.response.status_code == 404:
                        continue
                    else:
                        raise
                
                table = player_page.find("table", id="stats")
                if not table:
                    continue

                if key == "Goalie":
                    if not str(year) in totals[over_key][key]["G"]:
                        totals[over_key][key]["G"][str(year)] = {}
                else:
                    if not str(year) in totals[over_key][key]["F"]:
                        totals[over_key][key]["F"][str(year)] = {}
                        totals[over_key][key]["D"][str(year)] = {}

                header_columns = table.find("thead").find("tr", {"class" : "over_header"}).find_next_sibling().find_all("th")
                header_values = []
                for header in header_columns:
                    header_values.append(header.find(text=True).strip())

                standard_table_rows = table.find("tbody").find_all("tr")

                for row in standard_table_rows:
                    classes = row.get("class")
                    if not classes or not "thead" in classes:
                        team = row.find("td", {"data-stat" : "team_id"}).find(text=True)
                        if key == "Goalie":
                            pos = "G"
                        else:
                            pos = row.find("td", {"data-stat" : "pos"}).find(text=True)
                            pos = "D" if pos == "D" else "F"

                        if team == "TOT":
                            continue

                        columns = row.find_all("td", recursive=False)
                        for sub_index, column in enumerate(columns):
                            real_index = sub_index + 1
                            header_value = header_values[real_index]
                            if header_value == "TOI":
                                continue
                            elif header_value == "ATOI" or header_value == "MIN":
                                header_value = "TOI"
                            elif header_value == "PP":
                                if column["data-stat"] == "goals_pp":
                                    header_value = "PPG"
                                else:
                                        header_value = "PPA"
                            elif header_value == "SH":
                                if column["data-stat"] == "goals_sh":
                                    header_value = "SHG"

                            if header_value in headers_to_read[key]:
                                column_contents = column.find(text=True)
                                column_value = 0.0
                                if column_contents:
                                    if header_value == "TOI":
                                        if column_contents.isdigit():
                                            column_value = int(column_contents) * 60
                                        else:
                                            time_split = column_contents.split(":")
                                            minutes = int(time_split[0])
                                            seconds = int(time_split[1])
                                            column_value = (minutes * 60) + seconds
                                            column_value *= int(row.find("td", {"data-stat" : "games_played"}).find(text=True))
                                    else:
                                        column_value = float(column_contents)

                                    if not team in totals[over_key][key][pos][str(year)]:
                                        totals[over_key][key][pos][str(year)][team] = {}
                                    if not header_value in totals[over_key][key][pos][str(year)][team]:
                                        totals[over_key][key][pos][str(year)][team][header_value] = 0.0

                                    totals[over_key][key][pos][str(year)][team][header_value] += column_value
                
                if not str(year) in totals[over_key]["TOT"]:
                    totals[over_key]["TOT"][str(year)] = {}

                if key == "Skater":
                    for pos in ["F", "D"]:
                        for team in totals[over_key][key][pos][str(year)]:
                            if not team in totals[over_key]["TOT"][str(year)]:
                                totals[over_key]["TOT"][str(year)][team] = {}

                            for header_value in totals[over_key][key][pos][str(year)][team]:
                                if not header_value in totals[over_key]["TOT"][str(year)][team]:
                                    totals[over_key]["TOT"][str(year)][team][header_value] = 0.0
                                totals[over_key]["TOT"][str(year)][team][header_value] += totals[over_key][key][pos][str(year)][team][header_value]
                else:
                    for team in totals[over_key][key]["G"][str(year)]:
                        if not team in totals[over_key]["TOT"][str(year)]:
                            totals[over_key]["TOT"][str(year)][team] = {}

                        for header_value in totals[over_key][key]["G"][str(year)][team]:
                            if not header_value in totals[over_key]["TOT"][str(year)][team]:
                                totals[over_key]["TOT"][str(year)][team][header_value] = 0.0
                            totals[over_key]["TOT"][str(year)][team][header_value] += totals[over_key][key]["G"][str(year)][team][header_value]
                                    
                count += 1
                percent_complete = 100 * (count / len(years))
                if not specific_year and count != 1 and percent_complete >= current_percent:
                    logger.info(str(current_percent) + "%")
                    current_percent += 10

    for over_key in totals:
        for key in totals[over_key]:
            logger.info("Combining league total data for " + over_key + " : " + key)
            if key == "TOT":
                for year in years:
                    if str(year) in totals[over_key][key]:
                        totals[over_key][key][str(year)]["NHL"] = {}

                        for team in totals[over_key][key][str(year)]:
                            if team != "NHL":
                                if team in team_map_by_year[over_key][str(year)]:
                                    for header_value in team_map_by_year[over_key][str(year)][team]:
                                        totals[over_key][key][str(year)][team][header_value] = team_map_by_year[over_key][str(year)][team][header_value]

                                    for header_value in totals[over_key][key][str(year)][team]:
                                        if header_value not in totals[over_key][key][str(year)]["NHL"]:
                                            totals[over_key][key][str(year)]["NHL"][header_value] = 0.0

                                        totals[over_key][key][str(year)]["NHL"][header_value] += totals[over_key][key][str(year)][team][header_value]

                        for year_game_played in year_games_played:
                            year_start_year = year_game_played["start_year"]
                            year_end_year = year_game_played["end_year"]
                            if (not year_start_year or year >= year_start_year) and (not year_end_year or year <= year_end_year):
                                roster_per_season = year_game_played["roster"]
                        
                        totals[over_key][key][str(year)]["NHL"]["roster_size"] = roster_per_season
            else:
                for pos in totals[over_key][key]:
                    for year in years:
                        if str(year) in totals[over_key][key][pos]:
                            totals[over_key][key][pos][str(year)]["NHL"] = {}

                            for team in totals[over_key][key][pos][str(year)]:
                                if team != "NHL":
                                    if team in team_map_by_year[over_key][str(year)]:
                                        if key == "Skater":
                                            for header_value in team_map_by_year[over_key][str(year)][team]:
                                                totals[over_key][key][pos][str(year)][team][header_value] = team_map_by_year[over_key][str(year)][team][header_value]

                                        for header_value in totals[over_key][key][pos][str(year)][team]:
                                            if header_value not in totals[over_key][key][pos][str(year)]["NHL"]:
                                                totals[over_key][key][pos][str(year)]["NHL"][header_value] = 0.0

                                            totals[over_key][key][pos][str(year)]["NHL"][header_value] += totals[over_key][key][pos][str(year)][team][header_value]

    return totals

def calculate_year_games_by_team(year, for_playoffs):
    teams = {}
    try:
        response, player_page = url_request(current_year_stats_url.format("playoffs" if for_playoffs else "leagues", year + 1))
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
            return None
        else:
            raise

    table_name = "^teams$" if for_playoffs else "^stats"

    team_abbr_map = {}

    if for_playoffs:
        original_player_page = player_page

        try:
            response, player_page = url_request(current_year_stats_url.format("leagues", year + 1))
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                return None
            else:
                raise

        table = player_page.find("table", id="stats")
        if not table:
            comments = player_page.find_all(string=lambda text: isinstance(text, Comment))
            for c in comments:
                temp_soup = BeautifulSoup(c, "lxml")
                temp_table = temp_soup.find("table", id="stats")
                if temp_table:
                    table = temp_table
                    break

        if table:
            standard_table_rows = table.find("tbody").find_all("tr")
            for row in standard_table_rows:
                classes = row.get("class")
                if not classes or not "thead" in classes:
                    team_row = row.find("td", {"data-stat" : "team_name"})
                    team_link = row.find("td", {"data-stat" : "team_name"}).find("a")
                    if not team_link:
                        continue
                    team_name = team_row.find(text=True)
                    team_abbr = team_link["href"].split("/")[2].upper()
                    if not team_abbr in team_abbr_map:
                        team_abbr_map[team_name] = team_abbr
        
        player_page = original_player_page

    tables = player_page.findAll("table", id=re.compile(table_name))
    if not tables:
        comments = player_page.find_all(string=lambda text: isinstance(text, Comment))
        for c in comments:
            temp_soup = BeautifulSoup(c, "lxml")
            temp_tables = temp_soup.findAll("table", id=re.compile(table_name))
            if temp_tables:
                tables = temp_tables
                break

    for table in tables:
        standard_table_rows = table.find("tbody").find_all("tr")
        header_columns = table.find("thead").find_all("th")
            
        header_values = []
        for header in header_columns:
            header_text = header.find(text=True)
            if header_text:
                header_values.append(header_text.strip())
            else:
                header_values.append(None)

        standard_table_rows = table.find("tbody").find_all("tr")

        for row in standard_table_rows:
            classes = row.get("class")
            if not classes or not "thead" in classes:
                if for_playoffs:
                    team_name = row.find("td", {"data-stat" : "team_name"}).find(text=True)
                    if team_name == "League Average":
                        continue
                    team_abbr = team_abbr_map[team_name]
                else:
                    team_link = row.find("td", {"data-stat" : "team_name"}).find("a")
                    if not team_link:
                        continue
                    team_abbr = team_link["href"].split("/")[2].upper()

                columns = row.find_all("td", recursive=False)
                for column in columns:
                    if hasattr(column, "data-stat"):
                        if column["data-stat"] == "games":
                            header_value = "T-GP"
                        elif column["data-stat"] == "goals":
                            header_value = "T-GF"
                        elif column["data-stat"] == "goals_against" or column["data-stat"] == "opp_goals":
                            header_value = "T-GA"
                        elif column["data-stat"] == "points":
                            header_value = "T-PTS"
                        else:
                            continue

                        column_contents = column.find(text=True)
                        column_value = 0
                        if column_contents:
                            column_value = int(column_contents)
                        
                        if not team_abbr in teams:
                            teams[team_abbr] = {}
                        if not header_value in teams[team_abbr]:
                            teams[team_abbr][header_value] = 0.0

                        if header_value == "T-GF":
                            wins_shootout = row.find("td", {"data-stat" : "wins_shootout"})
                            if wins_shootout:
                                wins_shootout_str = wins_shootout.find(text=True)
                                if wins_shootout_str and wins_shootout_str.isdigit():
                                    column_value += int(wins_shootout_str)
                        elif header_value == "T-GA":
                            losses_shootout = row.find("td", {"data-stat" : "losses_shootout"})
                            if losses_shootout:
                                losses_shootout_str = losses_shootout.find(text=True)
                                if losses_shootout_str and losses_shootout_str.isdigit():
                                    column_value += int(losses_shootout_str)
                                
                        teams[team_abbr][header_value] = column_value

    return teams

def url_request(url, timeout=30, retry_403=True):
    gateway_session = requests.Session()
    gateway_session.mount("https://www.hockey-reference.com", gateway)
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
