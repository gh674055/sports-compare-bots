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
import threading
import ssl
from requests_ip_rotator import ApiGateway
import signal

league_totals_url = "https://www.fangraphs.com/api/leaders/major-league/data?age=0&pos={}&stats={}&lg={}&qual=0&season={}&season1={}&month=0&hand=&team=0%2Css&pageitems=30&pagenum=1&ind=0&rost=0&players=0&type={}"
constants_url = "https://www.fangraphs.com/guts.aspx?type=cn"
park_factors_url = "https://www.fangraphs.com/guts.aspx?type=pf&teamid=0&season={}"

start_year = 1871
end_year = datetime.date.today().year

league_years = {
    "NNL" : range(1920, 1932),
    "ECL" : range(1923, 1929),
    "ANL" : range(1929, 1930),
    "EWL" : range(1932, 1933),
    "NSL" : range(1932, 1933),
    "NN2" : range(1933, 1949),
    "NAL" : range(1937, 1949),
    "AA" : range(1882, 1892),
    "FL" : range(1914, 1916),
    "PL" : range(1890, 1891),
    "UA" : range(1884, 1885),
    "NA" : range(1871, 1876),
    "AL" : range(1901, end_year + 1),
    "NL" : range(1876, end_year + 1),
    "MLB" : range(start_year, end_year + 1)
}

