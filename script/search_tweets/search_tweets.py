import logging
import os
from datetime import datetime
import re, string
from hate_tweet_map.database import DataBase
from hate_tweet_map.tweets_searcher.SearchTweets import SearchTweets

import time
import sys


def main():

    logging.basicConfig()
    log = logging.getLogger("SEARCH")
    log.setLevel(logging.INFO)
    start = time.time()
    log.info(datetime.fromtimestamp(start))

    mongo_db = DataBase("search_tweets.config")
    log.info("LOADING CONFIGURATION")
    twitter_search = SearchTweets(mongodb=mongo_db, path_to_cnfg_file='search_tweets.config')

    log.info("SEARCH FOR TWEETS")
    n_tweets = twitter_search.search()

    print("\n")
    log.info("TWEETS FOUND AND SAVED SUCCESSFULLY: {}".format(n_tweets))

    end = time.time()
    log.info("DONE IN: {}".format(end - start))


if __name__ == "__main__":
    main()
