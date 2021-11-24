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
import decimal
import numexpr
import threading
import lxml
import cchardet
import ssl

league_totals_url = "https://pro-football-reference.com/years/{}/passing.htm"

max_request_retries = 3
retry_failure_delay = 3

request_headers = {
    "User-Agent" : "NFLCompareRedditBot"
}

start_year = 1936
end_year = 2021
skip_current_year = True

current_year_standings_url = "https://www.pro-football-reference.com/years/{}"

logname = "nfl-constants.log"
logger = logging.getLogger("nfl-constants")
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler = TimedRotatingFileHandler(logname, when="midnight", interval=1)
handler.suffix = "%Y%m%d"
handler.setFormatter(formatter)
logger.addHandler(handler)
streamhandler = logging.StreamHandler(sys.stdout)
streamhandler.setLevel(logging.DEBUG)
logger.addHandler(streamhandler)

stat_groups = {
    "Passing" : {
        "Cmp" : {
            "positive" : True
        },
        "Att" : {
            "positive" : True
        },
        "Att1D" : {
            "positive" : True,
            "display" : False
        },
        "Cmp%": {
            "positive" : True,
            "round" : "percent"
        },
        "Yds": {
            "positive" : True
        },
        "TD": {
            "positive" : True
        },
        "Int": {
            "positive" : False
        },
        "TD/Int": {
            "positive" : True,
            "round" : 2,
            "isinf" : "TD"
        },
        "Sk": {
            "positive" : False,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "SkYds": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "Y/C": {
            "positive" : True,
            "round" : 2
        },
        "Y/A": {
            "positive" : True,
            "round" : 2
        },
        "AY/A": {
            "positive" : True,
            "round" : 2
        },
        "NY/A": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "ANY/A": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "TD%": {
            "positive" : True,
            "round" : "percent"
        },
        "Int%": {
            "positive" : False,
            "round" : "percent"
        },
        "Sk%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "Yds/Sk": {
            "positive" : False,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "Rate": {
            "positive" : True,
            "round" : 2
        },
        "QBR": {
            "positive" : True,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2006,
                "game-np" : 2006
            }
        },
        "Cmp/G" : {
            "positive" : True,
            "round" : 2
        },
        "Att/G" : {
            "positive" : True,
            "round" : 2
        },
        "Yds/G": {
            "positive" : True,
            "round" : 2
        },
        "TD/G": {
            "positive" : True,
            "round" : 2
        },
        "Int/G": {
            "positive" : False,
            "round" : 2
        },
        "Sk/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "SkYds/G": {
            "positive" : False,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "Cmp/17G" : {
            "positive" : True,
            "round" : 2
        },
        "Att/17G" : {
            "positive" : True,
            "round" : 2
        },
        "Yds/17G": {
            "positive" : True,
            "round" : 2
        },
        "TD/17G": {
            "positive" : True,
            "round" : 2
        },
        "Int/17G": {
            "positive" : False,
            "round" : 2
        },
        "Sk/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        },
        "SkYds/17G": {
            "positive" : False,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1969,
                "game-np" : 1970
            }
        }
    },
    "Era Adjusted Passing" : {
        "Cmp%+": {
            "positive" : True,
        },
        "Y/A+": {
            "positive" : True,
        },
        "AY/A+": {
            "positive" : True,
        },
        "NY/A+": {
             "positive" : True,
             "valid_since" : {
                 "season" : 1969,
                 "game" : 1970
             }
        },
        "ANY/A+" : {
            "positive" : True,
            "valid_since" : {
                 "season" : 1969,
                 "game" : 1970
            }
        },
        "TD%+": {
            "positive" : True,
        },
        "Int%+": {
            "positive" : True,
        },
        "Sk%+": {
            "positive" : True,
            "valid_since" : {
                "season" : 1969,
                "game" : 1970
            }
        },
        "Rate+": {
            "positive" : True,
        },
        "TtlYds": {
            "positive" : True
        },
        "TtlTD": {
            "positive" : True
        },
        "TtlTDTnv": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "Tnv": {
            "positive" : False,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "TD/Tnv": {
            "positive" : True,
            "round" : 2,
            "isinf" : "TtlTDTnv",
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "Pick6": {
            "positive" : False,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "Yds/G": {
            "positive" : True,
            "round" : 2
        },
        "TD/G": {
            "positive" : True,
            "round" : 2
        },
        "Tnv/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "Yds/17G": {
            "positive" : True,
            "round" : 2
        },
        "TD/17G": {
            "positive" : True,
            "round" : 2
        },
        "TtlTD%": {
            "positive" : True,
            "round" : "percent",
            "display" : False
        },
        "Tnv/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "Pick6/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "4QC" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "GWD" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "4QC/17G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "GWD/17G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "QBW" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "QBW/17G" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "QBL" : {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "QBL/17G" : {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "QBT" : {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "QBT/17G" : {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "Rec" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "Rec/17G" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        },
        "W/L%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1950,
                "game" : 1950
            }
        }
    },
    "Advanced/Passing" : {
        "Cmp" : {
            "positive" : True,
            "display" : False
        },
        "Att" : {
            "positive" : True,
            "display" : False
        },
        "Sk" : {
            "positive" : False,
            "display" : False
        },
        "Rush" : {
            "positive" : True,
            "display" : False
        },
        "Rec" : {
            "positive" : True,
            "display" : False
        },
        "Touch" : {
            "positive" : True,
            "display" : False
        },
        "1D": {
            "positive" : True,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "1D/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Pass1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Pass1D%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rush1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rush1D%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rec1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rec1D%": {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "CAY-RAW": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "CAY": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "IAY-RAW": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "IAY": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "AYD": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAC-RAW": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAC": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "OnTgt": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2019,
                "game" : None
            }
        },
        "OnTgt%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2019,
                "game" : None
            }
        },
        "BadTh": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "BadTh%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : None
            }
        },
        "ThAwy": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Spikes": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : None
            }
        },
        "ThAwyTgt": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2019
            }
        },
        "SpikesTgt": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2019
            }
        },
        "Drops": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Drop%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : None
            }
        },
        "Bltz": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Bltz%": {
            "positive" : False,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Hrry": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Hrry%": {
            "positive" : False,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Hits": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Hit%": {
            "positive" : False,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Prss": {
            "positive" : False,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Prss%": {
            "positive" : False,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "LngPass": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },
        "YBContact": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAContact": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YBC/Rush": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAC/Rush": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "LngRush": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },
        "BrkTkl": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "BrkTkl/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "RushBrkTkl": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rush/BrkTkl": {
            "positive" : False,
            "round" : 2,
            "skipzero" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "RecBrkTkl": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rec/BrkTkl": {
            "positive" : False,
            "round" : 2,
            "skipzero" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        }
    },
    "Rushing" : {
        "Att": {
            "positive" : True
        },
        "Att1D" : {
            "positive" : True,
            "display" : False
        },
        "Yds": {
            "positive" : True
        },
        "Yds/Att": {
            "positive" : True,
            "round" : 2
        },
        "TD": {
            "positive" : True
        },
        "Fmb": {
            "positive" : False,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "FmbLst": {
            "positive" : False,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "TD%": {
            "positive" : True,
            "round" : "percent"
        },
        "Fmb%": {
            "positive" : False,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "FmbLst%": {
            "positive" : False,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "Att/G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/G": {
            "positive" : True,
            "round" : 2
        },
        "TD/G": {
            "positive" : True,
            "round" : 2
        },
        "Fmb/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "FmbLst/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "Att/17G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/17G": {
            "positive" : True,
            "round" : 2
        },
        "TD/17G": {
            "positive" : True,
            "round" : 2
        },
        "Fmb/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "FmbLst/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        }
    },
    "Advanced/Rushing" : {
        "Rush" : {
            "positive" : True,
            "display" : False
        },
        "Rec" : {
            "positive" : True,
            "display" : False
        },
        "Tgt": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1992,
                "game" : 1992
            }
        },
        "Touch" : {
            "positive" : True,
            "display" : False
        },
        "RecYds" : {
            "positive" : True,
            "display" : False
        },
        "RecTD" : {
            "positive" : True,
            "display" : False
        },
        "Int" : {
            "positive" : False,
            "display" : False
        },
        "1D": {
            "positive" : True,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "1D/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rush1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rush1D%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rec1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rec1D%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Pass1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Pass1D%": {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "YBContact": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAContact": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YBC/Rush": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAC/Rush": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "LngRush": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },   
        "YBCatch": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YACatch": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YBC/Rec": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAC/Rec": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Drop": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Drop%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rate": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "LngRec": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },
        "BrkTkl": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "BrkTkl/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "RushBrkTkl": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rush/BrkTkl": {
            "positive" : False,
            "round" : 2,
            "skipzero" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "RecBrkTkl": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rec/BrkTkl": {
            "positive" : False,
            "round" : 2,
            "skipzero" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        }
    },
    "Receiving" : {
        "Rec": {
            "positive" : True
        },
        "Rec1D" : {
            "positive" : True,
            "display" : False
        },
        "Tgt": {
            "positive" : True,
            "valid_since" : {
                "season" : 1992,
                "game" : 1992
            }
        },
        "Catch%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1992,
                "game" : 1992
            }
        },
        "Yds": {
            "positive" : True
        },
        "Yds/Rec": {
            "positive" : True,
            "round" : 2	
        },
        "Yds/Tgt": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1992,
                "game" : 1992
            }
        },
        "TD": {
            "positive" : True
        },
        "TD%": {
            "positive" : True,
            "round" : "percent"
        },
        "Rec/G": {
            "positive" : True,
            "round" : 2
        },
        "Tgt/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1992,
                "game" : 1992
            }
        },
        "Yds/G": {
            "positive" : True,
            "round" : 2
        },
        "TD/G": {
            "positive" : True,
            "round" : 2
        },
        "Rec/17G": {
            "positive" : True,
            "round" : 2
        },
        "Tgt/17G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1992,
                "game" : 1992
            }
        },
        "Yds/17G": {
            "positive" : True,
            "round" : 2
        },
        "TD/17G": {
            "positive" : True,
            "round" : 2
        }
    },
    "Advanced/Receiving" : {
        "Rush" : {
            "positive" : True,
            "display" : False
        },
        "Rec" : {
            "positive" : True,
            "display" : False
        },
        "Tgt": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1992,
                "game" : 1992
            }
        },
        "Touch" : {
            "positive" : True,
            "display" : False
        },
        "RecYds" : {
            "positive" : True,
            "display" : False
        },
        "RecTD" : {
            "positive" : True,
            "display" : False
        },
        "Int" : {
            "positive" : False,
            "display" : False
        },
        "1D": {
            "positive" : True,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "1D/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rec1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rec1D%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rush1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Rush1D%": {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Pass1D": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "Pass1D%": {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1994,
                "game" : 2018
            }
        },
        "YBCatch": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YACatch": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YBC/Rec": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAC/Rec": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Drop": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Drop%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rate": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "LngRec": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },
        "YBContact": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAContact": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YBC/Rush": {
            "positive" : True,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "YAC/Rush": {
            "positive" : True,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "LngRush": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },
        "BrkTkl": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "BrkTkl/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "RecBrkTkl": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rec/BrkTkl": {
            "positive" : False,
            "round" : 2,
            "skipzero" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "RushBrkTkl": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rush/BrkTkl": {
            "positive" : False,
            "round" : 2,
            "skipzero" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        }
    },
    "Scrimmage/All Purpose" : {
        "Touch": {
            "positive" : True
        },
        "Yds": {
            "positive" : True
        },
        "Yds/Tch": {
            "positive" : True,
            "round" : 2
        },
        "TD": {
            "positive" : True
        },
        "2PM": {
            "positive" : True
        },
        "Fmb": {
            "positive" : False,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "FmbLst": {
            "positive" : False,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "TD%": {
            "positive" : True,
            "round" : "percent"
        },
        "Fmb%": {
            "positive" : False,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "FmbLst%": {
            "positive" : False,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "Tch/G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/G": {
            "positive" : True,
            "round" : 2
        },
        "TD/G": {
            "positive" : True,
            "round" : 2
        },
        "Fmb/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "FmbLst/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "Tch/17G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/17G": {
            "positive" : True,
            "round" : 2
        },
        "TD/17G": {
            "positive" : True,
            "round" : 2
        },
        "2PM/17G": {
            "positive" : True,
            "round" : 2
        },
        "Fmb/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "FmbLst/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "game" : 1994,
                "season" : 1994
            }
        },
        "APYds": {
            "positive" : True
        },
        "APTD": {
            "positive" : True
        },
        "APYds/G": {
            "positive" : True,
            "round" : 2
        },
        "APTD/G": {
            "positive" : True,
            "round" : 2
        },
        "APYds/17G": {
            "positive" : True,
            "round" : 2
        },
        "APTD/17G": {
            "positive" : True,
            "round" : 2
        }
    },
    "Defense" : {
        "DefSnp" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "DefSnp%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Solo": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1994,
                "game" : 1999
            }
        },
        "Ast": {
            "positive" : True,
            "valid_since" : {
                "season" : 1994,
                "game" : 1999
            }
        },
        "Comb": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1994,
                "game" : 1999
             }
        },
        "TFL": {
            "positive" : True,
            "valid_since" : {
                "season" : 1999,
                "game" : 1999,
                "inconsistent" : 2008
            }
        },
        "Sk": {
            "positive" : True,
            "round" : 1,
            "valid_since" : {
                "season" : 1960,
                "game" : 1982,
                "inconsistent" : 1982
            }
        },
        "QBHits": {
            "positive" : True,
            "valid_since" : {
                "season" : 2006,
                "game" : 2006
            }
        },
        "FF": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1993,
                "inconsistent-game" : 1993
            }
        },
        "FR": {
            "positive" : True
        },
        "FR Yds": {
            "positive" : True,
            "display" : False
        },
        "FR TD": {
            "positive" : True
        },
        "Int": {
            "positive" : True
        },
        "Int Yds": {
            "positive" : True,
            "display" : False
        },
        "Int TD": {
            "positive" : True
        },
        "Ttl TD" : {
            "positive" : True
        },
        "PD": {
            "positive" : True,
            "valid_since" : {
                "season" : 1999,
                "game" : 1999
             }
        },
        "Sfty": {
            "positive" : True
        }
    },
    "Defense Per Game/Snap": {
        "DefSnp" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Solo": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "inconsistent" : 1994,
                "game" : 1999
            }
        },
        "Ast": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1999
            }
        },
        "Comb": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "inconsistent" : 1994,
                "game" : 1999
             }
        },
        "TFL": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1999,
                "game" : 1999,
                "inconsistent" : 2008
            }
        },
        "Sk": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1960,
                "game" : 1982,
                "inconsistent" : 1982
            }
        },
        "QBHits": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2006,
                "game" : 2006
            }
        },
        "Solo/17": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "inconsistent" : 1994,
                "game" : 1999
            }
        },
        "Ast/17": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1999
            }
        },
        "Comb/17": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "inconsistent" : 1994,
                "game" : 1999
             }
        },
        "TFL/17": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1999,
                "game" : 1999,
                "inconsistent" : 2008
            }
        },
        "Sk/17": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1960,
                "game" : 1982,
                "inconsistent" : 1982
            }
        },
        "QBHits/17": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2006,
                "game" : 2006
            }
        },
        "FF/17": {
            "positive" : True,
            "round" : 2
        },
        "Int/17": {
            "positive" : True,
            "round" : 2
        },
        "TD/17" : {
            "positive" : True,
            "round" : 2
        },
        "PD/17": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1999,
                "game" : 1999
             }
        },
        "Solo%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Ast%": {
            "positive" : True,
            "round" : "percent",
            "display": False,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Comb%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "TFL%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Sk%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "QBHit%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "FF%": {
            "positive" : True,
            "display": False,
            "round" : "percent"
        },
        "Int%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "PD%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        }
    },
    "Advanced/Defense" : {
        "DefSnp" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Comb": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "inconsistent" : 1994,
                "game" : 1999
             }
        },
        "Sk": {
            "positive" : True,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1960,
                "game" : 1982,
                "inconsistent" : 1982
            }
        },
        "QBHrry": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "QBKD": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "QBPress": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Bltz": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "MissTckl": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Hrry/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "KD/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Press/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "MTckl/G": {
            "positive" : False,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Hrry%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "KD%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Press%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Bltz%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "MTckl%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Cmp": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Tgt": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Cmp%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds/Cmp": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds/Tgt": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds/Snp": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "TD": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Int": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rate": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Cmp/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Tgt/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "TD/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "TD%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        }
    },
    "Advanced/Defense/Back" : {
        "DefSnp" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Cmp": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Tgt": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Cmp%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds/Cmp": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds/Tgt": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds/Snp": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "TD": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Int": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Rate": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Cmp/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Tgt/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Yds/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "TD/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "TD%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Comb": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "inconsistent" : 1994,
                "game" : 1999
             }
        },
        "Sk": {
            "positive" : True,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1960,
                "game" : 1982,
                "inconsistent" : 1982
            }
        },
        "QBHrry": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "QBKD": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "QBPress": {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Bltz": {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "MissTckl": {
            "positive" : False,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Hrry/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "KD/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Press/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "MTckl/G": {
            "positive" : False,
            "display" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Hrry%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "KD%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Press%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "Bltz%": {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "MTckl%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        }
    },
    "Penalties/Snaps" : {
        "Pen" : {
            "positive" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "AcptPen" : {
            "positive" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "PenYds" : {
            "positive" : False,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "PenYds/Pen": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "Pen/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "AcptPen/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "PenYds/G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "Pen/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "AcptPen/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "PenYds/17G": {
            "positive" : False,
            "round" : 2,
            "valid_since" : {
                "season" : 1994,
                "game" : 1994
            }
        },
        "Pen%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "AcptPen%": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Snp" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "OffSnp" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "DefSnp" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "STSnp" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "OffSnp%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "DefSnp%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "STSnp%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Snp/G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "OffSnp/G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "DefSnp/G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "STSnp/G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        }
    },
    "Snaps" : {
         "Snp" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "OffSnp" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "DefSnp" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "STSnp" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "OffSnp%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "DefSnp%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "STSnp%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "Snp/G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "OffSnp/G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "DefSnp/G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        },
        "STSnp/G" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 2012,
                "game" : 2012
             }
        }
    },
    "Scoring" : {
        "FGM": {
            "positive" : True
        },
        "FGA": {
            "positive" : True
        },
        "FG%": {
            "positive" : True,
            "round" : "percent"
        },
        "XPM": {
            "positive" : True
        },
        "XPA": {
            "positive" : True
        },
        "XP%": {
            "positive" : True,
            "round" : "percent"
        },
        "Pts": {
            "positive" : True
        },
        "FGM/G": {
            "positive" : True,
            "round" : 2
        },
        "FGA/G": {
            "positive" : True,
            "round" : 2
        },
        "XPM/G": {
            "positive" : True,
            "round" : 2
        },
        "XPAtt/G": {
            "positive" : True,
            "round" : 2
        },
        "Pts/G": {
            "positive" : True,
            "round" : 2
        },
        "FGM/17G": {
            "positive" : True,
            "round" : 2
        },
        "FGA/17G": {
            "positive" : True,
            "round" : 2
        },
        "XPM/17G": {
            "positive" : True,
            "round" : 2
        },
        "XPAtt/17G": {
            "positive" : True,
            "round" : 2
        },
        "Pts/17G": {
            "positive" : True,
            "round" : 2
        }
    },
    "Advanced/Kicking" : {
        "FGM:0-19": {
            "positive" : True
        },
        "FGA:0-19": {
            "positive" : True
        },
        "FG%:0-19": {
            "positive" : True,
            "round" : "percent"
        },
        "FGM:20-29": {
            "positive" : True
        },
        "FGA:20-29": {
            "positive" : True
        },
        "FG%:20-29": {
            "positive" : True,
            "round" : "percent"
        },
        "FGM:30-39": {
            "positive" : True
        },
        "FGA:30-39": {
            "positive" : True
        },
        "FG%:30-39": {
            "positive" : True,
            "round" : "percent"
        },
        "FGM:40-49": {
            "positive" : True
        },
        "FGA:40-49": {
            "positive" : True
        },
        "FG%:40-49": {
            "positive" : True,
            "round" : "percent"
        },
        "FGM:50+": {
            "positive" : True
        },
        "FGA:50+": {
            "positive" : True
        },
        "FG%:50+": {
            "positive" : True,
            "round" : "percent"
        },
        "Lng": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },
        "KO" : {
            "display" : False,
            "positive" : True
        },
        "KOYds" : {
            "display" : False,
            "positive" : True
        },
        "KOAvg" : {
            "positive" : True,
            "round": 2
        },
        "TB" : {
            "display" : False,
            "positive" : True
        },
        "TB%" : {
            "positive" : True,
            "round": "percent"
        }
    },
    "Punting" : {
        "Pnt": {   			
            "positive" : True
        },
        "Yds": {
            "positive" : True
        },
        "Yds/Pnt": {
            "positive" : True,
            "round" : 2
        },
        "Blck": {
            "positive" : False
        },
        "Pnt/G": {
            "positive" : True,
            "round": 2
        },
        "Yds/G": {
            "positive" : True,
            "round" : 2
        },
        "Pnt/17G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/17G": {
            "positive" : True,
            "round" : 2
        },
        "Blck/17G": {
            "positive" : False,
            "round": 2
        }
    },
    "Advanced/Punting" : {
        "Lng": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        }
    },
    "Kick Returns" : {
        "Rt": {   			
            "positive" : True
        },
        "Yds": {
            "positive" : True
        },
        "Yds/Rt": {
            "positive" : True,
            "round" : 2
        },
        "TD": {
            "positive" : True
        },
        "TD%": {
            "positive" : True,
            "round": "percent"
        },
        "Rt/G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/G": {
            "positive" : True,
            "round" : 2
        },
        "TD/G": {
            "positive" : True,
            "round" : 2,
            "display": False
        },
        "Rt/17G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/17G": {
            "positive" : True,
            "round" : 2
        },
        "TD/17G": {
            "positive" : True,
            "round" : 2
        }
    },
    "Punt Returns" : {
        "Rt": {   			
            "positive" : True
        },
        "Yds": {
            "positive" : True
        },
        "Yds/Rt": {
            "positive" : True,
            "round" : 2
        },
        "TD": {
            "positive" : True
        },
        "TD%": {
            "positive" : True,
            "round": "percent"
        },
        "Rt/G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/G": {
            "positive" : True,
            "round" : 2
        },
        "TD/G": {
            "positive" : True,
            "round" : 2,
            "display" : False
        },
        "Rt/17G": {
            "positive" : True,
            "round" : 2
        },
        "Yds/17G": {
            "positive" : True,
            "round" : 2
        },
        "TD/17G": {
            "positive" : True,
            "round" : 2
        }
    },
    "Advanced/Kick Returns" : {
        "KickLng": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },
        "PuntLng": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        }
    },
    "Advanced/Punt Returns" : {
        "PuntLng": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        },
        "KickLng": {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1975,
                "game" : None
            }
        }
    },
    "Fantasy" : {
        "STD": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "STD/G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "STD/17G": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "STD Median": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "STD High": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "STD Low": {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "STD Variance": {
            "positive" : False,
            "round" : "percent",
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "0.5PPR": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "0.5PPR/G": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "0.5PPR/17G": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "0.5PPR Median": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "0.5PPR High": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "0.5PPR Low": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "0.5PPR Variance": {
            "positive" : False,
            "round" : "percent",
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "PPR": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "PPR/G": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "PPR/17G": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "PPR Median": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "PPR High": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "PPR Low": {
            "positive" : True,
            "round" : 2,
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        },
        "PPR Variance": {
            "positive" : False,
            "round" : "percent",
            "valid_for" : ["Receiving"],
            "valid_since" : {
                "game-np" : 1994
            }
        }
    },
    "Shared" : {
        "Player" : {
            "positive" : True
        },
        "DateStart" : {
            "positive" : True,
            "display" : False
        },
        "DateEnd" : {
            "positive" : True,
            "display" : False
        },
        "YearStart" : {
            "positive" : True,
            "display" : False
        },
        "YearEnd" : {
            "positive" : True,
            "display" : False
        },
        "Gm" : {
            "positive" : True,
            "display" : False
        },
        "GmRev" : {
            "positive" : True,
            "display" : False
        },
        "TmGm" : {
            "positive" : True,
            "display" : False
        },
        "TmGmRev" : {
            "positive" : True,
            "display" : False
        },
        "CrGm" : {
            "positive" : True,
            "display" : False
        },
        "CrGmRev" : {
            "positive" : True,
            "display" : False
        },
        "DyRst" : {
            "positive" : True,
            "display" : False
        },
        "G" : {
            "positive" : True
        },
        "G_Adv" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "GS_Adv" : {
            "positive" : True,
            "valid_since" : {
                "season" : 2018,
                "game" : 2018
            }
        },
        "G1D" : {
            "positive" : True,
            "display" : False
        },
        "GS" : {
            "positive" : True,
            "valid_since" : {
                "inconsistent" : 1980,
                "inconsistent-game" : 1999
            }
        },
        "TmW" :{
            "positive" : True,
            "display" : False
        },
        "TmL" :{
            "positive" : False,
            "display" : False
        },
        "TmT" :{
            "positive" : False,
            "display" : False
        },
        "TmRec" : {
            "positive" : True,
            "display" : False
        },
        "TmW/L%" :{
            "positive" : True,
            "round" : "percent",
            "display" : False
        },
        "ATSTeamW" :{
            "positive" : True,
            "display" : False
        },
        "ATSTeamL" :{
            "positive" : False,
            "display" : False
        },
        "ATSTeamT" :{
            "positive" : False,
            "display" : False
        },
        "ATS TmRec" : {
            "positive" : True,
            "display" : False
        },
        "ATS TmW/L%" :{
            "positive" : True,
            "round" : "percent",
            "display" : False
        },
        "OUTeamW" :{
            "positive" : True,
            "display" : False
        },
        "OUTeamL" :{
            "positive" : False,
            "display" : False
        },
        "OUTeamT" :{
            "positive" : False,
            "display" : False
        },
        "O/U TmRec" : {
            "positive" : True,
            "display" : False
        },
        "O/U TmW/L%" :{
            "positive" : True,
            "round" : "percent",
            "display" : False
        },
        "TmScore" :{
            "positive" : True,
            "display" : False
        },
        "OppScore" :{
            "positive" : False,
            "display" : False
        },
        "TtlScore" :{
            "positive" : True,
            "display" : False
        },
        "ScoreDiff" :{
            "positive" : True,
            "display" : False
        },
        "TmScore/G" :{
            "positive" : True,
            "round" : 2,
            "display" : False
        },
        "OppScore/G" :{
            "positive" : False,
            "round" : 2,
            "display" : False
        },
        "TtlScore/G" :{
            "positive" : True,
            "round" : 2,
            "display" : False,
        },
        "ScoreDiff/G" :{
            "positive" : True,
            "round" : 2,
            "display" : False
        },
        "Tm" : {
            "positive" : True,
            "display" : False
        },
        "RawTm" : {
            "positive" : True,
            "display" : False
        },
        "RawOpponent" : {
            "positive" : True,
            "display" : False
        },
        "Result" : {
            "positive" : True,
            "display" : False
        },
        "Team Score" : {
            "positive" : True,
            "display" : False
        },
        "Opponent Score" : {
            "positive" : True,
            "display" : False
        }
    },
    "Awards/Honors/Pass" : {
        "Seasons" : {
            "positive" : True
        },
        "RegularSeasons" : {
            "positive" : True,
            "display" : False
        },
        "RegularAVSeasons" : {
            "positive" : True,
            "display" : False
        },
        "UniqueSeasons" : {
            "positive" : True,
            "display" : False
        },
        "NonFakeSeasons" : {
            "positive" : True,
            "display" : False
        },
        "G/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "GS/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "ProBowl" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "OPOY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1972
            }
        },
        "OPOYShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1972,
                "inconsistent" : 1986
            }
        },
        "OPOYShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1972,
                "inconsistent" : 1986
            }
        },
        "MVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "MVPShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "MVPShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "PassTitle" : {
            "positive" : True,
            "display" : False
        },
        "ROY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "SBMVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1966,
                "game" : 1966
            }
        },
        "Champ" : {
            "positive" : True
        },
        "AV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "ProBowl%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "OPOY%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1972
            }
        },
        "MVP%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1957
            }
        },
        "PassTitle%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False
        },
        "Champ%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "AV/Yr" : {
            "positive" : True,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV/Yr" : {
            "positive" : True,
            "display" : False,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        }
    },
    "Awards/Honors/Rush" : {
        "Seasons" : {
            "positive" : True
        },
        "RegularSeasons" : {
            "positive" : True,
            "display" : False
        },
        "RegularAVSeasons" : {
            "positive" : True,
            "display" : False
        },
        "UniqueSeasons" : {
            "positive" : True,
            "display" : False
        },
        "NonFakeSeasons" : {
            "positive" : True,
            "display" : False
        },
        "G/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "GS/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "ProBowl" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "OPOY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1972
            }
        },
        "OPOYShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1972,
                "inconsistent" : 1986
            }
        },
        "OPOYShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1972,
                "inconsistent" : 1986
            }
        },
        "MVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "MVPShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "MVPShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "RushTitle" : {
            "positive" : True
        },
        "ROY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "SBMVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1966,
                "game" : 1966
            }
        },
        "Champ" : {
            "positive" : True
        },
        "AV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "ProBowl%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "OPOY%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1972
            }
        },
        "MVP%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1957
            }
        },
        "RushTitle%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "Champ%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "AV/Yr" : {
            "positive" : True,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV/Yr" : {
            "positive" : True,
            "display" : False,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        }
    },
    "Awards/Honors/Rec" : {
        "Seasons" : {
            "positive" : True
        },
        "RegularSeasons" : {
            "positive" : True,
            "display" : False
        },
        "RegularAVSeasons" : {
            "positive" : True,
            "display" : False
        },
        "UniqueSeasons" : {
            "positive" : True,
            "display" : False
        },
        "NonFakeSeasons" : {
            "positive" : True,
            "display" : False
        },
        "G/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "GS/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "ProBowl" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "OPOY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1972
            }
        },
        "OPOYShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1972,
                "inconsistent" : 1986
            }
        },
        "OPOYShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1972,
                "inconsistent" : 1986
            }
        },
        "MVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "MVPShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "MVPShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "RecTitle" : {
            "positive" : True
        },
        "ROY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "SBMVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1966,
                "game" : 1966
            }
        },
        "Champ" : {
            "positive" : True
        },
        "AV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "ProBowl%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "OPOY%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1972
            }
        },
        "MVP%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1957
            }
        },
        "RecTitle%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "Champ%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "AV/Yr" : {
            "positive" : True,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV/Yr" : {
            "positive" : True,
            "display" : False,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        }
    },
    "Awards/Honors/Defensive" : {
        "Seasons" : {
            "positive" : True
        },
        "RegularSeasons" : {
            "positive" : True,
            "display" : False
        },
        "RegularAVSeasons" : {
            "positive" : True,
            "display" : False
        },
        "UniqueSeasons" : {
            "positive" : True,
            "display" : False
        },
        "NonFakeSeasons" : {
            "positive" : True,
            "display" : False
        },
        "G/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "GS/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "ProBowl" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "DPOY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1972
            }
        },
        "DPOYShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1971,
                "inconsistent" : 1986
            }
        },
        "DPOYShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1971,
                "inconsistent" : 1986
            }
        },
        "MVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "MVPShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "MVPShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "TcklTitle" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "inconsistent" : 1994
            }
        },
        "SkTitle" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960,
                "inconsistent" : 1982
            }
        },
        "ROY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "SBMVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1966,
                "game" : 1966
            }
        },
        "Champ" : {
            "positive" : True
        },
        "AV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "ProBowl%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "DPOY%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1972
            }
        },
        "MVP%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1957
            }
        },
        "TcklTitle%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "inconsistent" : 1994
            }
        },
        "SkTitle%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1982
            }
        },
        "Champ%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "AV/Yr" : {
            "positive" : True,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV/Yr" : {
            "positive" : True,
            "display" : False,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        }
    },
    "Awards/Honors/Int" : {
        "Seasons" : {
            "positive" : True
        },
        "RegularSeasons" : {
            "positive" : True,
            "display" : False
        },
        "RegularAVSeasons" : {
            "positive" : True,
            "display" : False
        },
        "UniqueSeasons" : {
            "positive" : True,
            "display" : False
        },
        "NonFakeSeasons" : {
            "positive" : True,
            "display" : False
        },
        "G/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "GS/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "ProBowl" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "DPOY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1972
            }
        },
        "DPOYShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1971,
                "inconsistent" : 1986
            }
        },
        "DPOYShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1971,
                "inconsistent" : 1986
            }
        },
        "MVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "MVPShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "MVPShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "IntTitle" : {
            "positive" : True,
            "display" : False
        },
        "ROY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "SBMVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1966,
                "game" : 1966
            }
        },
        "Champ" : {
            "positive" : True
        },
        "AV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "ProBowl%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "DPOY%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1972
            }
        },
        "MVP%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1957
            }
        },
        "IntTitle%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "Champ%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "AV/Yr" : {
            "positive" : True,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV/Yr" : {
            "positive" : True,
            "display" : False,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        }
    },
    "Awards/Honors/Other" : {
        "Seasons" : {
            "positive" : True
        },
        "RegularSeasons" : {
            "positive" : True,
            "display" : False
        },
        "RegularAVSeasons" : {
            "positive" : True,
            "display" : False
        },
        "UniqueSeasons" : {
            "positive" : True,
            "display" : False
        },
        "NonFakeSeasons" : {
            "positive" : True,
            "display" : False
        },
        "G/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "GS/Yr" : {
            "positive" : True,
            "round" : 2
        },
        "ProBowl" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd" : {
            "positive" : True,
            "display" : False,
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1940
            }
        },
        "MVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "MVPShares" : {
            "positive" : True,
            "round" : 2,
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "MVPShr%" : {
            "positive" : True,
            "round" : "percent",
            "valid_since" : {
                "season" : 1957,
                "inconsistent" : 1986
            }
        },
        "ROY" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1957
            }
        },
        "SBMVP" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1966,
                "game" : 1966
            }
        },
        "Champ" : {
            "positive" : True
        },
        "AV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV" : {
            "positive" : True,
            "valid_since" : {
                "season" : 1960
            }
        },
        "ProBowl%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1950
            }
        },
        "APAllPro:1st%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:2nd%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "APAllPro:Tot%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent",
            "valid_since" : {
                "season" : 1940
            }
        },
        "MVP%" : {
            "positive" : True,
            "round" : "percent",
            "display" : False,
            "valid_since" : {
                "season" : 1957
            }
        },
        "Champ%" : {
            "positive" : True,
            "display" : False,
            "round" : "percent"
        },
        "AV/Yr" : {
            "positive" : True,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        },
        "WeightAV/Yr" : {
            "positive" : True,
            "display" : False,
            "round" : 1,
            "valid_since" : {
                "season" : 1960
            }
        }
    }
}

