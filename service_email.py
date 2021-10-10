import smtplib
import base64
from email.mime.text import MIMEText
import os
import getopt
import sys

def main():
    """The main function."""

    valid_services = ["MLB", "MLB_DELETER", "NFL", "NFL_DELETER", "NHL", "NHL_DELETER", "NBA", "NBA_DELETER"]

    service_start = "start"
    service_stop = "stop"
    service_arg = "service"
    try:
        options = getopt.getopt(sys.argv[1:], None, [service_start, service_stop, service_arg + "="])[0]
    except getopt.GetoptError as err:
        raise Exception("Encountered error \"" + str(err) + "\" parsing arguments")
        return

    is_start = None
    service = None

    for opt, arg in options:
        if opt == "--" + service_start:
            is_start = True
        elif opt == "--" + service_stop:
            is_start = False
        elif opt == "--" + service_arg:
            service = arg.strip().upper()

    if is_start == None:
        raise Exception("Must provide either stop or start argument")
    if not service:
        raise Exception("Must provide either service argument")
    if service not in valid_services:
        raise Exception(service + " is not a valid service (" + str(valid_services) + ")")

    sender = "sportscomparebots@gmail.com"
    encoded_password = b"QUVJb3UxMjMh\n"
    recipients = ["sportscomparebots@gmail.com"]

    msg = MIMEText("The " + service + " service up yo :)") if is_start else MIMEText("The " + service + " service down yo :(")
    msg["Subject"] = service + " Service Up" if is_start else service + " Service Down"
    msg["From"] = sender
    msg["To"] = ','.join(recipients)

    smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465)

    try:
        smtp.ehlo()
        smtp.login(sender, base64.decodebytes(encoded_password).decode("UTF-8"))
        smtp.sendmail(sender, recipients, msg.as_string())
    finally:
        smtp.close()

    print("EMAIL SENT FOR " + service + " SERVICE START") if is_start else print("EMAIL SENT FOR " + service + " SERVICE STOP")

if __name__ == "__main__":
    main()