teams_to_abbr = {
    "Angels" : [{
        "start" : None,
        "end" : 1964,
        "abbv" : "LAA"
    },{
        "start" : 1965,
        "end": 1996,
        "abbv" : "CAL"
    },{
        "start" : 1997,
        "end" : 2004,
        "abbv" : "ANA"
    },{
        "start" : 2005,
        "end" : None,
        "abbv" : "LAA"
    }],
    "Orioles" : "BAL",
    "Red Sox" : "BOS",
    "White Sox" : "CHW",
    "White Stockings" : "CHI",
    "Guardians" : "CLE",
    "Indians" : "CLE",
    "Cleveland" : "CLE",
    "Tigers" : "DET",
    "Royals" : "KCR",
    "Twins" : "MIN",
    "Yankees" : "NYY",
    "Athletics"  : [{
        "start" : None,
        "end": 1900,
        "abbv" : "ATH"
    },{
        "start" : 1901,
        "end": 1954,
        "abbv" : "PHA"
    },{
        "start" : 1955,
        "end" : 1967,
        "abbv" : "KCA"
    },{
        "start" : 1968,
        "end" : None,
        "abbv" : "OAK"
    }],
    "Whites" : "PHI",
    "Mariners" : "SEA",
    "Maroons" : "SLM",
    "Highlanders" : "NYY",
    "Rebels" : "PBS",
    "Rays" : "TBR",
    "Devil Rays" : "TBD",
    "Rangers" : "TEX",
    "Blue Jays" : "TOR",
    "Diamondbacks" : "ARI",
    "Braves" : [{
        "start" : None,
        "end" : 1952,
        "abbv" : "BSN"
    },{
        "start" : 1953,
        "end" : 1965,
        "abbv" : "MLN"
    },{
        "start" : 1966,
        "end" : None,
        "abbv" : "ATL"
    }],
    "Cubs" : "CHC",
    "Keystones" : "PHK",
    "Reds" : [{
        "start" : None,
        "end" : 1883,
        "abbv" : "CIN"
    },{
        "start" : 1884,
        "end" : 1884,
        "abbv" : ["BOS", "CIN"]
    },{
        "start" : 1885,
        "end" : 1889,
        "abbv" : "CIN"
    },{
        "start" : 1890,
        "end" : 1891,
        "abbv" : ["BOS", "CIN"]
    },{
        "start" : 1892,
        "end" : None,
        "abbv" : "CIN"
    }],
    "Redlegs" : "CIN",
    "Rockies" : "COL",
    "Olympics" : "OLY",
    "Pilots" : "SEP",
    "Canaries" : "BAL",
    "Marlins" : [{
        "start" : None,
        "end" : 2011,
        "abbv" : "FLA"
    },{
        "start" : 2012,
        "end" : None,
        "abbv" : "MIA"
    }],
    "Astros" : "HOU",
    "Colt .45's" : "HOU",
    "Dodgers" : [{
        "start" : None,
        "end" : 1957,
        "abbv" : "BRO"
    },{
        "start" : 1958,
        "end" : None,
        "abbv" : "LAD"
    }],
    "Superbras" : "BRO",
    "Robins" : "BRO",
    "Brewers" : "MIL",
    "Nationals" : [{
        "start" : None,
        "end" : 1872,
        "abbv" : "NAT"
    },{
        "start" : 1873,
        "end" : 1875,
        "abbv" : "WAS"
    },{
        "start" : 1876,
        "end" : 1889,
        "abbv" : "WHS"
    },{
        "start" : 1890,
        "end" : None,
        "abbv" : "WSN"
    }],
    "Mets" : "NYM",
    "Phillies" : "PHI",
    "Pirates" : "PIT",
    "Cardinals" : "STL",
    "Padres" : "SDP",
    "Giants" : [{
        "start" : None,
        "end" : 1957,
        "abbv" : "NYG"
    },{
        "start" : 1958,
        "end" : None,
        "abbv" : "SFG"
    }],
    "Expos" : "MON",
    "Spiders" : "CLV",
    "Senators" : [{
        "start" : None,
        "end" : 1899,
        "abbv" : "WHS"
    },{
        "start" : 1900,
        "end" : 1960,
        "abbv" : "WSH"
    },
    {
        "start" : 1961,
        "end" : None,
        "abbv" : "WSA"
    }],
    "Rustlers" : "BSN",
    "Perfectos" : "STL",
    "Americans" : "BOS",
    "Naps" : "CLE",
    "Bronchos" : "CLE",
    "Brown Stockings" : "STL",
    "Browns" : [{
        "start" : None,
        "end" : 1898,
        "abbv" : "STL"
    },{
        "start" : 1899,
        "end" : None,
        "abbv" : "SLB"
    }],
    "Eclipse" : "LOU",
    "Infants" : "CLE",
    "Colonels" : "LOU",
    "Grooms" : "BRO",
    "Grays" : [{
        "start" : None,
        "end" : 1877,
        "abbv" : "LOU"
    },{
        "start" : 1878,
        "end" : 1878,
        "abbv" : ["PRO", "MLG"]
    },{
        "start" : 1879,
        "end" : None,
        "abbv" : "PRO"
    }],
    "Beaneaters" : "BSN",
    "Red Stockings" : [{
        "start" : None,
        "end" : 1889,
        "abbv" : "STL"
    },{
        "start" : 1890,
        "end" : None,
        "abbv" : "SLB"
    }],
    "Doves" : "BSN",
    "Bees" : "BSN",
    "Bisons" : "BUF",
    "Blues" : [{
        "start" : None,
        "end" : 1878,
        "abbv" : "IND"
    },{
        "start" : 1879,
        "end" : None,
        "abbv" : "CLV"
    }],
    "Alleghenys" : "PIT",
    "Quicksteps" : "WIL",
    "Quakers" : "PHI",
    "Mutuals" : "NYU",
    "Dark Blues" : "HAR",
    "Trojans" : "TRO",
    "Haymakers" : "TRO",
    "Metropolitans" : "NYP",
    "Wolverines" : "DTN",
    "Ruby Legs" : "WOR"
}

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "MLBCompareRedditBot"
}

#request_headers= {}

logname = "mlb-constants.log"
logger = logging.getLogger("mlb-constants")
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler = TimedRotatingFileHandler(logname, when="midnight", interval=1)
handler.suffix = "%Y%m%d"
handler.setFormatter(formatter)
logger.addHandler(handler)
streamhandler = logging.StreamHandler(sys.stdout)
streamhandler.setLevel(logging.DEBUG)
logger.addHandler(streamhandler)

ssl._create_default_https_context = ssl._create_unverified_context