formulas = {
    "Passing" : {
        "Att/G" : "Att / G",
        "Cmp/G" : "Cmp / G",
        "Att/17G" : "Att / (G / 17)",
        "Cmp/17G" : "Cmp / (G / 17)",
        "Cmp%" : "Cmp / Att",
        "Yds/G": "Yds / G",
        "Yds/17G": "Yds / (G / 17)",
        "Y/C" : "Yds / Cmp",
        "Y/A" : "Yds / Att",
        "AY/A": "(Yds + 20*(TD) - 45*(Int))/(Att)",
        "NY/A": "(Yds - SkYds) / (Att + Sk)",
        "ANY/A": "(Yds - SkYds + 20*(TD) - 45*(Int)) / (Att + Sk)",
        "TD/G" : "TD / G",
        "TD/17G" : "TD / (G / 17)",
        "TD%" : "TD / Att",
        "Int/G" : "Int / G",
        "Int/17G" : "Int / (G / 17)",
        "Int%" : "Int / Att",
        "TD/Int" : "TD / Int",
        "Rate" : "Special",
        "Sk/G" : "Sk / G",
        "Sk/17G" : "Sk / (G / 17)",
        "Sk%" : "Sk / (Att + Sk)",
        "SkYds/G" : "SkYds / G",
        "SkYds/17G" : "SkYds / (G / 17)",
        "Yds/Sk" : "SkYds / Sk"
    },
    "Era Adjusted Passing" : {
        "4QC/17G" : "4QC / (G / 17)",
        "GWD/17G" : "GWD / (G / 17)",
        "QBW/17G" : "QBW / ((QBW + QBL + QBT) / 17)",
        "QBL/17G" : "QBL / ((QBW + QBL + QBT) / 17)",
        "QBT/17G" : "QBT / ((QBW + QBL + QBT) / 17)",
        "TtlYds" : "Special",
        "Yds/G": "TtlYds / G",
        "Yds/17G": "TtlYds / (G / 17)",
        "Tnv" : "Special",
        "Tnv/G": "Tnv / G",
        "Tnv/17G": "Tnv / (G / 17)",
        "Pick6/17G" : "Pick6 / (G / 17)",
        "Rec" : "Special",
        "Rec/17G" : "Special",
        "TtlTD" : "Special",
        "TD/G" : "TtlTD / G",
        "TD/17G" : "TtlTD / (G / 17)",
        "TtlTD%" : "Special",
        "TtlTDTnv" : "Special",
        "TD/Tnv" : "TtlTDTnv/Tnv",
        "W/L%" : "QBW / (QBW + QBL)"
    },
    "Advanced/Passing" : {
        "1D" : "Pass1D + Rush1D + Rec1D",
        "1D/G" : "1D / G1D",
        "Pass1D%" : "Special",
        "Rush1D%" : "Special",
        "Rec1D%" : "Special",
        "CAY" : "CAY-RAW / Cmp",
        "IAY" : "IAY-RAW / Att",
        "AYD" : "CAY - IAY",
        "YAC" : "YAC-RAW / Cmp",
        "OnTgt%" : "OnTgt / (Att - ThAwyTgt - SpikesTgt)",
        "BadTh%" : "BadTh / (Att - ThAwy - Spikes)",
        "Drop%" : "Drops / (Att - ThAwy - Spikes)",
        "Bltz%" : "Bltz / Att",
        "Hrry%" : "Hrry / Att",
        "Hit%" : "Hits / Att",
        "Prss%" : "Prss / Att",
        "YBC/Rush" : "YBContact / Rush",
        "YAC/Rush" : "YAContact / Rush",
        "BrkTkl" : "RushBrkTkl + RecBrkTkl",
        "BrkTkl/G" : "BrkTkl / G",
        "Rush/BrkTkl" : "Rush / RushBrkTkl",
        "Rec/BrkTkl" : "Rec / RecBrkTkl",
        "LngPass" : "MAX",
        "LngRush" : "MAX"
    },
    "Rushing" : {
        "Att/G" : "Att / G",
        "Att/17G" : "Att / (G / 17)",
        "Yds/G": "Yds / G",
        "Yds/17G": "Yds / (G / 17)",
        "Yds/Att": "Yds / Att",
        "TD/G" : "TD / G",
        "TD/17G" : "TD / (G / 17)",
        "TD%": "TD / Att",
        "Fmb/G" : "Fmb / G",
        "Fmb/17G" : "Fmb / (G / 17)",
        "FmbLst/G" : "FmbLst / G",
        "FmbLst/17G" : "FmbLst / (G / 17)",
        "Fmb%" : "Special",
        "FmbLst%" : "FmbLst / Fmb"
    },
    "Advanced/Rushing" : {
        "1D" : "Pass1D + Rush1D + Rec1D",
        "1D/G" : "1D / G1D",
        "Pass1D%" : "Special",
        "Rush1D%" : "Special",
        "Rec1D%" : "Special",
        "YBC/Rush" : "YBContact / Rush",
        "YAC/Rush" : "YAContact / Rush",
        "YBC/Rec" : "YBCatch / Rec",
        "YAC/Rec" : "YACatch / Rec",
        "Drop%" : "Drop / Tgt",
        "BrkTkl" : "RushBrkTkl + RecBrkTkl",
        "BrkTkl/G" : "BrkTkl / G",
        "Rush/BrkTkl" : "Rush / RushBrkTkl",
        "Rec/BrkTkl" : "Rec / RecBrkTkl",
        "Rate" : "Special",
        "LngRush" : "MAX",
        "LngRec" : "MAX"
    },
    "Receiving" : {
        "Tgt/G" : "Tgt / G",
        "Tgt/17G" : "Tgt / (G / 17)",
        "Rec/G" : "Rec / G",
        "Rec/17G" : "Rec / (G / 17)",
        "Yds/G": "Yds / G",
        "Yds/17G": "Yds / (G / 17)",
        "Yds/Rec": "Yds / Rec",
        "Yds/Tgt": "Yds / Tgt",
        "Catch%" : "Rec / Tgt",
        "TD/G": "TD / G",
        "TD/17G" : "TD / (G / 17)",
        "TD%": "TD / Rec"
    },
    "Advanced/Receiving" : {
        "1D" : "Pass1D + Rush1D + Rec1D",
        "1D/G" : "1D / G1D",
        "Pass1D%" : "Special",
        "Rush1D%" : "Special",
        "Rec1D%" : "Special",
        "YBC/Rush" : "YBContact / Rush",
        "YAC/Rush" : "YAContact / Rush",
        "YBC/Rec" : "YBCatch / Rec",
        "YAC/Rec" : "YACatch / Rec",
        "Drop%" : "Drop / Tgt",
        "BrkTkl" : "RushBrkTkl + RecBrkTkl",
        "BrkTkl/G" : "BrkTkl / G",
        "Rush/BrkTkl" : "Rush / RushBrkTkl",
        "Rec/BrkTkl" : "Rec / RecBrkTkl",
        "Rate" : "Special",
        "LngRush" : "MAX",
        "LngRec" : "MAX"
    },
    "Scrimmage/All Purpose" : {
        "Tch/G" : "Touch / G",
        "Tch/17G" : "Touch / (G / 17)",
        "Yds/G": "Yds / G",
        "Yds/17G": "Yds / (G / 17)",
        "Yds/Tch": "Yds / Touch",
        "TD/G": "TD / G",
        "TD/17G" : "TD / (G / 17)",
        "2PM/17G" : "2PM / (G / 17)",
        "TD%": "TD / Touch",
        "Fmb/G" : "Fmb / G",
        "Fmb/17G" : "Fmb / (G / 17)",
        "FmbLst/G" : "FmbLst / G",
        "FmbLst/17G" : "FmbLst / (G / 17)",
        "Fmb%" : "Special",
        "FmbLst%" : "FmbLst / Fmb",
        "APYds/G": "APYds / G",
        "APYds/17G": "APYds / (G / 17)",
        "APTD/G": "APTD / G",
        "APTD/17G" : "APTD / (G / 17)",
    },
    "Defense" : {
        "Ttl TD" : "Special"
    },
    "Defense Per Game/Snap" : {
        "Int/17" : "Int / (G / 17)",
        "Int%" : "Int / DefSnp",
        "PD/17" : "PD/ (G / 17)",
        "PD%" : "PD / DefSnp",
        "FF/17" : "FF / (G / 17)",
        "FF%" : "FF / DefSnp",
        "Solo" : "Solo / G",
        "Solo/17" : "Solo / (G / 17)",
        "Solo%" : "Solo / DefSnp",
        "Ast" : "Ast / G",
        "Ast/17" : "Ast / (G / 17)",
        "Ast%" : "Ast / DefSnp",
        "Comb" : "Comb / G",
        "Comb/17" : "Comb / (G / 17)",
        "Comb%" : "Comb / DefSnp",
        "TFL" : "TFL / G",
        "TFL/17" : "TFL / (G / 17)",
        "TFL%" : "TFL / DefSnp",
        "Sk" : "Sk / G",
        "Sk/17" : "Sk / (G / 17)",
        "Sk%" : "Sk / DefSnp",
        "QBHits" : "QBHits / G",
        "QBHits/17" : "QBHits / (G / 17)",
        "QBHit%" : "QBHits / DefSnp",
        "TD/17" : "Ttl TD / (G / 17)"
    },
    "Advanced/Defense" : {
        "MTckl%" : "MissTckl / (MissTckl + Comb)",
        "Hrry%" : "QBHrry / DefSnp",
        "KD%" : "QBKD / DefSnp",
        "Press%" : "QBPress / DefSnp",
        "MTckl/G" : "MissTckl / G",
        "Hrry/G" : "QBHrry / G",
        "KD/G" : "QBKD / G",
        "Bltz%" : "Bltz / DefSnp",
        "Press/G" : "QBPress / G",
        "TD/G" : "TD / G",
        "Cmp/G" : "Cmp / G",
        "Tgt/G" : "Tgt / G",
        "Yds/G" : "Yds / G",
        "Cmp%" : "Cmp / Tgt",
        "Yds/Cmp" : "Yds / Cmp",
        "Yds/Tgt" : "Yds / Tgt",
        "Yds/Snp" : "Yds / DefSnp",
        "TD%" : "TD / DefSnp",
        "Rate" : "Special"
    },
    "Penalties/Snaps" : {
        "Snp" : "OffSnp + DefSnp + STSnp",
        "OffSnp/G" : "OffSnp / G",
        "DefSnp/G" : "DefSnp / G",
        "STSnp/G" : "STSnp / G",
        "Snp/G" : "Snp / G",
        "Pen/G" : "Pen / G",
        "Pen/17G" : "Pen / (G / 17)",
        "Pen%" : "Pen / Snp",
        "AcptPen/G" : "AcptPen / G",
        "AcptPen/17G" : "AcptPen / (G / 17)",
        "AcptPen%" : "AcptPen / Snp",
        "PenYds/G" : "PenYds / G",
        "PenYds/17G" : "PenYds / (G / 17)",
        "PenYds/Pen" : "PenYds / AcptPen"
    },
    "Snaps" : {
        "Snp" : "OffSnp + DefSnp + STSnp",
        "OffSnp/G" : "OffSnp / G",
        "DefSnp/G" : "DefSnp / G",
        "STSnp/G" : "STSnp / G",
        "Snp/G" : "Snp / G"
    },
    "Scoring" : {
        "FGM/G" : "FGM / G",
        "FGM/17G" : "FGM / (G / 17)",
        "FGA/G" : "FGA / G",
        "FGA/17G" : "FGA / (G / 17)",
        "FG%" : "FGM / FGA",
        "XPM/G": "XPM / G",
        "XPM/17G": "XPM / (G / 17)",
        "XPAtt/G": "XPA / G",
        "XPAtt/17G": "XPA / (G / 17)",
        "XP%" : "XPM / XPA",
        "Pts" : "(FGM * 3) + XPM",
        "Pts/G" : "Pts / G",
        "Pts/17G" : "Pts / (G / 17)"
    },
    "Advanced/Kicking" : {
        "Lng" : "MAX",
        "FG%:0-19" : "FGM:0-19 / FGA:0-19",
        "FG%:20-29" : "FGM:20-29 / FGA:20-29",
        "FG%:30-39" : "FGM:30-39 / FGA:30-39",
        "FG%:40-49" : "FGM:40-49 / FGA:40-49",
        "FG%:50+" : "FGM:50+ / FGA:50+",
        "KOAvg" : "KOYds / KO",
        "TB%" : "TB / KO"
    },
    "Punting" : {
        "Yds/Pnt" : "Yds / Pnt",
        "Pnt/G" : "Pnt / G",
        "Pnt/17G" : "Pnt / (G / 17)",
        "Yds/G": "Yds / G",
        "Yds/17G": "Yds / (G / 17)",
        "Blck/17G": "Blck / (G / 17)"
    },
    "Advanced/Punting" : {
        "Lng" : "MAX"
    },
    "Kick Returns" : {
        "Rt/G" : "Yds / G",
        "Rt/17G" : "Yds / (G / 17)",
        "Yds/G" : "Yds / G",
        "Yds/17G": "Yds / (G / 17)",
        "Yds/Rt": "Yds / Rt",
        "TD%": "TD / Rt",
        "TD/G": "TD / G",
        "TD/17G" : "TD / (G / 17)"
    },
    "Punt Returns" : {
        "Rt/G" : "Yds / G",
        "Rt/17G" : "Yds / (G / 17)",
        "Yds/G" : "Yds / G",
        "Yds/17G": "Yds / (G / 17)",
        "Yds/Rt": "Yds / Rt",
        "TD%": "TD / Rt",
        "TD/G": "TD / G",
        "TD/17G" : "TD / (G / 17)"
    },
    "Advanced/Kick Returns" : {
        "KickLng" : "MAX",
        "PuntLng" : "MAX"
    },
    "Advanced/Punt Returns" : {
        "PuntLng" : "MAX",
        "KickLng" : "MAX"
    },
    "Fantasy" : {
        "Passing" : {
            "STD" : "(4 * TD) + (Yds / 25) - (2 * Int)",
            "0.5PPR" : "STD",
            "PPR" : "STD"
        },
        "Rushing" : {
            "STD" : "(6 * TD) + (Yds / 10) - (2 * FmbLst)",
            "0.5PPR" : "STD",
            "PPR" : "STD"
        },
        "Scrimmage/All Purpose" : {
            "STD" : "2 * 2PM",
            "0.5PPR" : "STD",
            "PPR" : "STD"
        },
        "Receiving" : {
            "STD" : "(6 * TD) + (Yds / 10)",
            "0.5PPR" : "STD + (0.5 * Rec)",
            "PPR" : "STD + (Rec)"
        },
        "Kick Returns" : {
            "STD" : "(6 * TD)",
            "0.5PPR" : "STD",
            "PPR" : "STD"
        },
        "Punt Returns" : {
            "STD" : "(6 * TD)",
            "0.5PPR" : "STD",
            "PPR" : "STD"
        },
        "Defense" :  {
            "STD" : "(6 * Ttl TD)"
        }
    },
    "Shared" : {
        "TmW" : "Special",
        "TmL" : "Special",
        "TmT" : "Special",
        "TmRec" : "Special",
        "TmW/L%" : "TmW / (TmW + TmL)",
        "ATS TmRec" : "Special",
        "ATS TmW/L%" : "ATSTeamW / (ATSTeamW + ATSTeamL)",
        "O/U TmRec" : "Special",
        "O/U TmW/L%" : "OUTeamW / (OUTeamW + OUTeamL)",
        "TmScore" : "Special",
        "OppScore" : "Special",
        "TtlScore" : "TmScore + OppScore",
        "ScoreDiff" : "TmScore - OppScore",
        "TmScore/G" : "TmScore / G",
        "OppScore/G" : "OppScore / G",
        "TtlScore/G" : "TtlScore / G",
        "ScoreDiff/G" : "ScoreDiff / G"
    },
    "Awards/Honors/Pass" : {
        "G/Yr" : "G / NonFakeSeasons",
        "GS/Yr" : "GS / NonFakeSeasons",
        "ProBowl%" : "ProBowl / RegularSeasons",
        "APAllPro:1st%" : "APAllPro:1st / RegularSeasons",
        "APAllPro:2nd%" : "APAllPro:2nd / RegularSeasons",
        "APAllPro:Tot" : "APAllPro:1st + APAllPro:2nd",
        "APAllPro:Tot%" : "APAllPro:Tot / RegularSeasons",
        "MVP%" : "MVP / RegularSeasons",
        "MVPShr%" : "MVPShares / RegularSeasons",
        "Champ%" : "Champ / UniqueSeasons",
        "OPOY%" : "OPOY / RegularSeasons",
        "OPOYShr%" : "OPOYShares / RegularSeasons",
        "PassTitle%" : "PassTitle / RegularSeasons",
        "AV/Yr" : "AV / RegularAVSeasons",
        "WeightAV" : "Special",
        "WeightAV/Yr" : "WeightAV / RegularAVSeasons"
    },
    "Awards/Honors/Rush" : {
        "G/Yr" : "G / NonFakeSeasons",
        "GS/Yr" : "GS / NonFakeSeasons",
        "ProBowl%" : "ProBowl / RegularSeasons",
        "APAllPro:1st%" : "APAllPro:1st / RegularSeasons",
        "APAllPro:2nd%" : "APAllPro:2nd / RegularSeasons",
        "APAllPro:Tot" : "APAllPro:1st + APAllPro:2nd",
        "APAllPro:Tot%" : "APAllPro:Tot / RegularSeasons",
        "MVP%" : "MVP / RegularSeasons",
        "MVPShr%" : "MVPShares / RegularSeasons",
        "Champ%" : "Champ / UniqueSeasons",
        "OPOY%" : "OPOY / RegularSeasons",
        "OPOYShr%" : "OPOYShares / RegularSeasons",
        "RushTitle%" : "RushTitle / RegularSeasons",
        "AV/Yr" : "AV / RegularAVSeasons",
        "WeightAV" : "Special",
        "WeightAV/Yr" : "WeightAV / RegularAVSeasons"
    },
    "Awards/Honors/Rec" : {
        "G/Yr" : "G / NonFakeSeasons",
        "GS/Yr" : "GS / NonFakeSeasons",
        "ProBowl%" : "ProBowl / RegularSeasons",
        "APAllPro:1st%" : "APAllPro:1st / RegularSeasons",
        "APAllPro:2nd%" : "APAllPro:2nd / RegularSeasons",
        "APAllPro:Tot" : "APAllPro:1st + APAllPro:2nd",
        "APAllPro:Tot%" : "APAllPro:Tot / RegularSeasons",
        "MVP%" : "MVP / RegularSeasons",
        "MVPShr%" : "MVPShares / RegularSeasons",
        "Champ%" : "Champ / UniqueSeasons",
        "OPOY%" : "OPOY / RegularSeasons",
        "OPOYShr%" : "OPOYShares / RegularSeasons",
        "RecTitle%" : "RecTitle / RegularSeasons",
        "AV/Yr" : "AV / RegularAVSeasons",
        "WeightAV" : "Special",
        "WeightAV/Yr" : "WeightAV / RegularAVSeasons"
    },
    "Awards/Honors/Defensive" : {
        "G/Yr" : "G / NonFakeSeasons",
        "GS/Yr" : "GS / NonFakeSeasons",
        "ProBowl%" : "ProBowl / RegularSeasons",
        "APAllPro:1st%" : "APAllPro:1st / RegularSeasons",
        "APAllPro:2nd%" : "APAllPro:2nd / RegularSeasons",
        "APAllPro:Tot" : "APAllPro:1st + APAllPro:2nd",
        "APAllPro:Tot%" : "APAllPro:Tot / RegularSeasons",
        "MVP%" : "MVP / RegularSeasons",
        "MVPShr%" : "MVPShares / RegularSeasons",
        "Champ%" : "Champ / UniqueSeasons",
        "DPOY%" : "DPOY / RegularSeasons",
        "DPOYShr%" : "DPOYShares / RegularSeasons",
        "TcklTitle%" : "TcklTitle / RegularSeasons",
        "SkTitle%" : "SkTitle / RegularSeasons",
        "AV/Yr" : "AV / RegularAVSeasons",
        "WeightAV" : "Special",
        "WeightAV/Yr" : "WeightAV / RegularAVSeasons"
    },
    "Awards/Honors/Int" : {
        "G/Yr" : "G / NonFakeSeasons",
        "GS/Yr" : "GS / NonFakeSeasons",
        "ProBowl%" : "ProBowl / RegularSeasons",
        "APAllPro:1st%" : "APAllPro:1st / RegularSeasons",
        "APAllPro:2nd%" : "APAllPro:2nd / RegularSeasons",
        "APAllPro:Tot" : "APAllPro:1st + APAllPro:2nd",
        "APAllPro:Tot%" : "APAllPro:Tot / RegularSeasons",
        "MVP%" : "MVP / RegularSeasons",
        "MVPShr%" : "MVPShares / RegularSeasons",
        "Champ%" : "Champ / UniqueSeasons",
        "DPOY%" : "DPOY / RegularSeasons",
        "DPOYShr%" : "DPOYShares / RegularSeasons",
        "IntTitle%" : "IntTitle / RegularSeasons",
        "AV/Yr" : "AV / RegularAVSeasons",
        "WeightAV" : "Special",
        "WeightAV/Yr" : "WeightAV / RegularAVSeasons"
    },
    "Awards/Honors/Other" : {
        "G/Yr" : "G / NonFakeSeasons",
        "GS/Yr" : "GS / NonFakeSeasons",
        "ProBowl%" : "ProBowl / RegularSeasons",
        "APAllPro:1st%" : "APAllPro:1st / RegularSeasons",
        "APAllPro:2nd%" : "APAllPro:2nd / RegularSeasons",
        "APAllPro:Tot" : "APAllPro:1st + APAllPro:2nd",
        "APAllPro:Tot%" : "APAllPro:Tot / RegularSeasons",
        "MVP%" : "MVP / RegularSeasons",
        "MVPShr%" : "MVPShares / RegularSeasons",
        "Champ%" : "Champ / UniqueSeasons",
        "AV/Yr" : "AV / RegularAVSeasons",
        "WeightAV" : "Special",
        "WeightAV/Yr" : "WeightAV / RegularAVSeasons"
    }
}

