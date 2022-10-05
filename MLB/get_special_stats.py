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
import unidecode
import dateutil.parser
from nameparser import HumanName
from urllib.parse import urlparse, parse_qs
import mlb

no_hit_format = "https://www.baseball-reference.com/friv/no-hitters-and-perfect-games.shtml"
cycles_format = "https://www.baseball-almanac.com/hitting/Major_League_Baseball_Players_to_hit_for_the_cycle.shtml"
player_search_url_format = "https://www.baseball-reference.com/search/search.fcgi?search={}"

max_request_retries = 3
retry_failure_delay = 3

playoff_no_hitters = [
    dateutil.parser.parse("October 8, 1956").date(),
    dateutil.parser.parse("October 6, 2010").date()
]

special_stats = {
    "no_hit" : {},
    "perfect" : {},
    "cycle" : {}
}

request_headers = {
    "User-Agent" : "MLBCompareRedditBot"
}

request_headers= {}

manual_map = {
    "Andy Thornton" : "thornan01",
    "John Bates" : "batesjo02",
    "Frank Baker" : "bakerfr01",
    "George Burns" : "burnsge01",
    "Ivan DeJesus" : "dejesiv01",
    "Jose Reyes" : "reyesjo01",
    "CarlosGuillen" : "guillca01",
    "Gary Mathews, Jr." : "matthga02",
    "Mike Cuddyer" : "cuddymi01",
    "Jose Abreu" : "abreujo02"
}

team_name_info = None
with open ("team_name_info.json", "r") as file:
    team_name_info = json.load(file)

