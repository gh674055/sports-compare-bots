from convertdate import holidays, hebrew
from pytz import timezone
import datetime

def thanksgiving(date, church, country, obseverd, eve):
    if country == "usa" and date.year > 1939:
        holiday_date = holidays.nth_day_of_month(4, holidays.THU, holidays.NOV, date.year)
    else:
        holiday_date = holidays.thanksgiving(date.year, country=country)
    
    if eve:
        holiday_date -= datetime.timedelta(days=1)
    
    holiday_date = datetime.datetime(holiday_date[0], holiday_date[1], holiday_date[2]).date()
    return date == holiday_date

def daylight_saving(date, church, country, obseverd, eve):
    return daylight_savings(date, church, country, obseverd, eve)

def daylight_saving_start(date, church, country, obseverd, eve):
    return daylight_savings_start(date, church, country, obseverd, eve)

def daylight_saving_end(date, church, country, obseverd, eve):
    return daylight_savings_end(date, church, country, obseverd, eve)

def daylight_savings(date, church, country, obseverd, eve):
    daylight_savings_times = get_savings_times(date, country, eve)

    return date in daylight_savings_times

def daylight_savings_start(date, church, country, obseverd, eve):
    daylight_savings_times = get_savings_times(date, country, eve)
    if daylight_savings_times:
        daylight_savings_times.pop(0)

    return date in daylight_savings_times

def daylight_savings_end(date, church, country, obseverd, eve):
    daylight_savings_times = get_savings_times(date, country, eve)
    if daylight_savings_times:
        daylight_savings_times.pop()

    return date in daylight_savings_times

def get_savings_times(date, country, eve):
    if country == "usa":
        tz = timezone("US/Eastern")
    else:
        tz = timezone(country)

    daylight_savings_times = []
    for pot_date in tz._utc_transition_times:
        if pot_date.year == date.year:
            if eve:
                daylight_savings_times.append(pot_date.date() - datetime.timedelta(days=1))
            else:
                daylight_savings_times.append(pot_date.date())
    
    return daylight_savings_times

def chanukkah(date, church, country, obseverd, eve):
    return hanukkah(date, church, country, obseverd, eve)

def hanukkah(date, church, country, obseverd, eve):
    year, month, day = hebrew.to_jd_gregorianyear(year, hebrew.KISLEV, 25)
    if not obseverd:
        day -= 1
    start_date = datetime.date(year, month, day)
    if not obseverd:
        end_date = start_date + datetime.timedelta(days=8)
    else:
        end_date = start_date + datetime.timedelta(days=7)
return [start_date + datetime.timedelta(days=x) for x in range((end_date - start_date).days + 1)]