qualifier_map = {
    "Rookie" : {},
    "Facing Former Team" : {},
    "Facing Former Franchise" : {},
    "Age" : {},
    "Season Age" : {},
    "Round" : {
        "ch" : "Championship",
        "sb" : "Super Bowl",
        "lc" : "League Championship",
        "cc" : "Conference Championship",
        "dr" : "Divisional",
        "wc" : "Wild Card"
    },
    "Super Bowl" : {},
    "Time" : {
        "m" : "Morning",
        "e" : "Early Afternoon",
        "a" : "Late Afternoon",
        "l" : "Night"
    },
    "Start Time" : {},
    "Location" : {
        "home" : "Home",
        "away" : "Away",
        "neutral" : "Neutral"
    },
    "With New Team" : {},
    "With New Franchise" : {},
    "Temperate Season" : {},
    "Team" : {},
    "Opponent" : {},
    "Team Franchise" : {},
    "Opponent Franchise" : {},
    "Start" : {
        True : "Only Starts",
        False : "No Starts"
    },
    "Month" : {},
    "Stadium" : {},
    "Exact Stadium" : {},
    "Temperature" : {},
    "Humidity" : {},
    "Wind" : {},
    "Wind Chill" : {},
    "Roof" : {},
    "Surface" : {},
    "Day" : {},
    "Date" : {},
    "Dates" : {},
    "Week" : {},
    "Birthday" : {
        True : "Birthday",
        False : "Not Birthday"
    },
    "Sub Query" : {},
    "Or Sub Query" : {},
    "Day Of Sub Query" : {},
    "Day After Sub Query" : {},
    "Day Before Sub Query" : {},
    "Game After Sub Query" : {},
    "Game Before Sub Query" : {},
    "Season Sub Query" : {},
    "Season After Sub Query" : {},
    "Season Before Sub Query" : {},
    "Moon Phase" : {},
    "Playing With" : {},
    "Playing Against" : {},
    "Previous Playing With" : {},
    "Previous Playing Against" : {},
    "Upcoming Playing With" : {},
    "Upcoming Playing Against" : {},
    "Playing Same Game" : {},
    "Playing Same Opponents" : {},
    "Playing Same Date" : {},
    "Thrown To" : {},
    "Result" : {},
    "Team Score" : {},
    "Opponent Score" : {},
    "Score Margin" : {},
    "Score Difference" : {},
    "Previous Team Score" : {},
    "Previous Opponent Score" : {},
    "Previous Score Margin" : {},
    "Previous Score Difference" : {},
    "Upcoming Team Score" : {},
    "Upcoming Opponent Score" : {},
    "Upcoming Score Margin" : {},
    "Upcoming Score Difference" : {},
    "Spread" : {},
    "Over/Under" : {},
    "Spread Margin" : {},
    "Over/Under Margin" : {},
    "Underdog" : {},
    "Favorite" : {},
    "Season" : {},
    "Season Reversed" : {},
    "Season Game" : {},
    "Career Game" : {},
    "Team Game" : {},
    "Career Game Reversed" : {},
    "Season Game Reversed" : {},
    "Team Game Reversed" : {},
    "First Half" : {},
    "Second Half" : {},
    "Days Rest" : {},
    "Starts Days Rest" : {},
    "Upcoming Starts Days Rest" : {},
    "Team League" : {},
    "Opponent League" : {},
    "Interleague" : {},
    "Intraleague" : {},
    "Quarter" : {},
    "Overtime" : {},
    "RedZone" : {},
    "Down" : {},
    "Down Distance" : {},
    "Field Position" : {},
    "Quarter Time" : {},
    "Quarter Time Remaining" : {},
    "Pass Distance" : {},
    "Pass Direction" : {},
    "Current Team Score" : {},
    "Current Opponent Score" : {},
    "Current Score Margin" : {},
    "Current Score Difference" : {},
    "Team Conference" : {},
    "Opponent Conference" : {},
    "Interconference" : {},
    "Intraconference" : {},
    "Team Division" : {},
    "Opponent Division" : {},
    "Interdivsion" : {},
    "Intradivision" : {},
    "Upcoming Days Rest" : {},
    "Games Rest" : {},
    "Starts Rest" : {},
    "Days In A Row" : {},
    "Games In A Row" : {},
    "Starts In A Row" : {},
    "Number" : {},
    "Year" : {},
    "Even Year" : {},
    "Odd Year" : {},
    "Winning Opponent" : {},
    "Losing Opponent" : {},
    "Tied Opponent" : {},
    "Winning Or Tied Opponent" : {},
    "Losing Or Tied Opponent" : {},
    "Current Winning Opponent" : {},
    "Current Losing Opponent" : {},
    "Current Tied Opponent" : {},
    "Current Winning Or Tied Opponent" : {},
    "Current Losing Or Tied Opponent" : {},
    "Playoff Opponent" : {},
    "Champ Winner Opponent" : {},
    "Conference Winner Opponent" : {},
    "Division Winner Opponent" : {},
    "Opponent Wins" : {},
    "Opponent Losses" : {},
    "Opponent Ties" : {},
    "Opponent Games Over 500" : {},
    "Opponent Win Percentage" : {},
    "Current Opponent Wins" : {},
    "Current Opponent Losses" : {},
    "Current Opponent Ties" : {},
    "Current Opponent Games Over 500" : {},
    "Current Opponent Win Percentage" : {},
    "Opponent Points Rank" : {},
    "Opponent Points Allowed Rank" : {},
    "Opponent Yards Rank" : {},
    "Opponent Yards Allowed Rank" : {},
    "Opponent Pass TD Rank" : {},
    "Opponent Pass TD Allowed Rank" : {},
    "Opponent Pass Yards Rank" : {},
    "Opponent Pass Yards Allowed Rank" : {},
    "Opponent ANY/A Rank" : {},
    "Opponent ANY/A Allowed Rank" : {},
    "Opponent Passer Rating Rank" : {},
    "Opponent Passer Rating Allowed Rank" : {},
    "Opponent Rush TD Rank" : {},
    "Opponent Rush TD Allowed Rank" : {},
    "Opponent Rush Yards Rank" : {},
    "Opponent Rush Yards Allowed Rank" : {},
    "Opponent Fantasy Position Rank" : {},
    "Winning Team" : {},
    "Losing Team" : {},
    "Tied Team" : {},
    "Winning Or Tied Team" : {},
    "Losing Or Tied Team" : {},
    "Current Winning Team" : {},
    "Current Losing Team" : {},
    "Current Tied Team" : {},
    "Current Winning Or Tied Team" : {},
    "Current Losing Or Tied Team" : {},
    "Playoff Team" : {},
    "Champ Winner Team" : {},
    "Conference Winner Team" : {},
    "Division Winner Team" : {},
    "Team Wins" : {},
    "Team Losses" : {},
    "Team Ties" : {},
    "Team Games Over 500" : {},
    "Team Win Percentage" : {},
    "Current Team Wins" : {},
    "Current Team Losses" : {},
    "Current Team Ties" : {},
    "Current Team Games Over 500" : {},
    "Current Team Win Percentage" : {},
    "Team Points Rank" : {},
    "Team Points Allowed Rank" : {},
    "Team Yards Rank" : {},
    "Team Yards Allowed Rank" : {},
    "Team Pass TD Rank" : {},
    "Team Pass TD Allowed Rank" : {},
    "Team Pass Yards Rank" : {},
    "Team Pass Yards Allowed Rank" : {},
    "Team ANY/A Rank" : {},
    "Team ANY/A Allowed Rank" : {},
    "Team Passer Rating Rank" : {},
    "Team Passer Rating Allowed Rank" : {},
    "Team Rush TD Rank" : {},
    "Team Rush TD Allowed Rank" : {},
    "Team Rush Yards Rank" : {},
    "Team Rush Yards Allowed Rank" : {},
    "Team Fantasy Position Rank" : {},
    "Previous Team" : {},
    "Upcoming Team" : {},
    "Previous Opponent" : {},
    "Upcoming Opponent" : {},
    "Previous Opponent" : {},
    "Upcoming Opponent" : {},
    "Previous Team Franchise" : {},
    "Upcoming Team Franchise" : {},
    "Previous Opponent Franchise" : {},
    "Upcoming Opponent Franchise" : {},
    "Previous Same Opponent" : {},
    "Upcoming Same Opponent" : {},
    "Previous Location" : {
        "home" : "Home",
        "away" : "Away"
    },
    "Upcoming Location" : {
        "home" : "Home",
        "away" : "Away"
    },
    "Previous Result" : {},
    "Upcoming Result" : {},
    "Previous Team Result" : {},
    "Upcoming Team Result" : {},
    "Stat" : {},
    "Previous Stat" : {},
    "Upcoming Stat" : {},
    "Season Stat" : {},
    "Previous Season Stat" : {},
    "Upcoming Season Stat" : {},
    "Formula" : {},
    "Season Formula" : {},
    "Max Streak Formula" : {},
    "Count Streak Formula" : {},
    "Total Games Stat" : {},
    "Min Stat" : {},
    "Max Stat" : {},
    "Max Streak" : {},
    "Max Stretch" : {},
    "Count Streak" : {},
    "Quickest" : {},
    "Longest" : {},
    "Holiday" : {},
    "After Bye" : {},
    "Before Bye" : {},
    "Game After Bye" : {},
    "Game Before Bye" : {},
    "Had Bye" : {},
    "Probable" : {},
    "Questionable" : {},
    "Doubtful" : {},
    "Injured" : {},
    "Injury" : {},
    "Force Dates" : False,
    "Ignore Start" : False
}

