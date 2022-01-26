import re
import yaml
import pandas as pd

def read_tsv(tsv):
    rd = pd.read_csv(tsv, sep='\t')
    return rd


def check_female_name(token):
    with open('docs/nomif.txt', 'r', encoding='utf-8') as f:
        myNamesFemale = set(line.strip() for line in f)

    if token.lower() in myNamesFemale:
        return True
    else:
        return False


def check_male_name(token):
    with open('docs/nomim.txt', 'r', encoding='utf-8') as f:
        myNamesMale = set(line.strip() for line in f)

    if token.lower() in myNamesMale:
        return True
    else:
        return False


def check_surname(token):
    with open('docs/lista_cognomi.txt', 'r', encoding='utf-8') as f:
        mySurnames = set(line.strip() for line in f)

    if token.lower() in mySurnames:
        return True
    else:
        return False

def clean_tweet (t):
    clean_tweet = re.sub("@[A-Za-z0-9_]+", "", t)
    clean_tweet = re.sub("#[A-Za-z0-9_]+", "", clean_tweet)
    clean_link = re.sub(r"http\S+", "", clean_tweet)
    regrex_pattern = re.compile(pattern="["
                                        u"\U0001F600-\U0001F64F"  # emoticons
                                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                        "]+", flags=re.UNICODE)
    result = regrex_pattern.sub(r'', clean_link)
    result = result.lower()
    return result


def calculate_user_score(results_csv):

    tweets = pd.read_csv(results_csv)
    df = pd.DataFrame(tweets)
    inclusivity_sum = df['inclusive_rate'].sum()
    n_tweets = df['inclusive_rate'].count()
    inclusivity_score = inclusivity_sum/n_tweets
    if inclusivity_score > 0.00:
        user_label = "inclusive"
    elif inclusivity_score == 0.00:
        user_label = "neutral"
    else:
        user_label = "non-inclusive"

    return inclusivity_score, user_label
