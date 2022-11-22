import praw
from praw.models import Message
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import threading
import getopt
import traceback
import time
import nhl
import math
import re
import ssl
from requests_ip_rotator import ApiGateway

logname = "nhl_comment_deleter.log"
logger = logging.getLogger("nhl_comment_deleter")
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler = TimedRotatingFileHandler(logname, when="midnight", interval=1)
handler.suffix = "%Y%m%d"
handler.setFormatter(formatter)
logger.addHandler(handler)
streamhandler = logging.StreamHandler(sys.stdout)
streamhandler.setLevel(logging.DEBUG)
logger.addHandler(streamhandler)

comment_editor_map = set()
lock = threading.Lock()

ssl._create_default_https_context = ssl._create_unverified_context

def main():
    """The main function."""


    manual_message_short = "m"
    manual_messagage_long = "message"
    debug_subject_short = "s"
    debug_subject_long = "subject"
    debug_body_short = "b"
    debug_body_long = "body"
    debug_author_short = "a"
    debug_author_long = "author"
    try:
        options = getopt.getopt(sys.argv[1:], manual_message_short + ":" + debug_subject_short + ":" + debug_body_short + ":" + debug_author_short + ":", [manual_messagage_long + "=", debug_subject_long + "=", debug_body_long + "=", debug_author_long + "="])[0]
    except getopt.GetoptError as err:
        logger.error("Encountered error \"" + str(err) + "\" parsing arguments")
        return

    conn = sqlite3.connect("nhl.db")
    try:
        with conn:
            curr = conn.cursor()

            curr.execute("SELECT COUNT(*) FROM sqlite_master WHERE type=\"table\" AND name=\"nhl_messages\";")
            
            numtables = int(curr.fetchone()[0])

            if not numtables:
                logger.info("nhl_messages table missing. Creating...")
                curr.execute("CREATE TABLE nhl_messages (message_id TEXT PRIMARY KEY, message_author TEXT NOT NULL, was_successful BOOLEAN NOT NULL CHECK (was_successful IN (0,1)), timestamp INTEGER NOT NULL);")
                curr.execute("SELECT COUNT(*) FROM sqlite_master WHERE type=\"table\" AND name=\"nhl_messages\";")
                numtables = int(curr.fetchone()[0])
                if numtables:
                    logger.info("nhl_messages table created!")
                else:
                    raise Exception("Error creating table!")

            curr.execute("SELECT COUNT(*) FROM sqlite_master WHERE type=\"table\" AND name=\"nhl_reruns\";")
            
            numtables = int(curr.fetchone()[0])

            if not numtables:
                logger.info("nhl_reruns table missing. Creating...")
                curr.execute("CREATE TABLE nhl_reruns (message_id TEXT PRIMARY KEY, message_author TEXT NOT NULL, was_successful BOOLEAN NOT NULL CHECK (was_successful IN (0,1)), timestamp INTEGER NOT NULL);")
                curr.execute("SELECT COUNT(*) FROM sqlite_master WHERE type=\"table\" AND name=\"nhl_reruns\";")
                numtables = int(curr.fetchone()[0])
                if numtables:
                    logger.info("nhl_reruns table created!")
                else:
                    raise Exception("Error creating table!")
    finally:
        conn.close()

    reddit = praw.Reddit("nhlcomparebot")
    
    manual_message = None
    debug_subject = None
    debug_body = None
    debug_author = None
    for opt, arg in options:
        if opt in ("-" + manual_message_short, "--" + manual_messagage_long):
            manual_message = arg.strip()
        if opt in ("-" + debug_subject_short, "--" + debug_subject_long):
            debug_subject = arg.strip()
        elif opt in ("-" + debug_body_short, "--" + debug_body_long):
            debug_body = arg.strip()
        elif opt in ("-" + debug_author_short, "--" + debug_author_long):
            debug_author = arg.strip()

    global gateway
        with ApiGateway("https://www.hockey-reference.com", verbose=False) as gateway:
        if manual_message:
            message = reddit.inbox.message(manual_message)
            if message.author and not message.author.name.lower() in nhl.blocked_users:
                if message.subject.strip().lower() == "delete":
                    logger.info("FOUND DELETE MESSAGE " + str(message.id))
                    parse_message(message, reddit)
                elif message.subject.strip().lower() == "re-run" or message.subject.strip().lower() == "rerun":
                    logger.info("FOUND RE-RUN MESSAGE " + str(message.id))
                    re_run_message(message, reddit, True)
                elif re.search(r"!\bnhlcompare(?:bot)?\b", message.body, re.IGNORECASE):
                    logger.info("FOUND COMPARE MESSAGE " + str(message.id))
                    nhl.parse_input(message, True, False)
            return
        elif debug_subject and debug_body and debug_author:
            message = FakeMessage(debug_subject, debug_body, "-1", debug_author)
            if message.subject.strip().lower() == "delete":
                logger.info("FOUND DELETE MESSAGE " + str(message.id))
                parse_message(message, reddit)
            elif message.subject.strip().lower() == "re-run" or message.subject.strip().lower() == "rerun":
                logger.info("FOUND RE-RUN MESSAGE " + str(message.id))
                re_run_message(message, reddit, True)
            elif re.search(r"!\bnhlcompare(?:bot)?\b", message.body, re.IGNORECASE):
                logger.info("FOUND COMPARE MESSAGE " + str(message.id))
                nhl.parse_input(message, True, False)
            return

        with ThreadPoolExecutor(max_workers=5) as executor:
            for message in reddit.inbox.stream():
                if isinstance(message, Message):
                    if message.author and not message.author.name.lower() in nhl.blocked_users:
                        if message.subject.strip().lower() == "delete":
                            logger.info("FOUND DELETE MESSAGE " + str(message.id))
                            executor.submit(parse_message, message, reddit)
                        elif message.subject.strip().lower() == "re-run" or message.subject.strip().lower() == "rerun":
                            logger.info("FOUND RE-RUN MESSAGE " + str(message.id))
                            executor.submit(re_run_message, message, reddit, False)
                        elif re.search(r"!\bnhlcompare(?:bot)?\b", message.body, re.IGNORECASE):
                            logger.info("FOUND COMPARE MESSAGE " + str(message.id))
                            executor.submit(nhl.parse_input, message, False, False)