year_games_played = [
    {
        "start_year" : None,
        "end_year" : 1936,
        "games" : 12
    },
    {
        "start_year" : 1937,
        "end_year" : 1942,
        "games" : 11
    },
    {
        "start_year" : 1943,
        "end_year" : 1945,
        "games" : 10
    },
    {
        "start_year" : 1946,
        "end_year" : 1946,
        "games" : 11
    },
    {
        "start_year" : 1947,
        "end_year" : 1960,
        "games" : 12
    },
    {
        "start_year" : 1961,
        "end_year" : 1977,
        "games" : 14
    },
    {
        "start_year" : 1978,
        "end_year" : end_year - 1,
        "games" : 16
    },
    {
        "start_year" : end_year,
        "end_year" : end_year,
        "games" : None
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

    table_name = "passing"
    if not totals:
        totals = {}

    standard_dev_totals = {}
    ind_year_totals = {}

    current_games_by_team = calculate_current_games_by_team()

    standard_dev_stats = [
        "Yds/G",
        "Cmp%",
        "Y/A",
        "NY/A",
        "AY/A",
        "ANY/A",
        "TD%",
        "Int%",
        "Rate",
        "Sk%"
    ]

    headers_to_read = [
        "G",
        "Cmp",
        "Att",
        "Yds",
        "TD",
        "Int",
        "Sk",
        "SkYds"
    ]

    years = None
    if specific_year:
        years = [specific_year - 2, specific_year - 1, specific_year, specific_year + 1, specific_year + 2]
    else:
        years = range(start_year, end_year + 1)

    current_percent = 10
    for index, year in enumerate(years):
        request = urllib.request.Request(league_totals_url.format(year), headers=request_headers)
        try:
            response, player_page = url_request(request)
        except urllib.error.HTTPError as err:
            if err.status == 404:
                continue
            else:
                raise

        table = player_page.find("table", id=table_name)
        if not table:
            continue
    
        ind_year_totals[str(year)] = {}
        standard_dev_totals[str(year)] = {}

        for standard_dev_stat in standard_dev_stats:
            standard_dev_totals[str(year)][standard_dev_stat] = []

        for header in headers_to_read:
             ind_year_totals[str(year)][header] = 0.0

        header_columns = table.find("thead").find_all("th")
        header_values = []
        for header in header_columns:
            contents = header.find(text=True)
            header_values.append(contents)

        standard_table_rows = table.find("tbody").find_all("tr", recursive=False)
        for row in standard_table_rows:
            classes = row.get("class")
            if not classes or not "thead" in classes:
                player_stats = {
                    "Passing" : {}
                }
                for header in headers_to_read:
                    player_stats["Passing"][header] = 0.0

                columns = row.find_all("td", recursive=False)
                for sub_index, column in enumerate(columns):
                    real_index = sub_index + 1
                    header_value = header_values[real_index]
                    if header_value == "Tm":
                        link = column.find("a")
                        if link:
                            player_stats["Passing"]["Tm"] = link["href"].split("/")[2].upper()
                        else:
                            player_stats["Passing"]["Tm"] = "TOT"
                    else:
                        column_contents = column.find(text=True)
                        if column_contents:
                            if column.get("data-stat") == "pass_sacked_yds":
                                header_value = "SkYds"
                            
                            if header_value in headers_to_read:
                                column_value = float(column_contents)
                                ind_year_totals[str(year)][header_value] += column_value
                                player_stats["Passing"].update({header_value : column_value})

                games_per_season = None
                for year_game_played in year_games_played:
                    year_start_year = year_game_played["start_year"]
                    year_end_year = year_game_played["end_year"]
                    if (not year_start_year or year >= year_start_year) and (not year_end_year or year <= year_end_year):
                        games_per_season = year_game_played["games"]
                        if not games_per_season:
                            if player_stats["Passing"]["Tm"] == "TOT":
                                games_per_season = statistics.mode(current_games_by_team.values())
                            else:
                                games_per_season = current_games_by_team[player_stats["Passing"]["Tm"]]
                                
                if (player_stats["Passing"]["Att"] / games_per_season) >= 14:
                    for standard_dev_stat in standard_dev_totals[str(year)]:
                        standard_dev_stat_val = calculate_formula(standard_dev_stat, formulas["Passing"][standard_dev_stat], player_stats, "Passing", None, None, None)
                        standard_dev_totals[str(year)][standard_dev_stat].append(standard_dev_stat_val)

        count = index + 1
        percent_complete = 100 * (count / len(years))
        if not specific_year and count != 1 and percent_complete >= current_percent:
            logger.info(str(current_percent) + "%")
            current_percent += 10

    logger.info("Calculating yearly batches")
    current_percent = 10
    for index, year in enumerate([specific_year - 1, specific_year, specific_year + 1] if specific_year else years):
        if str(year) in ind_year_totals:
            totals[str(year)] = {}

            prev_year = year - 1
            next_year = year + 1

            total_stats = {
                "Passing" : {}
            }
            for header in headers_to_read:
                total_stats["Passing"][header] = 0.0
            total_standard_devs = {}
            for standard_dev_stat in standard_dev_stats:
                total_standard_devs[standard_dev_stat] = []

            for header in ind_year_totals[str(year)]:
                total_stats["Passing"][header] += ind_year_totals[str(year)][header]
            for standard_dev_stat in standard_dev_totals[str(year)]:
                total_standard_devs[standard_dev_stat] += standard_dev_totals[str(year)][standard_dev_stat]

            if str(prev_year) in ind_year_totals:
                for header in ind_year_totals[str(prev_year)]:
                    total_stats["Passing"][header] += ind_year_totals[str(prev_year)][header]
                for standard_dev_stat in standard_dev_totals[str(prev_year)]:
                    total_standard_devs[standard_dev_stat] += standard_dev_totals[str(prev_year)][standard_dev_stat]

            if str(next_year) in ind_year_totals and (not skip_current_year or next_year != end_year):
                for header in ind_year_totals[str(next_year)]:
                    total_stats["Passing"][header] += ind_year_totals[str(next_year)][header]
                for standard_dev_stat in standard_dev_totals[str(next_year)]:
                    total_standard_devs[standard_dev_stat] += standard_dev_totals[str(next_year)][standard_dev_stat]

            for standard_dev_stat in standard_dev_stats:
                stat_val = calculate_formula(standard_dev_stat, formulas["Passing"][standard_dev_stat], total_stats, "Passing", None, None, None)
                totals[str(year)][standard_dev_stat] = stat_val
                standard_dev_val = statistics.stdev(total_standard_devs[standard_dev_stat])
                totals[str(year)]["std_" + standard_dev_stat] = standard_dev_val

    return totals

def calculate_current_games_by_team():
    logger.info("Getting current year game data for year " + str(end_year))
    request = urllib.request.Request(current_year_standings_url.format(end_year), headers=request_headers)
    response, player_page = url_request(request)
    table_names = ["AFC", "NFC"]
    teams = {}

    for table_name in table_names:
        table = player_page.find("table", id=table_name)

        header_columns = table.find("thead").find_all("th")
        header_values = []
        for header in header_columns:
            contents = header.find(text=True)
            header_values.append(contents)

        standard_table_rows = table.find("tbody").find_all("tr")
        for row in standard_table_rows:
            classes = row.get("class")
            if not classes or not "thead" in classes:
                games = 0
                team = None
                columns = row.find_all("td", recursive=False)
                columns.insert(0, row.find("th"))
                for sub_index, column in enumerate(columns):
                    header_value = header_values[sub_index]
                    if header_value == "Tm":
                        team = column.find("a")["href"].split("/")[2].upper()
                    elif header_value == "W" or header_value == "L" or header_value == "T":
                        games += int(column.find(text=True))
                teams[team] = games
    return teams

def url_request(request, timeout=10):
    failed_counter = 0
    while(True):
        try:
            response = urllib.request.urlopen(request, timeout=timeout)
            text = response.read()
            try:
                text = text.decode(response.headers.get_content_charset())
            except UnicodeDecodeError:
                return response, BeautifulSoup(text, "html.parser")

            return response, BeautifulSoup(text, "lxml")
        except Exception:
            failed_counter += 1
            if failed_counter > max_request_retries:
                raise

        delay_step = 10
        logger.info("#" + str(threading.get_ident()) + "#   " + "Retrying in " + str(retry_failure_delay) + " seconds to allow request to " + request.get_full_url() + " to chill")
        time_to_wait = int(math.ceil(float(retry_failure_delay)/float(delay_step)))
        for i in range(retry_failure_delay, 0, -time_to_wait):
            logger.info("#" + str(threading.get_ident()) + "#   " + str(i))
            time.sleep(time_to_wait)
        logger.info("#" + str(threading.get_ident()) + "#   " + "0")

def calculate_formula(stat, formula, data, header, headers, player_type, all_rows, safe_eval=False):
    if header == "Defense Per Game/Snap":
        over_header = "Defense"
    else:
        over_header = header

    if formula == "Special":
        if stat == "Rate":
            return calculate_passer_rating(data[header], header)
        elif stat == "Fmb%":
            return calculate_fumble_percent(data, all_rows)
        elif stat == "Rec":
            return str(data[header]["QBW"]) + ":" + str(data[header]["QBL"]) + ":" + str(data[header]["QBT"])
        elif stat == "TmRec":
            return str(data[header]["TmW"]) + ":" + str(data[header]["TmL"]) + ":" + str(data[header]["TmT"])
        elif stat == "ATS TmRec":
            return str(data[header]["ATSTeamW"]) + ":" + str(data[header]["ATSTeamL"]) + ":" + str(data[header]["ATSTeamT"])
        elif stat == "O/U TmRec":
            return str(data[header]["OUTeamW"]) + ":" + str(data[header]["OUTeamL"]) + ":" + str(data[header]["OUTeamT"])
        elif stat == "Rec/17G":
            return str(data[header]["QBW/17G"]) + ":" + str(data[header]["QBL/17G"]) + ":" + str(data[header]["QBT/17G"])
        elif stat == "TtlYds":
            total_yds = 0
            if "Passing" in data:
                total_yds += data["Passing"]["Yds"]
            if "Rushing" in data:
                total_yds += data["Rushing"]["Yds"]
            if "Receiving" in data:
                total_yds += data["Receiving"]["Yds"]
            return total_yds
        elif stat == "Tnv":
            total_tnv = 0
            all_rows = [data] if not all_rows else all_rows
            for row in all_rows:
                if "Year" in row["Shared"] and row["Shared"]["Year"] >= 1994:
                    if "Passing" in row and "Int" in row["Passing"]:
                        total_tnv += row["Passing"]["Int"]
                    if "Rushing" in row and "FmbLst" in row["Rushing"]:
                        total_tnv += row["Rushing"]["FmbLst"]
            return total_tnv
        elif stat == "TtlTD":
            total_td = 0
            if "Passing" in data:
                total_td += data["Passing"]["TD"]
            if "Rushing" in data:
                total_td += data["Rushing"]["TD"]
            if "Receiving" in data:
                total_td += data["Receiving"]["TD"]
            return total_td
        elif stat == "TtlTDTnv":
            total_td = 0
            all_rows = [data] if not all_rows else all_rows
            for row in all_rows:
                if "Year" in row["Shared"] and row["Shared"]["Year"] >= 1994:
                    if "Passing" in row and "TD" in row["Passing"]:
                        total_td += row["Passing"]["TD"]
                    if "Rushing" in row and "TD" in row["Rushing"]:
                        total_td += row["Rushing"]["TD"]
                    if "Receiving" in row and "TD" in row["Receiving"]:
                        total_td += row["Receiving"]["TD"]
            return total_td
        elif stat == "Ttl TD":
            return data["Defense"]["FR TD"] + data["Defense"]["Int TD"]
        elif stat == "TD%" or stat == "TtlTD%":
            total_attempts = 0
            if "Passing" in data:
                total_attempts += data["Passing"]["Att"]
            if "Rushing" in data:
                total_attempts += data["Rushing"]["Att"]
            if "Receiving" in data:
                total_attempts += data["Receiving"]["Rec"]
            try:
                return data["Era Adjusted Passing"]["TtlTD"] / total_attempts
            except ZeroDivisionError:
                return 0
        elif stat == "Pass1D%":
            return calculate_1D_percent(data, header, all_rows, "Pass")
        elif stat == "Rush1D%":
            return calculate_1D_percent(data, header, all_rows, "Rush")
        elif stat == "Rec1D%":
            return calculate_1D_percent(data, header, all_rows, "Rec")
        elif stat == "WeightAV":
            avs = []
            all_rows = [data] if not all_rows else all_rows
            for row in all_rows:
                if header in row and "AV" in row[header]:
                    avs.append(row[header]["AV"])
            avs = sorted(avs, reverse=True)

            start_percent = 100
            weighted_av = 0
            for av in avs:
                weighted_av += av * (start_percent / 100)
                if start_percent >= 5:
                    start_percent -= 5
            return weighted_av
        elif stat == "TmW":
            return calculate_team_win_losses(data, all_rows, "W")
        elif stat == "TmL":
            return calculate_team_win_losses(data, all_rows, "L")
        elif stat == "TmT":
            return calculate_team_win_losses(data, all_rows, "T")
        elif stat == "TmScore":
            return data["Shared"]["Team Score"]
        elif stat == "OppScore":
            return data["Shared"]["Opponent Score"]
    elif formula == "MAX":
        max_value = 0
        all_rows = [data] if not all_rows else all_rows
        for row in all_rows:
            if header in row and stat in row[header] and row[header][stat] > max_value:
                max_value = row[header][stat]
        return max_value
    else:
        earliest_invalid_date = None
        formula = formula.lower()

        if all_rows:
            if is_invalid_stat(header, stat, data, False) == float("inf"):
                earliest_invalid_date = float("inf")
            else:
                if stat == "custom_formula":
                    for over_header in headers[player_type["da_type"]]:
                        if over_header != "Shared":
                            for sub_stat in data[over_header]:
                                temp_earliest_invalid_date = calculate_earliest_invalid_date(sub_stat, over_header, data, formula, earliest_invalid_date, stat)
                                if temp_earliest_invalid_date:
                                    earliest_invalid_date = temp_earliest_invalid_date
                else:
                    for sub_stat in data[over_header]:
                        temp_earliest_invalid_date = calculate_earliest_invalid_date(sub_stat, over_header, data, formula, earliest_invalid_date, stat)
                        if temp_earliest_invalid_date:
                            earliest_invalid_date = temp_earliest_invalid_date

                if "Shared" in data:
                    for sub_stat in data["Shared"]:
                        if stat == "custom_formula" or (sub_stat != "Tm" and sub_stat != "RawTm" and sub_stat != "RawOpponent" and sub_stat != "Result" and sub_stat != "is_playoffs" and (not sub_stat in qualifier_map or sub_stat == "Team Score" or sub_stat == "Opponent Score")):
                            temp_earliest_invalid_date = calculate_earliest_invalid_date(sub_stat, "Shared", data, formula, earliest_invalid_date, stat)
                            if temp_earliest_invalid_date:
                                earliest_invalid_date = temp_earliest_invalid_date

        if stat == "custom_formula":
            for over_header in headers[player_type["da_type"]]:
                if over_header != "Shared":
                    for sub_stat in data[over_header]:
                        formula = replace_formula(data, over_header, sub_stat, formula, all_rows, earliest_invalid_date, stat)
        else:
            for sub_stat in data[over_header]:
                formula = replace_formula(data, over_header, sub_stat, formula, all_rows, earliest_invalid_date, stat)

        if "Shared" in data:
            for sub_stat in data["Shared"]:
                if stat == "custom_formula" or (sub_stat != "Tm" and sub_stat != "RawTm" and sub_stat != "RawOpponent" and sub_stat != "Result" and sub_stat != "is_playoffs" and (not sub_stat in qualifier_map or sub_stat == "Team Score" or sub_stat == "Opponent Score")):
                    formula = replace_formula(data, "Shared", sub_stat, formula, all_rows, earliest_invalid_date, stat)

        try:
            if safe_eval:
                return float(numexpr.evaluate(formula))
            else:
                return eval(formula)
        except ZeroDivisionError:
            if "isinf" in stat_groups[header][stat]:
                if data[header][stat_groups[header][stat]["isinf"]] == 0:
                    return 0.0
                else:
                    return math.inf
            else:
                return 0.0
        except Exception:
            if stat == "custom_formula":
                raise CustomMessageException("Invalid formula!")
            else:
                raise

def calculate_passer_rating(passing_data, header="Passing"):
    try:        
        if header == "Advanced/Defense":
            completions = passing_data.get("Cmp", 0)
        elif header == "Passing":
            completions = passing_data.get("Cmp", 0)
        else:
            completions = passing_data.get("Rec", 0)

        if header == "Advanced/Defense":
            attemps = passing_data.get("Tgt", 0)
        elif header == "Passing":
            attemps = passing_data.get("Att", 0)
        else:
            attemps = passing_data.get("Tgt", 0)

        if header == "Advanced/Defense":
            yards = passing_data.get("Yds", 0)
        elif header == "Passing":
            yards = passing_data.get("Yds", 0)
        else:
            yards = passing_data.get("RecYds", 0)

        if header == "Advanced/Defense":
            TDs = passing_data.get("TD", 0)
        elif header == "Passing":
            TDs = passing_data.get("TD", 0)
        else:
            TDs = passing_data.get("RecTD", 0)
        INTs = passing_data.get("Int", 0)

        a = ((completions / attemps) - 0.3) * 5
        if a > 2.375:
            a = 2.375
        elif a < 0:
            a = 0

        b = ((yards / attemps) - 3) * .25
        if b > 2.375:
            b = 2.375
        elif b < 0:
            b = 0

        c = (TDs / attemps) * 20
        if c > 2.375:
            c = 2.375
        elif c < 0:
            c = 0

        d = 2.375 - ((INTs / attemps) * 25)
        if d > 2.375:
            d = 2.375
        elif d < 0:
            d = 0

        return ((a + b + c + d) / 6) * 100
    except ZeroDivisionError:
        return 0.0

def calculate_fumble_percent(data, all_rows):
    fumbles = data["Rushing"]["Fmb"]

    invalid_date_fumbles = is_invalid_stat("Rushing", "Fmb", data, False)
    rushing_attempts = calculate_valid_value("Att", "Rushing", data["Rushing"]["Att"], invalid_date_fumbles, all_rows)

    receptions = 0
    if "Receiving" in data:
        receptions = calculate_valid_value("Rec", "Receiving", data["Receiving"]["Rec"], invalid_date_fumbles, all_rows)

    sacks = 0
    if "Passing" in data:
        sacks = calculate_valid_value("Sk", "Passing", data["Passing"]["Sk"], invalid_date_fumbles, all_rows)

    returns = 0
    if "Kick Returns" in data:
        returns += calculate_valid_value("Sk", "Kick Returns", data["Kick Returns"]["Rt"], invalid_date_fumbles, all_rows)
    if "Punt Returns" in data:
        returns += calculate_valid_value("Sk", "Punt Returns", data["Punt Returns"]["Rt"], invalid_date_fumbles, all_rows)

    try:
        return fumbles / (rushing_attempts + receptions + sacks)
    except ZeroDivisionError:
        return 0.0

def calculate_1D_percent(data, header, all_rows, type):
    attempts = 0
    if type == "Pass":
        first_downs = data[header]["Pass1D"]
        invalid_date_1Ds = is_invalid_stat(header, "Pass1D", data, False)
        if "Passing" in data:
            attempts += calculate_valid_value("Att", "Passing", data["Passing"]["Att1D"], invalid_date_1Ds, all_rows)
    elif type == "Rush":
        first_downs = data[header]["Rush1D"]
        invalid_date_1Ds = is_invalid_stat(header, "Rush1D", data, False)
        if "Rushing" in data:
            attempts += calculate_valid_value("Att", "Rushing", data["Rushing"]["Att1D"], invalid_date_1Ds, all_rows)
    else:
        first_downs = data[header]["Rec1D"]
        invalid_date_1Ds = is_invalid_stat(header, "Rec1D", data, False)
        if "Receiving" in data:
            attempts += calculate_valid_value("Rec", "Receiving", data["Receiving"]["Rec1D"], invalid_date_1Ds, all_rows)

    try:
        return first_downs / attempts
    except ZeroDivisionError:
        return 0.0

def calculate_team_win_losses(data, all_rows, result):
    if not all_rows:
        all_rows = [data]

    result_count = 0
    for row in all_rows:
        if "Result" in row["Shared"] and row["Shared"]["Result"] == result:
            result_count += 1
    return result_count

def calculate_earliest_invalid_date(stat, header, data, formula, earliest_invalid_date, real_stat):
    if real_stat == "custom_formula":
        if header in data and stat in data[header]:
            header_match = r"(?:" + header.lower() + r")"
            if header == "Era Adjusted Passing":
                header_match = r"(?:era adjusted passing|total)"
            elif header == "Scrimmage/All Purpose":
                header_match = r"(?:scrimmage/all purpose|scrimmage)"
            if re.search(r"(?:(?<![\w~+])(?=[\w~+])|(?<=[\w~+])(?![\w~+]))" + header_match + r"~" + re.escape(stat.lower()) + r"(?:(?<![\w~+])(?=[\w~+])|(?<=[\w~+])(?![\w~+]))", formula):
                invalid_date = is_invalid_stat(header, stat, data, False)
                if invalid_date:
                    if not earliest_invalid_date or invalid_date > earliest_invalid_date:
                        return invalid_date
            elif re.search(r"(?:(?<![\w~+])(?=[\w~+])|(?<=[\w~+])(?![\w~+]))" + re.escape(stat.lower()) + r"(?:(?<![\w~+])(?=[\w~+])|(?<=[\w~+])(?![\w~+]))", formula):
                invalid_date = is_invalid_stat(header, stat, data, False)
                if invalid_date:
                    if not earliest_invalid_date or invalid_date > earliest_invalid_date:
                        return invalid_date
    else:
        if re.search(r"(?:(?<![\w+])(?=[\w+])|(?<=[\w+])(?![\w+]))" + re.escape(stat.lower()) + r"(?:(?<![\w+])(?=[\w+])|(?<=[\w+])(?![\w+]))", formula):
            invalid_date = is_invalid_stat(header, stat, data, False)
            if invalid_date:
                if not earliest_invalid_date or invalid_date > earliest_invalid_date:
                    return invalid_date

def replace_formula(data, header, stat, formula, all_rows, earliest_invalid_date, real_stat):
    if real_stat == "custom_formula":
        if header in data and stat in data[header]:
            value = data[header][stat]

        if isinstance(value, (int, float)):
            value = calculate_valid_value(stat, header, value, earliest_invalid_date, all_rows)
            header_match = r"(?:" + header.lower() + r")"
            if header == "Era Adjusted Passing":
                header_match = r"(?:era adjusted passing|total)"
            elif header == "Scrimmage/All Purpose":
                header_match = r"(?:scrimmage/all purpose|scrimmage)"
            formula, num_subs = re.subn(r"(?:(?<![\w~+])(?=[\w~+])|(?<=[\w~+])(?![\w~+]))" + header_match + r"~" + re.escape(stat.lower()) + r"(?:(?<![\w~+])(?=[\w~+])|(?<=[\w~+])(?![\w~+]))", str(value), formula)
            if not num_subs:
                formula = re.sub(r"(?:(?<![\w~+])(?=[\w~+])|(?<=[\w~+])(?![\w~+]))" + re.escape(stat.lower()) + r"(?:(?<![\w~+])(?=[\w~+])|(?<=[\w~+])(?![\w~+]))", str(value).lower(), formula)
        return formula
    else:
        value = data[header][stat]
        if isinstance(value, (int, float)):
            value = calculate_valid_value(stat, header, value, earliest_invalid_date, all_rows)
            return re.sub(r"(?:(?<![\w+])(?=[\w+])|(?<=[\w+])(?![\w+]))" + re.escape(stat.lower()) + r"(?:(?<![\w+])(?=[\w+])|(?<=[\w+])(?![\w+]))", str(value).lower(), formula)
        else:
            return formula
            
def calculate_valid_value(stat, header, value, earliest_invalid_date, all_rows):
    if not earliest_invalid_date:
        return value
    else:
        for row_data in all_rows:
            if header in row_data and stat in row_data[header]:
                date = row_data["Shared"]["Year"]
                if date < earliest_invalid_date:
                    value = value - row_data[header][stat]
        return value

def is_invalid_stat(header, stat, data, count_inconsistent, player_data=None):
    if "YearStart" in data["Shared"] and data["Shared"]["YearStart"]:
        for index, date_start in enumerate(data["Shared"]["DateStart"]):
            is_invalid = is_invalid_year_stat(header, stat, data, count_inconsistent, date_start, data["Shared"]["YearStart"][index], player_data)
            if is_invalid:
                return is_invalid          
    return None

def is_invalid_year_stat(header, stat, data, count_inconsistent, date_start, year, player_data=None):
    if "1D" in stat and "hide_first_downs" in data["Shared"] and data["Shared"]["hide_first_downs"]:
        return float("inf")

    if player_data:
        if stat == "GS":
            if any(True for true_player_type in player_data["stat_values"]["Shared"]["Types"] if true_player_type == "QB" or true_player_type == "B"):
                return None

    if "valid_since" in stat_groups[header][stat]:
        if isinstance(date_start, int) and ((not data["Shared"]["is_playoffs"] or data["Shared"]["is_playoffs"] == "No") or "1D" in stat or "Lng" in stat):
            if "season" in stat_groups[header][stat]["valid_since"] and year < stat_groups[header][stat]["valid_since"]["season"]:
                return stat_groups[header][stat]["valid_since"]["season"]
            elif count_inconsistent and "inconsistent" in stat_groups[header][stat]["valid_since"] and year < stat_groups[header][stat]["valid_since"]["inconsistent"]:
                return stat_groups[header][stat]["valid_since"]["inconsistent"]
            elif count_inconsistent and "playoff-inconsistent" in stat_groups[header][stat]["valid_since"] and year < stat_groups[header][stat]["valid_since"]["playoff-inconsistent"] and (data["Shared"]["is_playoffs"] and data["Shared"]["is_playoffs"] != "No"):
                return stat_groups[header][stat]["valid_since"]["playoff-inconsistent"]
        else:
            if "game" in stat_groups[header][stat]["valid_since"] and (stat_groups[header][stat]["valid_since"]["game"] == None or year < stat_groups[header][stat]["valid_since"]["game"]) and (not data["Shared"]["is_playoffs"] or data["Shared"]["is_playoffs"] == "No"):
                if stat_groups[header][stat]["valid_since"]["game"] == None:
                    return float("inf")
                else:
                    return stat_groups[header][stat]["valid_since"]["game"]
            elif "game-np" in stat_groups[header][stat]["valid_since"] and year < stat_groups[header][stat]["valid_since"]["game-np"]:
                if data["Shared"]["is_playoffs"] == "Include":
                    if count_inconsistent:
                        return stat_groups[header][stat]["valid_since"]["game-np"]
                elif data["Shared"]["is_playoffs"] != "Only":
                    return stat_groups[header][stat]["valid_since"]["game-np"]
            elif "game" in stat_groups[header][stat]["valid_since"] and (stat_groups[header][stat]["valid_since"]["game"] == None or year < stat_groups[header][stat]["valid_since"]["game"]) and ("game-np" not in stat_groups[header][stat]["valid_since"] or year < stat_groups[header][stat]["valid_since"]["game-np"]):
                if stat_groups[header][stat]["valid_since"]["game"] == None:
                    return float("inf")
                else:
                    return stat_groups[header][stat]["valid_since"]["game"]
            elif count_inconsistent and "inconsistent-game" in stat_groups[header][stat]["valid_since"] and year < stat_groups[header][stat]["valid_since"]["inconsistent-game"]:
                return stat_groups[header][stat]["valid_since"]["inconsistent"]
            elif count_inconsistent and "playoff-inconsistent" in stat_groups[header][stat]["valid_since"] and year < stat_groups[header][stat]["valid_since"]["playoff-inconsistent"] and (data["Shared"]["is_playoffs"] and data["Shared"]["is_playoffs"] != "No"):
                return stat_groups[header][stat]["valid_since"]["playoff-inconsistent"]
    return None

def round_value(value, round_val=0):
    if value == math.inf:
        return value
    decimal_val = decimal.Decimal(str(value)).quantize(
        decimal.Decimal(("{:." + str(round_val) + "f}").format(0)), 
        rounding=decimal.ROUND_HALF_UP
    )
    if round_val == 0:
        return int(decimal_val)
    else:
        return float(decimal_val)

class CustomMessageException(Exception):
    message = None
    def __init__(self, message):
        super().__init__(message)
        self.message = message

if __name__ == "__main__":
    main()
