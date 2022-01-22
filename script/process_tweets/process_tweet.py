import logging

from hate_tweet_map.tweets_processor.TweetProcessor import ProcessTweet


def main():
    logging.info("CONFIGURING...")
    p = ProcessTweet("../../script/process_tweets/process_tweets.config")
    p.start()


if __name__ == "__main__":
    main()