def parse_message(message, reddit):
    """Parses a message"""

    conn = sqlite3.connect("nhl.db")
    try:
        with conn:
            curr = conn.cursor()
            curr.execute("SELECT 1 FROM nhl_messages WHERE message_id = ?;", (message.id, ))
            if not curr.fetchone():
                reddit_message = None
                was_successful = 0
                try:
                    comment_id = message.body.strip().lower()
                    if not comment_id:
                        raise CustomMessageException("Comment ID to delete must be the body of the message!")
                    curr.execute("SELECT reply_comment_id, reply_author, subreddit FROM nhl WHERE was_deleted = 0 AND reply_id = ?;", (comment_id, ))
                    
                    rows = curr.fetchone()
                    if not rows:
                        raise CustomMessageException(comment_id + " is not an existing comment/message!")

                    reply_comment_id = rows[0]
                    reply_author = rows[1]
                    is_message = rows[2] == "from_message"

                    if not reply_comment_id or not reply_author:
                         raise CustomMessageException(comment_id + " is not an existing comment/message!")

                    if message.author.name != "Sweetpotatonvenison" and reply_author != message.author.name:
                        if is_message:
                            raise CustomMessageException("You were not the summoner of message " + comment_id + "!")
                        else:
                            raise CustomMessageException("You were not the summoner of comment " + comment_id + "!")

                    failed_counter = 0
                    while(True):
                        try:
                            curr.execute("UPDATE nhl SET was_deleted = 1 WHERE reply_id = ?;", (comment_id, ))
                            break
                        except Exception:
                            failed_counter += 1
                            if failed_counter > nhl.max_request_retries:
                                raise

                        delay_step = 10
                        logger.info("#" + str(threading.get_ident()) + "#   " + "Retrying in " + str(nhl.retry_failure_delay) + " seconds to allow db to chill")
                        time_to_wait = int(math.ceil(float(nhl.retry_failure_delay)/float(delay_step)))
                        for i in range(nhl.retry_failure_delay, 0, -time_to_wait):
                            logger.info("#" + str(threading.get_ident()) + "#   " + str(i))
                            time.sleep(time_to_wait)
                        logger.info("#" + str(threading.get_ident()) + "#   " + "0")

                    if is_message:
                        reply_message = reddit.inbox.message(reply_comment_id)
                        try:
                            reply_message.delete()
                        except praw.exceptions.APIException as e:
                            raise CustomMessageException(comment_id + " is not an existing message!")
                        reddit_message = "Message " + comment_id + " succesfully deleted!"
                    else:
                        comment = reddit.comment(id=reply_comment_id)
                        try:
                            comment.delete() 
                        except praw.exceptions.APIException as e:
                            raise CustomMessageException("Comment " + comment_id + " is not an existing comment!")
                        reddit_message = "Comment " + comment_id + " succesfully deleted!"

                    was_successful = 1
                except CustomMessageException as e:
                    reddit_message = "Oh no, I had a problem with your request: " + e.message
                    logger.error("#" + str(threading.get_ident()) + "#   " + traceback.format_exc())
                except BaseException as e:
                    reddit_message = "Oh no, I had a problem with your request"
                    logger.error("#" + str(threading.get_ident()) + "#   " + traceback.format_exc())
                
                try:
                    message.reply(reddit_message)
                    logger.info("#" + str(threading.get_ident()) + "#   " + "MESSAGE: " + reddit_message)
                except praw.exceptions.APIException as e:
                    logger.error("#" + str(threading.get_ident()) + "#   " + traceback.format_exc())

                failed_counter = 0
                while(True):
                    try:
                        curr.execute("INSERT INTO nhl_messages VALUES (?,?,?,?);", (message.id, message.author.name, was_successful, round(time.time() * 1000)))
                        break
                    except Exception:
                        failed_counter += 1
                        if failed_counter > nhl.max_request_retries:
                            raise

                    delay_step = 10
                    logger.info("#" + str(threading.get_ident()) + "#   " + "Retrying in " + str(nhl.retry_failure_delay) + " seconds to allow db to chill")
                    time_to_wait = int(math.ceil(float(nhl.retry_failure_delay)/float(delay_step)))
                    for i in range(nhl.retry_failure_delay, 0, -time_to_wait):
                        logger.info("#" + str(threading.get_ident()) + "#   " + str(i))
                        time.sleep(time_to_wait)
                    logger.info("#" + str(threading.get_ident()) + "#   " + "0")                
            else:
                logger.info("#" + str(threading.get_ident()) + "#   " + "SKIP: " +  message.id)
    finally:
        conn.close()