def main(gateway):
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
        get_totals(year, totals, gateway)
    else:
        totals = get_totals(None, None, gateway)

    with open("yearly_totals.json", "w") as file:
        file.write(json.dumps(totals, indent=4, sort_keys=True))

    constants = None
    if year:
        with open("yearly_constants.json", "r") as file:
            constants = json.load(file)
        get_constants(year, constants, gateway)
    else:
        constants = get_constants(None, constants, gateway)

    with open("yearly_constants.json", "w") as file:
        file.write(json.dumps(constants, indent=4, sort_keys=True))

    if year:
        with open("yearly_park_factors.json", "r") as file:
            park_factors = json.load(file)
        get_park_factors(year, park_factors, gateway)
    else:
        park_factors = get_park_factors(None, None, gateway)

    with open("yearly_park_factors.json", "w") as file:
        file.write(json.dumps(park_factors, indent=4, sort_keys=True))

def get_totals(single_year, totals, gateway, log=True):
    if log:
        logger.info("Getting league total data for year " + str(single_year))

    format_strs = {
        "Batter" : "bat",
        "Pitcher" : "pit"
    }

    if not totals:
        totals = {
            "MLB" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "AL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "NL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "FL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "AA" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "PL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "UA" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "NNL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "ECL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "ANL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "EWL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "NSL" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "NN2" : {
                "Batter" : {},
                "Pitcher" : {}
            },
            "NAL" : {
                "Batter" : {},
                "Pitcher" : {}
            }
        }
    
    years = None
    if single_year:
        years = [single_year]
    else:
        years = range(start_year, end_year + 1)

    total_years = len(years)

    with requests.Session() as gateway_session:
        #gateway_session.mount("https://www.fangraphs.com", gateway)

        for league in list(totals):
            for key in list(totals[league]):
                if log:
                    logger.info("Getting league total data for " + league + " : " + key)
                current_percent = 10
                for index, year in enumerate(years):
                    if year in league_years[league]:
                        league_str = "ALL" if league == "MLB" else league

                        league_totals_url = "https://www.fangraphs.com/api/leaders/major-league/data?age=0&pos={}&stats={}&lg={}&qual=0&season={}&season1={}&month=0&hand=&team=0%2Css&pageitems=30&pagenum=1&ind=0&rost=0&players=0&type={}"
                        league_excluding_pitchers_url = "https://www.fangraphs.com/api/leaders/major-league/data?age=0&pos=np&stats=bat&lg={}&qual=0&season={}&season1={}&month=0&hand=&team=0%2Css&pageitems=30&pagenum=1&ind=0&rost=0&players=0&type=0"

                        data = url_request_json(gateway_session, league_totals_url.format("all", format_strs[key], league_str.lower(), year, year, "0"), log)["data"]
                        if data:
                            totals[league][key][str(year)] = data[0]

                        if key == "Batter" and league != "MLB":                            
                            pitcherless_values = url_request_json(gateway_session, league_totals_url.format("np", "bat", league_str.lower(), year, year, "0"), log)["data"]
                            if pitcherless_values:
                                totals[league][key][str(year)]["pitcherless_values"] = pitcherless_values[0]

                    count = index + 1
                    percent_complete = 100 * (count / total_years)
                    if not single_year and count != 1 and percent_complete >= current_percent:
                        if log:
                            logger.info(str(current_percent) + "%")
                        current_percent += 10

    return totals

def get_constants(year, constants, gateway, log=True):
    if log:
        logger.info("Getting league constants data for year " + str(year))

    if not constants:
        constants = {}
    
    response, player_page = url_request(constants_url, gateway, log)

    table = player_page.find("div", id="content").find("table")

    header_columns = table.find("thead").find_all("th")
    header_values = []
    for header in header_columns:
        header_values.append(header.find(text=True).strip())

    standard_table_rows = table.find("tbody").find_all("tr")
    total_rows = len(standard_table_rows)
    current_percent = 10

    for index, row in enumerate(standard_table_rows):
        columns = row.find_all("td", recursive=False)
        row_year = None
        for sub_index, column in enumerate(columns):
            header_value = header_values[sub_index]
            column_contents = column.find(text=True)
            if header_value == "Season":
                row_year = int(column_contents)
                if year and year != row_year:
                    break
                constants[str(row_year)] = {}
            else:
                column_value = float(column_contents)
                constants[str(row_year)][header_value] = column_value

        count = index + 1
        percent_complete = 100 * (count / total_rows)
        if not year and count != 1 and percent_complete >= current_percent:
            if log:
                logger.info(str(current_percent) + "%")
            current_percent += 10

    return constants

