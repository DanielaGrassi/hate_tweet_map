import logging
import os
from datetime import time
import time
from json import dumps

import pandas
import yaml

from hate_tweet_map.database import DataBase


def main():

    """
    Using this script is possible:
        - extract some tweets from the database and save it on .json or .csv file
        - delete some tweets
    The criteria to select the tweets to extract/delete are defined in the manage_tweets.config file.
    Is possible modify that file to set the criteria.
    The possible criteria are:
        - contains some specific word/words. In this case it is possible or write a list of words separated by comma in the words field, or use a txt file and write it path in the path field.
        - contains a specific sentiment
        - contains a word with a specific Part Of Speech (POS)
        - raw criteria: a query written in mongodb style
    These criteria and the words specified in the relative field/file are connected with the "OR" logical operator
    or with the "AND" logical operator. It is possible specify which operator must be used setting the logical_operator field in the config file.

    :return: None
    """
    global db, query
    start = time.time()
    logging.basicConfig()

    with open("../../script/manage_tweets/manage_tweets.config", "r") as ymlfile:
        # load the configuration from the config file
        cfg = yaml.safe_load(ymlfile)
        mode = cfg['mode']
        _format = cfg['format']
        sentiment = cfg['criteria']['sentiment']
        keywords_path = cfg['criteria']['keywords']['path']
        keywords_words = cfg['criteria']['keywords']['words']
        _words = []
        logical_operator = cfg['criteria']['logical_operator']
        postag = cfg['criteria']['postag']
        morph = cfg['criteria']['morph']
        raw_query = cfg['criteria']['raw_query']

    # validate the config file
    if sentiment is None and keywords_words and None and postag is None and raw_query is None:
        raise ValueError("Please specify at least one value for the criteria field")

    if keywords_path is None and keywords_words is None:
        raise ValueError("It's not possible set the words and the path for the keywords field .")
    # if the path of the keyword file is set
    if keywords_path:
        # open, read and save in a list the words
        with open(keywords_path, "r") as f:
            _words = f.readlines()
    # if the path of the keyword file is not set but there some words set in the file config
    elif keywords_words:
         # read the words, splitting these, and save them in a list.
        _words = keywords_words.split(",")
    # validate the config file
    if mode != "extract" and mode != "delete":
        raise ValueError("The only possible modes are: extract, delete")
    # ir the mode is extract the format field must be set
    if mode == "extract":
        if _format is None:
            raise ValueError("If you want extract the tweets please specify the format. The possible formats are: "
                             "json, csv")
        elif _format != "json" and _format != "csv":
            raise ValueError("The only possible formats are: csv, json")

    log = logging.getLogger("MANAGE")
    log.setLevel(logging.INFO)

    # connect to the databse
    db = DataBase('../../script/manage_tweets/manage_tweets.config')
    values = []
    # set the logical operator that must be used to connect the fields
    if logical_operator == "and":
        query = {"$and": values}
    else:
        query = {"$or": values}
    # if the sentiment field is set
    if sentiment:
        # adds the query to search the tweets where the field sentiment of sent-it or the field sentiment of feel-it is
        # equal to the value inserted in the sentiment field of the config ile
        values.append({"$or": [{'sentiment.sent-it.sentiment': sentiment}, {'sentiment.feel-it.sentiment': sentiment}]})
    # if there a words to check
    if _words:
        # append each words to the query that check if that word are in the lemma returned by the spacy analysis.
        for k in _words:
            # spacy.processed_text is an array of string, each string contain a token normalized and the pos information
            # so to check if the tweet contains the word given we use a regex.
            values.append({"spacy.processed_text": {"$regex": ".*{}.*".format(k.strip()), "$options": "i"}})
    if raw_query:
        # adds a raw query if setted
        values.append(raw_query)
    # if a postag is set
    if postag and morph and logical_operator == "and":
        values.append({"spacy.processed_text": {"$regex": ".* POS : {} ; MORPH : .*{}.*".format(postag.strip(), morph.strip()), "$options": "i"}})
    # se non sono settati entrambi o se sono settati entrambi e sono in or
    else:
        if postag:
            # check if after the string " POS :" there is the value given using the regex.
            values.append({"spacy.processed_text": {"$regex": ".* POS : {}.*".format(postag.strip()), "$options": "i"}})
        if morph:
            values.append({"spacy.processed_text": {"$regex": ".* MORPH : {}.*".format(morph.strip()), "$options": "i"}})

    # if the mode is delete
    if mode == 'delete':
        log.info("MODE: DELETE")
        # if a query exist
        if query:
            # delete all tweets that match the query
            deleted = db.delete_more(query)
            log.info("DELETED: {} TWEETS".format(deleted))
        else:
            log.info("NO TWEETS TO DELETE")
    # else if the mode is extract
    elif mode == 'extract':
        log.info("MODE: EXTRACT")
        # search the tweets that match the query
        result = db.extract(query)
        log.info("TWEETS RETRIEVED: {}".format(len(result)))
        # if the format is json
        if _format == "json":
            # write the data on a json file
            with open('../../data.json', 'w') as file:
                file.write(dumps(result, indent=2))
                log.info("TWEETS SAVED ON: {}".format(os.path.abspath('../../data.json')))
        # if the format is csv
        elif _format == "csv":
            # create a dump of the data in csv using panda module
            df = pandas.DataFrame(db.extract(query))
            df.to_csv('data.csv', index=False)
            log.info("TWEETS SAVED ON: {}".format(os.path.abspath('../../data.csv')))

    end = time.time()
    log.info("DONE IN: {}".format(end - start))


if __name__ == "__main__":
    main()