def re_run_message(message, reddit, debug_mode):
    """Re-runs a comparison"""

    conn = sqlite3.connect("nhl.db")
    try:
        with conn:
            curr = conn.cursor()
            curr.execute("SELECT 1 FROM nhl_reruns WHERE message_id = ?;", (message.id, ))
            if not curr.fetchone():
                reddit_message = None
                was_successful = 0
                comment_id = message.body.strip().lower()
                if not comment_id:
                    raise CustomMessageException("Comment ID to delete must be the body of the message!")
                
                try:
                    with lock:
                        if comment_id in comment_editor_map:
                            raise CustomMessageException("A re-run is already running for comment " + comment_id + "!")
                        comment_editor_map.add(comment_id)
                        
                    try:
                        curr.execute("SELECT reply_comment_id, reply_author, subreddit, original_comment, was_successful FROM nhl WHERE was_deleted = 0 AND reply_id = ?;", (comment_id, ))
                        
                        rows = curr.fetchone()
                        if rows:
                            was_successful = parse_comment(reddit, comment_id, rows[0], rows[3], rows[4], message, debug_mode, curr)
                        else:
                            was_successful = parse_comment(reddit, comment_id, None, None, False, message, debug_mode, curr)
                    finally:
                        with lock:
                            comment_editor_map.remove(comment_id)
                except CustomMessageException as e:
                    reddit_message = "Oh no, I had a problem with your request: " + e.message
                    logger.error("#" + str(threading.get_ident()) + "#   " + traceback.format_exc())
                except BaseException as e:
                    reddit_message = "Oh no, I had a problem with your request"
                    logger.error("#" + str(threading.get_ident()) + "#   " + traceback.format_exc())
                
                if reddit_message:
                    try:
                        message.reply(reddit_message)
                        logger.info("#" + str(threading.get_ident()) + "#   " + "MESSAGE: " + reddit_message)
                    except praw.exceptions.APIException as e:
                        logger.error("#" + str(threading.get_ident()) + "#   " + traceback.format_exc())

                failed_counter = 0
                while(True):
                    try:
                        curr.execute("INSERT INTO nhl_reruns VALUES (?,?,?,?);", (message.id, message.author.name, was_successful, round(time.time() * 1000)))
                        break
                    except Exception:
                        failed_counter += 1
                        if failed_counter > nhl.max_request_retries:
                            raise

                    delay_step = 10
                    logger.info("#" + str(threading.get_ident()) + "#   " + "Retrying in " + str(nhl.retry_failure_delay) + " seconds to allow db to chill")
                    time_to_wait = int(math.ceil(float(nhl.retry_failure_delay)/float(delay_step)))
                    for i in range(nhl.retry_failure_delay, 0, -time_to_wait):
                        logger.info("#" + str(threading.get_ident()) + "#   " + str(i))
                        time.sleep(time_to_wait)
                    logger.info("#" + str(threading.get_ident()) + "#   " + "0")
            else:
                logger.info("#" + str(threading.get_ident()) + "#   " + "SKIP: " +  message.id)
    finally:
        conn.close()
    
