import concurrent
from concurrent import futures
import logging
import math
import time
import pandas as pd
from concurrent.futures import Future, as_completed
from datetime import datetime, timezone
import requests
import yaml
from tqdm import tqdm
import re

from hate_tweet_map import util
from hate_tweet_map.database import DataBase


class SearchTweets:
    """

    """

    def __init__(self, path_to_cnfg_file: str) -> None:
        """
        This method load the paramaters of the serch from the configuration file, validate these and initialize the value of the class attribute.

        :param path_to_cnfg_file:
        :type path_to_cnfg_file:
        :param mongodb: the database instance where save the result of the search
        :type mongodb: DataBase
        """

        self._all = []
        self.total_result = 0
        self.__multi_user = False
        self.__twitter_users = []

        self.log = logging.getLogger("SEARCH")
        self.log.setLevel(logging.INFO)
        logging.basicConfig()
        self.response = {}
        # load the comfiguration file, save the parameters and validate it
        with open(path_to_cnfg_file, "r") as ymlfile:
            cfg = yaml.safe_load(ymlfile)
            check = []
            self.__twitter_keyword = cfg['twitter']['search']['keyword']
            twitter_user = cfg['twitter']['search']['user']

            if not (self.__twitter_keyword or twitter_user):
                raise ValueError(
                    'Impostare un valore per almeno uno dei due perametri [user], [keyword]')
            if twitter_user:
                if "," in str(twitter_user):
                    self.__twitter_users = twitter_user.split(",")
                    self.__multi_user = True
                else:
                    self.__twitter_users = [twitter_user]

            self.__twitter_lang = cfg['twitter']['search']['lang']
            self.__twitter_place_country = cfg['twitter']['search']["geo"]['place_country']
            self.__twitter_place = cfg['twitter']['search']["geo"]['place']
            self.__twitter_bounding_box = cfg['twitter']['search']["geo"]['bounding_box']
            self.__twitter_point_radius_longitude = cfg['twitter']['search']["geo"]['point_radius']['longitude']
            self.__twitter_point_radius_latitude = cfg['twitter']['search']["geo"]['point_radius']['latitude']
            self.__twitter_point_radius_radius = cfg['twitter']['search']["geo"]['point_radius']['radius']
            self.__twitter_start_time = cfg['twitter']['search']['time']['start_time']
            self.__twitter_end_time = cfg['twitter']['search']['time']['end_time']

            if self.__twitter_point_radius_longitude:
                check.append(True)
            if self.__twitter_point_radius_radius:
                check.append(True)
            if self.__twitter_point_radius_latitude:
                check.append(True)

            if 1 < check.count(True) < 3:
                raise ValueError(
                    'To search using [point_radius] all the following parameters must be set: [latitude], [radius] e [longitude]')

            check = []

            if self.__twitter_place:
                check.append(True)
            if self.__twitter_place_country:
                check.append(True)
            if self.__twitter_bounding_box:
                check.append(True)
            if self.__twitter_point_radius_longitude:
                check.append(True)

            if check.count(True) > 1:
                raise ValueError(
                    'Only one of the following paramaters must be set [bounding_box], [point_radius]')

            self.__twitter_context_annotations = cfg['twitter']['search']['context_annotations']
            self.__twitter_all_tweets = cfg['twitter']['search']['all_tweets']
            self.__twitter_n_results = cfg['twitter']['search']['n_results']
            self.__twitter_filter_retweet = cfg['twitter']['search']['filter_retweet']
            self.__twitter_barer_token = cfg['twitter']['configuration']['barer_token']
            self.__twitter_end_point = cfg['twitter']['configuration']['end_point']

        self.__headers = {"Authorization": "Bearer {}".format(self.__twitter_barer_token)}

    def __next_page(self, next_token="") -> None:
        """
        Insert in the query the token to obtain the next page of the tesult of the search.

        :param next_token: the token obtained from twitter to reach the next page of the search
        :type next_token: str, optional
        :return: None
        """
        if next_token != "":
            self.__query["next_token"] = next_token

    def __build_query(self, user: str = None) -> None:
        """
        This method build the query to send to twitter

        :param user: the id or name of the user whose tweets you want, defaults to None
        :type user: str, optional
        :return: None
        """
        # Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
        # expansions,tweet.fields,media.fields,poll.fields,place.fields,user.fields
        self.__query = {'query': ""}

        if self.__twitter_keyword:
            self.__query['query'] = str(self.__twitter_keyword)
        if user is not None:
            if self.__twitter_keyword:
                self.__query['query'] += " from: " + str(user)
            else:
                self.__query['query'] += "from: " + str(user)

        if self.__twitter_lang:
            self.__query['query'] += " lang:" + self.__twitter_lang
        if self.__twitter_place:
            self.__query['query'] += " place:" + self.__twitter_place
        if self.__twitter_place_country:
            self.__query['query'] += " place_country:" + self.__twitter_place_country
        if self.__twitter_all_tweets:
            if self.__twitter_context_annotations:
                self.__query['max_results'] = str(100)
            else:
                self.__query['max_results'] = str(500)

        # if is specified a number of result to request
        elif self.__twitter_n_results:
            # if the specified number is greater than 500 set the max_result query field to the max value possible so
            # 500.
            if self.__twitter_context_annotations:
                if self.__twitter_n_results > 100:
                    self.__query['max_results'] = str(100)
            elif self.__twitter_n_results > 500:
                self.__query['max_results'] = str(500)
            # if the specified number is less than 10 set the max_result field to the min value possible so 10
            elif self.__twitter_n_results < 10:
                self.__query['max_results'] = str(10)
            # else if the value is between 10 and 500 set the max_result field query to the value given
            else:
                self.__query['max_results'] = str(self.__twitter_n_results)

        if self.__twitter_bounding_box:
            self.__query['query'] += " bounding_box:" + "[" + self.__twitter_bounding_box + "]"
        elif self.__twitter_point_radius_longitude:
            self.__query['query'] += " point_radius:" + "[" + str(self.__twitter_point_radius_longitude) + " " + str(
                self.__twitter_point_radius_latitude) + " " + self.__twitter_point_radius_radius + "]"
        if self.__twitter_filter_retweet is True:
            self.__query['query'] += " -is:retweet"
        self.__query['place.fields'] = "contained_within,country,country_code,full_name,geo,id,name,place_type"
        self.__query['expansions'] = 'author_id,geo.place_id,referenced_tweets.id'
        self.__query['tweet.fields'] = 'lang,referenced_tweets,public_metrics,entities,created_at,possibly_sensitive'
        self.__query['user.fields'] = 'username,location'

        if self.__twitter_context_annotations:
            self.__query['tweet.fields'] += ',context_annotations'
        if self.__twitter_start_time:
            self.__query['start_time'] = str(self.__twitter_start_time)
        if self.__twitter_end_time:
            self.__query['end_time'] = str(self.__twitter_end_time)

    @property
    def twitter_lang(self):
        return self.__twitter_lang

    @property
    def twitter_place_country(self):
        return self.__twitter_place_country

    @property
    def twitter_point_radius_radius(self):
        return self.__twitter_point_radius_radius

    @property
    def twitter_point_radius_longitude(self):
        return self.__twitter_point_radius_longitude

    @property
    def twitter_point_radius_latitude(self):
        return self.__twitter_point_radius_latitude

    @property
    def twitter_place(self):
        return self.__twitter_place

    @property
    def twitter_start_time(self):
        return self.__twitter_start_time

    @property
    def twitter_end_time(self):
        return self.__twitter_end_time

    @property
    def twitter_bounding_box(self):
        return self.__twitter_bounding_box

    @property
    def twitter_context_annotation(self):
        return self.__twitter_context_annotations

    @property
    def twitter_n_results(self):
        return self.__twitter_n_results

    @property
    def twitter_all_results(self):
        return self.__twitter_all_tweets

    @property
    def twitter_end_point(self):
        return self.__twitter_end_point

    @property
    def twitter_key_word(self):
        return self.__twitter_keyword

    @property
    def twitter_user(self):
        return self.__twitter_users

    @property
    def twitter_filter_retweet(self):
        return self.__twitter_filter_retweet

    def __connect_to_endpoint(self, retried: bool = False) -> dict:
        """
        This method sends the request to twitter and return the response.
        The possibles status codes in the twitter response are:
            - 200: ok,in this case the response is a valid response;
            - 429: rate limit exceeded, this means that either more requests were sent per second than allowed or more requests were sent in 15min than allowed. so in this case this method waits 1 second and tries to send the request again,  if twitter still replies with a 429 code, it retrieves from the reply the time when the limit will reset and wait for that time to resubmit the request;
            - 503: service overloaded, this means that twitter can't response to our requesst because there too many request to process. In this case this method wait for a minute and then retry to send the request.
            - others: in this case the method raises an exception

        :param retried: a parameter that indicate if it is the first retry after an error or not, defaults to False
        :type retried: bool, optional
        :raise Exception: when twitter response with not 200 or 429 status code.
        :return: dict that contains the response from twitter
        :rtype: dict
        """
        # send the request to twitter, save the response, check if it's ok and if is return the response in json format
        response = requests.request("GET", self.__twitter_end_point, headers=self.__headers, params=self.__query)
        if response.status_code == 200:
            t = response.headers.get('date')
            self.log.debug("RECEIVED VALID RESPONSE")
            return response.json()
        # if the response status code is 429 and the value of retried is False wait for 1 second and retry to send the request
        if response.status_code == 429 and not retried:
            self.log.debug("RETRY")
            time.sleep(1)
            return self.__connect_to_endpoint(retried=True)
        # if the response status code is 429 and the retried value is True it means it is at least the second attempt in a row after receiving a 429 error
        elif response.status_code == 429 and retried:
            self.log.warning("RATE LIMITS REACHED: WAITING")
            # save the current time
            now = time.time()
            # transform it in utc format
            now_date = datetime.fromtimestamp(now, timezone.utc)
            # retrieve the time when the rate limit will be reset
            reset = float(response.headers.get("x-rate-limit-reset"))
            # transform it in utc format
            reset_date = datetime.fromtimestamp(reset, timezone.utc)
            # obatain the second to wait for reset the rate limit
            sec_to_reset = (reset_date - now_date).total_seconds()
            # print a bar to show the time passing
            for i in tqdm(range(0, math.floor(sec_to_reset) + 1), desc="WAITING FOR (in sec)", leave=True, position=0):
                time.sleep(1)
            return self.__connect_to_endpoint(retried=True)
        # if the response is 503 twitter is overloaded, in this case wait for a minute and retry to send the request.
        elif response.status_code == 503:
            self.log.warning(
                "GET BAD RESPONSE FROM TWITTER: {}: {}. THE SERVICE IS OVERLOADED.".format(response.status_code,
                                                                                           response.text))
            self.log.warning("WAITING FOR 1 MINUTE BEFORE RESEND THE REQUEST")
            for i in tqdm(range(0, 60), desc="WAITING FOR (in sec)", leave=True):
                time.sleep(1)
            self.log.warning("RESENDING THE REQUEST")
            return self.__connect_to_endpoint()
        # else, fot all the other status code, raises an exception
        else:
            self.log.critical("GET BAD RESPONSE FROM TWITTER: {}: {}".format(response.status_code, response.text))
            raise Exception(response.status_code, response.text)

    def __make(self, bar) -> None:
        """
        This method sends the request to twitter, elaborates it and saves the response.
        After the first search the number of tweets contained in the response are checked,
        if this number is equal to the number of result wanted set in the config file the method stop to send request.
        If this number is less than the number of result wanted set in the config file, the difference between the two number are
        done and a new request with this number as max_result query field are send, so this method a called with
        result_obtained_yet parameter updated. Note that if the difference between the number of tweets obtained and the
        number of tweets wanted is greater than 500 the max_result query field for the next request is set to 500 instead
        if is less than 10 the max_result query field for the next request is set to 10.
        Moreover if the all_tweets parameters is set to True on the file config this method resend the request to twitter
        asking for 500 tweets per time (max_result = 500) until the end of the result is not reached.

        :param bar:
        :type bar:
        :return: None
        """
        # call the method to send the request to twitter
        result_obtained_yet = 0
        self.response = self.__connect_to_endpoint()
        # while there are tweets in the response
        while "meta" in self.response:
            self.log.debug("RECEIVED: {} TWEETS".format(self.response['meta']['result_count']))
            # save the tweets received
            # save_bar = tqdm(desc="Saving", leave=False, position=1)
            self.__save()
            # update the value of the total result obtained
            self.total_result += self.response['meta']['result_count']
            bar.update(self.response['meta']['result_count'])
            # check if there is another page fot the research performed
            if "next_token" in self.response['meta']:
                # if there is a next page and all_tweets are set to True to reach all tweets
                if self.__twitter_all_tweets:
                    self.log.debug("ASKING FOR NEXT PAGE")
                    # set the max_results query field to 500.
                    if self.__twitter_context_annotations:
                        self.__query['max_results'] = str(100)
                    else:
                        self.__query['max_results'] = str(500)
                # else if the all_tweets is False but is set a specific number of results to reach
                elif self.__twitter_n_results:
                    # update the value of the number of tweets obtained yet
                    result_obtained_yet += int(self.response['meta']['result_count'])
                    # calculate how many tweets is necessary to ask
                    results_to_request = self.__twitter_n_results - result_obtained_yet
                    # set the right value
                    if results_to_request <= 0:
                        return
                    elif results_to_request < 10:
                        results_to_request = 10
                    elif results_to_request > 100 and self.__twitter_context_annotations:
                        results_to_request = 100
                    elif results_to_request > 500:
                        results_to_request = 500
                    self.log.debug("ASKING FOR: {} TWEETS".format(results_to_request))
                    self.__query['max_results'] = results_to_request
                # retrieve from the response the next token and pass it to the next query
                self.__next_page(next_token=self.response["meta"]["next_token"])
                # resend the request
                self.response = self.__connect_to_endpoint()
            # if there is not a next token stop the loop
            else:
                self.log.debug("NO NEXT TOKEN IN RESPONSE:INTERRUPTING")
                bar.close()
                break
        self.log.debug("THERE ARE NO OTHER PAGE AVAILABLE. ALL TWEETS REACHED")

    def search(self) -> int:
        """
        This method start the search on twitter. So first build the query and then send it to twitter.
        If are set in the config file more users for each user tries to
        retrieve the number of tweets set in n_result config file field, only after reach this number perform the
        search on the next user.

        :return: the number of the total tweets saved
        :rtype: int
        """
        bar1 = None
        no_user = True
        multi_user = False
        one_user = False
        bar = None

        if len(self.__twitter_users) > 0:
            no_user = False
            if len(self.__twitter_users) == 1:
                one_user = True
            else:
                multi_user = True

        if multi_user:
            self.log.debug("MULTI-USERS SEARCH")
            bar1 = tqdm(total=len(self.__twitter_users), leave=False, position=0,
                        desc="INFO:MULTI-USERS SEARCH:SEARCHING")
        elif one_user:
            bar1 = tqdm(total=len(self.__twitter_users), leave=False, position=0,
                        desc="INFO:SEARCH:SEARCHING FOR {}".format(self.__twitter_users[0]))
        for us in self.__twitter_users:
            if multi_user:
                bar1.set_description("INFO:MULTI-USERS SEARCH:SEARCHING FOR: {}".format(us))
            self.log.debug("SEARCH FOR: {}".format(us))
            self.__build_query(user=us)
            if self.__twitter_n_results:
                bar = tqdm(total=self.__twitter_n_results, desc="INFO:SEARCH:SEARCHING", leave=False, position=1)
            else:
                bar = tqdm(desc="INFO:SEARCH:SEARCHING", leave=False, position=1)
            self.__make(bar)
            bar.close()
            bar1.update(1)
        if no_user:
            self.__build_query()
            if self.__twitter_n_results:
                bar = tqdm(total=self.__twitter_n_results, desc="INFO:SEARCH:SEARCHING", leave=False, position=0)
            else:
                bar = tqdm(desc="INFO:SEARCH:SEARCHING", leave=False, position=0)
            self.__make(bar)
        # time.sleep(0.1)
        # if bar is not None:
        #    bar.close()
        print('\n')
        # self.log.info('CREATING NECESSARY INDEXES ON DB')
        # self.log.debug(self.mongodb.create_indexes())
        #

        return self.total_result

    def __save(self):
        """
        THis method are called after that a request have been sent to twitter. When called this method process all
        the tweets received in parallel using the multithreading and then save all tweets processed on the database.
        Note that process only the tweet not already in the database.

        :return: None
        """
        self.log.debug("SAVING TWEETS")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            results = []
            for tweet in self.response.get('data', []):
                fut = executor.submit(util.pre_process_tweets_response, tweet, self.response['includes'])
                fut.add_done_callback(self.__save_callback)
                futures.append(fut)
                results.append(tweet['text'])
                pd.DataFrame(results).to_csv('../../input.csv', sep=',', encoding='utf-8-sig', index=True, header=['Tweet'])
                # if not self.mongodb.is_in(tweet['id']):
                #     self.log.debug(tweet)
                #     # process each tweet ib parallel
                #     fut = executor.submit(util.pre_process_tweets_response, tweet, self.response['includes'])
                #     fut.add_done_callback(self.__save_callback)
                #     futures.append(fut)
                # else:
                #     # if the tweet is already in the db not save it and update the value of the number of tweets saved.
                #     self.total_result -= 1

        for job in tqdm(as_completed(futures), total=len(futures), desc="INFO:SEARCH:SAVING", leave=False, position=1):
            pass

        # self.mongodb.save_many(self._all)
        # # clean the list populate with these tweets processed.
        # self._all = []

    def __save_callback(self, fut: Future):
        # append the tweet process on a list
        self._all.append(fut.result())
