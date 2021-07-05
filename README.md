# Sports Comparision Bots
This page is for information generic to all the comparison bots. For information specific to each bot check out the bot's wiki page

# Format

To start a comparison, make a comment on reddit or send a message to the bot in the following format:

**!mlbcompare \<Players To Compare> [Query Options]**

**!nflcompare \<Players To Compare> [Query Options]**

**!nhlcompare \<Players To Compare> [Query Options]**

# Players To Compare
A comma separated list of players to include in the comparison, up to 20 players. This just uses Sports-Reference's search page, so anything that works on there should work with the bot.

| Type        | Example |
| ------------- | -----|
| By Name | Mike Trout, Bryce Harper|
| By Full Name | Michael Nelson Trout, Bryce Aron Max Harper|
| By Nickname | TB12, The Sheriff, Big Ben |
| By Player ID | ahose01, ahose02 |
| Combining Player Stats | Ruth + Gehrig, Aaron + Eddie Matthews |

# Query Options
These query options will work with any of the bots. Each bots own page will have the options specific to that bot

Type| Explanation | Examples
---|---|----
Career | The default comparison when there's no option provided, over the players entire career | career, (when there's no option provided)
Season | Comparison over entire seasons or season ranges. For NHL this refers to the starting year of the season, so 2010 refers to the 2010-2011 season | 2019, 2010-2015
Season shortcuts | Shortcuts to grab first/last seasons | First 4 seasons, Last season, last year
First/Last Seasons | Automatically compare all the players first/last X seasons, based on the player with the least amount of seasons | first-seasons, last-seasons
Date | Comparison between a specific date range. Can use MIN or MAX/TODAY as shortcuts | 2019-11-03 TO 2019-12-01, MIN TO 2015-10-27, 2016-12-04 TO TODAY, 1976-12-09
Date shortcuts | Shortcuts for various date ranges| Last month, Last 3 days, First week, Last 2 years-calendar
Age| Only include games before (the default) or after a players age. Can also do an age range | age 30, before age 25y-172d, after age 35, age 20~25
Season Age| Same as age, but based on entire season age instead of specific date rage. Season age is calculated using the same method as Sports-Reference | season-age 30, after season-age 35, season-age 20~25
Current Age | Includes games based on the age of the youngest player in the comparison | current-age
Current Season Age | Includes seasons based on the age of the youngest player in the comparison | current-season-age
Games | First or last games. By default career games, but can specify a specific season. Can also specify a range instead of first/last | First 200 games, Last 20 games, first 6 games 2012, games 50-100, games 50-100 reversed
Starts | Can have any comparison only include starts, or only include non starts| starts, last 10 starts, first 20 games no starts
First/Last Games | Automatically compare all the players first/last X games (or starts), based on the player with the least amount of games| first-games, last-games, first starts
Playoffs | The default is to only show regular season stats, but you can get any comparison to only include playoff stats or include both playoffs and regular season stats combined asked. For NHL this now refers to the ending year of the season, so 2010 refers to playoffs of the 2009-2010 season | playoffs, 2019 playoffs, Last 20 games including playoffs
Playoff shortcuts| Shortcuts to only grab certain playoff rounds | World Series, Stanley Cup, Super Bowl, Conference Finals, First Round
Series Game | Only grab certain playoff series games | series-game:7, series-game:1-4
Location | Can have any comparison only be for home/away games| away, 2016 away, last 10 home starts
Team | Can have any comparison only include while playing for a specific team, or a combo of em. Based on the abbreviations used by Sports Reference | T:NYY, 2018 T:NYR-WSH
Opponent | Can have any comparison only include against a specific opponent or a combo of em. Based on the abbreviations used by Sports Reference | O:NYY, 2018 O:NYR-WSH
Rookie | Can have any comparison only include games the player was rookie-eligible | Rookie
First/Second half | Can have any comparison only include the first or second half of seasons. For seasons with an all star game the date of the game determines first/second half. For seasons without an all star game (or any NFL season), the season is just cut in half to determine first/second half | First-half, second-half, 2017 first-half
Number | Only include when a player was wearing certain number(s) | number:4, number:5-9
Stat | Can have any comparison only include games where a player had a certain stat value, or multiple. Will work with any stat you see in the comparison | Stat:HR, Stat:PIM=2, Stat:TD=2-4
Max Stat | Can find the game, week, month, or season where the player had the max value for a stat. For example find the best 5 season stretch in terms of batting average a player had, best 10 game stretch in terms of goals, etc. Can also do "Min-Stat" for the worst stretch. | Max-Stat:AVG:Seasons~5, Max-Stat:G:Games~10
Max Streak | Can find the longest game or season streak where a player had a certain value for a stat | Max-Streak:HR, Max-Streak:G=2
Playing with | Can have any comparison only include playing with a specific player. You can also use "starting-with" to only include games both players started | playing-with:(mike trout), starting-with:(peyton manning)
Playing against | Can have any comparison only include playing against a specific player.  You can also use "starting-against" to only include games both players started | playing-against:(mike trout), starting-against:(lundqvist)
Game | Can have any comparison only include a specific season game or game range. | Game:1-8, 2015 Game:7, 2018 Gm:6-10
Career Game | Can have any comparison only include a specific career game or career game range. | Career-Game:7, Cg:50-100
Days Rest | Can have any comparison only include a games where a player had a specific amount of days rest, or a range of days rest. | 2015 Days-Rest:7, 2018 Dr:6-10, Days-Rest:1-8
Days/Games In A Row | Can have any comparison only include games where a player played a specific amount of days/games in a row, including the given game. Can provided a range of days/games | 2015 Days-In-A-Row:3, 2018 Games-In-A-Row:2-4, Games-In-A-Row:1-3
Result | Can have any comparison only include games the player won/lost/tied | Win, 2018 Loss, Tie
Month | Can have any comparison only include during a specific month, or a combo of em | December, 2018 June-July
Temperate Season | Can have any comparison only include during a season. This is determined by the equinox/solstice days of that year | summer, winter, fall, spring
Day | Can have a comparison only count games played on a certain day, or a combo of them | Sunday, 2018 Saturday-Sunday
Date | Can have a comparison only count games played on a certain day of month, or a combo of them |Dt:1st, 2018 Date:20th-21st
Dates | Can include games that only occurred in an arbitrary list of date |dates:(01/01/2000-12/12/2001-02/02/2003)
Holiday | Can bring back games on a certain holiday. Should work with a good amount of US holidays | holiday:(Thanksgiving), holiday:(Fathers Day)
Birthday | Can have any comparison only include games on a players birthday |Birthday, 2018 Birthday
Negation | Options can be negated, pulling back only results which don't match the option. Wont work with Season or Date options, however you can alternatively accomplish negation through combination | Not O:BAL, Not playing-with:(peyton manning)
Combination | Can combine options together. Useful if you want to exclude certain dates/seasons, combine rounds, or combine other stuff | 2010-2014 + 2016-TODAY, 2019-11-03 TO 2019-12-01 + 2019-12-05 TO 2019-12-15, stanley cup + conference finals
Difference | Can also find the difference between options. For example finding out how much better a player does at home vs away | home diff away
Best/Worst Seasons | Special mode where you'll see the best/worst season stretch the player for each stat | show-best-season, show-worst-season:3
Seasons Leading | Special mode where you'll see how often a player led the league, or finished in the top X, of each stat | show-seasons-leading, show-seasons-leading:5
Special Stats | Some stats are hidden by default, but can be configured to be shown through the query. These include the team record or team score in games the player has played in | show-record, last 20 games show-score

# Search Results
I use my own sorting method when multiple players come back in a search. The two biggest factors are if a player is currently active or made the HOF, however it also takes into account making all star games/pro bowls, career length, etc. If the comparison isn't bringing back the right players, usually you can get the right one by specifying a full name (William Michael Smith vs William Dills Smith). In even rarer cases where full names are exactly the same, you can use Sports Reference IDs (ahose01 vs ahose02).

# Bot not working?
I don't have the bot looking for comments on all of reddit, just a specific list of subs. If you want me to add a new sub just hit me up on reddit or open a issue

# Reddit Accounts

[mlbcomparebot](https://www.reddit.com/user/mlbcomparebot)

[nflcomparebot](https://www.reddit.com/user/nflcomparebot)

[nhlcomparebot](https://www.reddit.com/user/nhlcomparebot)

[Sweetpotatonvenison](https://www.reddit.com/user/Sweetpotatonvenison) (Non-bot account I actually use reddit with and check for messages)

# General Usage/Testing
To just randomly use the bot you can send a message to right bots account. I also usually have a thread up on the bots [subreddit](https://www.reddit.com/r/sportscomparebots) for testing