def get_park_factors(single_year, park_factors, gateway, log=True):
    if log:
        logger.info("Getting league park factors data for year " + str(single_year))

    if not park_factors:
        park_factors = {}

    years = None
    if single_year:
        years = [single_year]
    else:
        years = range(start_year, end_year + 1)

    total_years = len(years)

    current_percent = 10
    for index, year in enumerate(years):
        try:
            response, player_page = url_request(park_factors_url.format(year), gateway, log)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                continue
            else:
                raise

        table = player_page.find("div", id="content").find("table")
        if not table:
            continue

        park_factors[str(year)] = {}

        header_columns = table.find("thead").find_all("th")
        header_values = []
        for header in header_columns:
            header_values.append(header.find(text=True).strip())

        standard_table_rows = table.find("tbody").find_all("tr")

        for row in standard_table_rows:
            columns = row.find_all("td", recursive=False)
            row_team = None
            for sub_index, column in enumerate(columns):
                header_value = header_values[sub_index]
                if header_value != "Season":
                    column_contents = column.find(text=True)
                    if not column_contents:
                        continue
                    
                    column_contents = column_contents.strip()
                    if header_value == "Team":
                        if column_contents in teams_to_abbr:
                            row_team = teams_to_abbr[column_contents]
                            if not isinstance(row_team, str):
                                for row in row_team:
                                    row_start_year = row["start"]
                                    row_end_year = row["end"]
                                    if (not row_start_year or year >= row_start_year) and (not row_end_year or year <= row_end_year):
                                        row_team = row["abbv"]
                            
                            if isinstance(row_team, list):
                                for ind_row_team in row_team:
                                    if not isinstance(ind_row_team, str):
                                        raise Exception("Unknown team " + str(ind_row_team) + " for year " + str(year))
                                    park_factors[str(year)][ind_row_team] = {} 
                            else:
                                if not isinstance(row_team, str):
                                    raise Exception("Unknown team " + str(row_team) + " for year " + str(year))
                                park_factors[str(year)][row_team] = {}
                        else:
                            break
                    else:
                        if column_contents:
                            column_value = int(column_contents)
                            if isinstance(row_team, list):
                                for ind_row_team in row_team:
                                    park_factors[str(year)][ind_row_team][header_value] = column_value 
                            else:
                                park_factors[str(year)][row_team][header_value] = column_value

        count = index + 1
        percent_complete = 100 * (count / total_years)
        if not single_year and count != 1 and percent_complete >= current_percent:
            if log:
                logger.info(str(current_percent) + "%")
            current_percent += 10

    return park_factors

def url_request_json(session, url, log, timeout=30):
    failed_counter = 0
    while(True):
        try:
            response = session.get(url, timeout=timeout, headers=request_headers)
            response.raise_for_status()
            return json.loads(response.content)
        except Exception:
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

def url_request(url, gateway, log, timeout=30):
    gateway_session = requests.Session()
    #gateway_session.mount("https://www.fangraphs.com", gateway)
    failed_counter = 0
    while(True):
        try:
            response = gateway_session.get(url, timeout=timeout, headers=request_headers)
            response.raise_for_status()
            text = response.content

            bs = BeautifulSoup(text, "html5lib")

            if not bs.contents:
                raise requests.exceptions.HTTPError("Page is empty!")
            return response, bs
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 403:
                raise
            else:
                failed_counter += 1
                if failed_counter > max_request_retries:
                    raise
        except Exception:
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
    #gateway =  ApiGateway("https://www.fangraphs.com", verbose=True)
    #endpoints = gateway.start(force=True)
    gateway = None

    def exit_gracefully(signum, frame):
        sys.exit(signum)
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)

    try:
        main(gateway)
    finally:
        #gateway.shutdown(endpoints)
        pass