def main():
    print("Starting no hitters")
    request = urllib.request.Request(no_hit_format, headers=request_headers)
    response = url_request(request)

    player_page = BeautifulSoup(response, "html.parser")

    table = player_page.find("table", {"id" : "no_hitters_individual"})
    if not table:
        comments = player_page.find_all(string=lambda text: isinstance(text, Comment))
        for c in comments:
            temp_soup = BeautifulSoup(c, "html.parser")
            temp_table = temp_soup.find("table", {"id" : "no_hitters_individual"})
            if temp_table:
                table = temp_table
                break

    if table:
        standard_table_rows = table.find("tbody").find_all("tr")
        for row in standard_table_rows:
            if not row.get("class") or not "thead" in row.get("class"):
                url = urlparse(row.find("td", {"data-stat" : "player"}).find("a").get("href"))
                path = url.path[1:].split("/")
                player_id = path[2][:-6]
                date_row = row.find("td", {"data-stat" : "date_game"})
                team = row.find("td", {"data-stat" : "team_ID"}).find(text=True)
                date_row_arr = date_row.get("csk").split(".")
                time_int = int(date_row_arr[1][-1])
                date_time = dateutil.parser.parse(date_row_arr[0]).replace(hour=time_int)
                if player_id not in special_stats["no_hit"]:
                    special_stats["no_hit"][player_id] = []
                
                game_obj = {
                    "date" : str(date_time),
                    "team" : team,
                    "is_playoffs" : date_time.date() in playoff_no_hitters
                }

                special_stats["no_hit"][player_id].append(game_obj)

                is_perfect = row.find("td", {"data-stat" : "perfect_game"}).find(text=True)
                if is_perfect:
                    if player_id not in special_stats["perfect"]:
                        special_stats["perfect"][player_id] = []
                    special_stats["perfect"][player_id].append(game_obj)
    
    print("Starting cycles")

    request = urllib.request.Request(cycles_format, headers=request_headers)
    response = url_request(request)

    player_page = BeautifulSoup(response, "html.parser")

    table = player_page.find("table")
    if not table:
        comments = player_page.find_all(string=lambda text: isinstance(text, Comment))
        for c in comments:
            temp_soup = BeautifulSoup(c, "html.parser")
            temp_table = temp_soup.find("table", {"id" : "no_hitters_individual"})
            if temp_table:
                table = temp_table
                break

    manual_date_maps = {
        "freembu01" : {
            "1903-07-21" : "1903-06-21"
        },
        "cooledu01" : {
            "1904-06-20" : "2020-01-01 02:00:00"
        },
        "bakerfr01" : {
            "1911-07-03" : "1911-07-03 02:00:00"
        },
        "wagneho01" : {
            "1912-08-22" : "1912-08-22 02:00:00"
        }
    }

    playoff_cycles = {
        "holtbr01" : {
            "2018-10-08"
        }
    }
    
    if table:
        rows = table.find_all("tr")
        current_percent = 10
        count = 0
        for row in rows:
            columns = row.find_all("td")
            if len(columns) == 5 and columns[0].find(text=True) != "MLB #":
                name = columns[1].find(text=True)
                date = dateutil.parser.parse(columns[3].find(text=True)).date()
                da_year = date.year
                team_str = columns[2].find(text=True)
                team = None
                datestr = str(date)


                if team_str in team_name_info:
                    for abbr in team_name_info[team_str]:
                        if da_year in team_name_info[team_str][abbr]:
                            team = abbr
                            break
                
                if not team:
                    if team_str in team_name_info:
                        for abbr in team_name_info[team_str]:
                            team = abbr

                if not team:
                    raise Exception("Unknown team " + team_str + " for year " + str(da_year))

                if name in manual_map:
                    name = manual_map[name]

                time_frame = {
                    "qualifiers" : []
                }
                time_frame["time_start"] = date
                time_frame["time_end"] = date
                time_frame["type"] = "date"

                player_id = mlb.get_player(name, [time_frame])[0]

                if player_id in manual_date_maps and datestr in manual_date_maps[player_id]:
                    datestr = manual_date_maps[player_id][datestr]

                is_playoffs = player_id in playoff_cycles and datestr in playoff_cycles[player_id]

                if not player_id:
                    print("No match for player " + name)
                else:
                    if player_id not in special_stats["cycle"]:
                        special_stats["cycle"][player_id] = []
                    special_stats["cycle"][player_id].append({
                        "date" : datestr,
                        "is_playoffs" : is_playoffs,
                        "team" : team
                    })
                
            count += 1
            percent_complete = 100 * (count / len(rows))
            if count != 1 and percent_complete >= current_percent:
                print(str(current_percent) + "%")
                current_percent += 10
    
    current_percent = 10
    count = 0
    player_ids_to_remove = set()
    for player_id in special_stats["cycle"]:
        temp_cycles = special_stats["cycle"][player_id]
        da_cyles = []
        for temp_cycle in temp_cycles:
            date_str = temp_cycle["date"]
            if not date_str.endswith("00:00") and dateutil.parser.parse(date_str).year >= 1901:
                da_cyles.append(date_str)

        if da_cyles:
            player_compare_str = "!mlbcompare <" + player_id + ">" + "[" + "+".join(da_cyles) + "]"
            player_type = {
                "da_type" : "Batter"
            }

            player_datas = mlb.handle_player_string(player_compare_str, player_type, None, False, None)[0]

            total_games = 0
            for player_data in player_datas:
                if player_data["stat_values"]["Player"] == ["No Player Match!"]:
                    continue
                if "all_rows" in player_data["stat_values"]:
                    for sub_row in player_data["stat_values"]["all_rows"]:
                        hits = sub_row.get("H", 0)
                        doubles = sub_row.get("2B", 0)
                        triples = sub_row.get("3B", 0)
                        homers = sub_row.get("HR", 0)
                        singles = hits - (doubles + triples + homers)

                        if singles and doubles and triples and homers:
                            total_games += 1
            
            if total_games != len(da_cyles):
                print("Bad player " + player_id + " : " + str(total_games) + " " + str(len(da_cyles)))
                player_ids_to_remove.add(player_id)
        
        count += 1
        percent_complete = 100 * (count / len(special_stats["cycle"]))
        if count != 1 and percent_complete >= current_percent:
            print(str(current_percent) + "%")
            current_percent += 10
    
    for player_id in player_ids_to_remove:
        del special_stats["cycle"][player_id]
    
    with open("special_stats.json", "w") as file:
        file.write(json.dumps(special_stats, indent=4, sort_keys=True))
 
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
        print("Retrying in " + str(retry_failure_delay) + " seconds to allow fangraphs to chill")
        time_to_wait = int(math.ceil(float(retry_failure_delay)/float(delay_step)))
        for i in range(retry_failure_delay, 0, -time_to_wait):
            print(i)
            time.sleep(time_to_wait)
        print("0")

if __name__ == "__main__":
    main()