def parse_comment(reddit, comment_id, reply_comment_id, original_comment, is_existing_comment, message, debug_mode, curr):
    was_successful = 0
    comment = reddit.comment(id=comment_id)
    is_message = False
    if not comment:
        is_message = True
        comment = reddit.inbox.message(comment_id)
    
    if not comment:
        raise CustomMessageException(comment_id + " is not an existing comment or message!")

    if message.author.name != "Sweetpotatonvenison" and comment.author.name != message.author.name:
        if is_message:
            raise CustomMessageException("You were not the summoner of message " + comment_id + "!")
        else:
            raise CustomMessageException("You were not the summoner of comment " + comment_id + "!")

    if is_message:
        message = reddit.inbox.message(comment_id)
        if re.search(r"!\bnhlcompare(?:bot)?\b", message.body, re.IGNORECASE):
            logger.info("#" + str(threading.get_ident()) + "#   " + "Starting re-run")
            try:
                message.reply("Starting re-run!")
                logger.info("#" + str(threading.get_ident()) + "#   " + "MESSAGE: " + "Starting re-run!")
            except praw.exceptions.APIException as e:
                logger.error("#" + str(threading.get_ident()) + "#   " + traceback.format_exc())
            nhl.parse_input(message, debug_mode, False, curr)
            was_successful = 1
        else:
            raise CustomMessageException("Message " + comment_id + " does not contain a comparison!")
    else:
        comment = reddit.comment(id=comment_id)
        if not comment.archived:
            if re.search(r"!\bnhlcompare(?:bot)?\b", comment.body, re.IGNORECASE):
                comment_obj = None
                if reply_comment_id:
                    delete_comment = reddit.comment(id=reply_comment_id)
                    if delete_comment:
                        if delete_comment.archived:
                            try:
                                delete_comment.delete() 
                            except praw.exceptions.APIException as e:
                                logger.info("#" + str(threading.get_ident()) + "#   Exception deleting comment " + str(e))
                                pass
                        else:
                            comment_obj = delete_comment

                logger.info("#" + str(threading.get_ident()) + "#   " + "Starting re-run")
                try:
                    message.reply("Starting re-run!")
                    logger.info("#" + str(threading.get_ident()) + "#   " + "MESSAGE: " + "Starting re-run!")
                except praw.exceptions.APIException as e:
                    logger.error("#" + str(threading.get_ident()) + "#   " + traceback.format_exc())
                nhl.parse_input(comment, debug_mode, comment.subreddit.display_name in nhl.approved_subreddits, curr, comment_obj)
                was_successful = 1
            else:
                raise CustomMessageException("Comment " + comment_id + " does not contain a comparison!")
        else:
            raise CustomMessageException("Comment " + comment_id + " archived and can no longer be replied to!")
    
    return was_successful

class CustomMessageException(Exception):
    message = None
    def __init__(self, message):
        super().__init__(message)
        self.message = message

class FakeMessage(object):
    def __init__(self, subject, body, id, author):
        self.subject = subject
        self.body = body
        self.id = id
        self.author = FakeAuthor(author)

class FakeAuthor(object):
    def __init__(self, name):
        self.name = name

if __name__ == "__main__":
    main()