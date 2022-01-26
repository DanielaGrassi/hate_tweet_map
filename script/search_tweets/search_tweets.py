import logging
from datetime import datetime
from hate_tweet_map.tweets_searcher.SearchTweets import SearchTweets

import time
import sys


def main():

    logging.basicConfig()
    log = logging.getLogger("SEARCH")
    log.setLevel(logging.INFO)
    start = time.time()
    log.info(datetime.fromtimestamp(start))

    log.info("LOADING CONFIGURATION")
    twitter_search = SearchTweets(path_to_cnfg_file='../../script/search_tweets/search_tweets.config')

    log.info("SEARCH FOR TWEETS")
    n_tweets = twitter_search.search()

    print("\n")
    log.info("TWEETS FOUND AND SAVED SUCCESSFULLY: {}".format(n_tweets))

    end = time.time()
    log.info("DONE IN: {}".format(end - start))


if __name__ == "__main__":
    main()
