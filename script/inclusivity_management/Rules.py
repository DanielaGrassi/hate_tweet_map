import json

import spacy
import RuntimePos as rp
import argparse
import pandas as pd
import yaml
import re
import script.inclusivity_management.utils as utils
from script.search_tweets import search_tweets
from script.process_tweets import process_tweet
from script.manage_tweets import manage_tweets
from hate_tweet_map.tweets_processor.TweetProcessor import ProcessTweet


def male_female_jobs(tweet, male_list, female_list):
    # Controlla che ci siano sia il mestiere maschile plurale che quello femminile
    male_female_detected = False
    male_female_words_detected = []
    for idx, (token, tag, det, morph) in enumerate(tweet):
        doc = nlp(token)
        for w in doc:
            if tag == 'NOUN' and w.lemma_ in male_list:
                if 'Number' in morph and morph['Number'] == 'Plur':
                    pos = male_list.index(w.lemma_)
                    for words in tweet:
                        token_words, tag_words, det_words, morph_words = words
                        doc_token = nlp(token_words)
                        for d in doc_token:
                            if tag_words == 'NOUN' and d.lemma_ in female_list:
                                pos1 = female_list.index(d.lemma_)
                                if pos == pos1:
                                    if 'Number' in morph_words and morph_words['Number'] == 'Plur':
                                        male_female_detected = True
                                        male_female_words_detected.append(token)
                                        male_female_words_detected.append(token_words)

    return male_female_detected, male_female_words_detected


def article_noun(tweet, explain):
    # Articolo femminile + nome proprio (spesso si riferisce solo alle donne)-> La Boschi
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == "PROPN":
            if (utils.check_surname(str(token).lower()) or utils.check_female_name(str(token).lower())) and idx != 0:
                if tweet[idx - 1][1] == 'DET':
                    if 'Gender' in tweet[idx - 1][3] and 'PronType' in tweet[idx - 1][3]:
                        if tweet[idx - 1][3]['Gender'] == 'Fem' and tweet[idx - 1][3]['PronType'] == 'Art':
                            inclusive = -0.25
                            if explain:
                                explanation = "Utilizzare un articolo davanti ad un nome femminile diminuisce di molto l'inclusività!"

    return inclusive, explanation


def femaleName_maleAppos(tweet, male_crafts, explain):
    # Alessia è un avvocato formidabile
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == 'PROPN' and utils.check_female_name(token):
            if idx + 1 < len(tweet):
                if tweet[idx + 1][2] == 'compound':
                    if tweet[idx + 1][0] in male_crafts:
                        inclusive = - 0.25
                        if explain:
                            explanation="Utilizzare un nome femminile con un'apposizione maschile diminuisce l'inclusività"

    return inclusive, explanation


def art_donna_noun(tweet, crafts, explain):
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        print(idx, (token, tag, det, morph))
        if token == 'donna' and idx != 0:
            print(token)
            if idx + 1 < len(tweet):
                if tweet[idx + 1][1] == 'NOUN' and tweet[idx + 1][2] == 'compound':
                    print(tweet[idx + 1][1])
                    print(tweet[idx + 1][0])
                    print(crafts)
                    if tweet[idx + 1][0] in crafts:

                        inclusive = - 0.25
                        print(inclusive)
                        if explain:
                            explanation =  "Utilizzare il sostantivo 'donna' con un' apposizione maschile' diminuisce l'inclusività"
    return inclusive, explanation


def maleAppos_femaleName(tweet, male_crafts, explain):
    # L'assessore Alessia
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token in male_crafts:
            if idx + 1 < len(tweet):
                if tweet[idx + 1][1] == 'PROPN' and utils.check_female_name(tweet[idx + 1][0]):
                    inclusive = - 0.25
                    if explain:
                        explanation = "Utilizzare un'apposizione maschile con un nome femminile diminuisce l'inclusività"
    return inclusive, explanation


def noun_donna(tweet, male_crafts, explain):
    # L'assessore donna
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token in male_crafts:
            if idx + 1 < len(tweet):
                if tweet[idx + 1][0] == 'donna':
                    inclusive = - 0.25
                    if explain:
                        explanation = "Utilizzare un'apposizione maschile seguito da 'donna' diminuisce l'inclusività"
    return inclusive, explanation


def femaleSub_malePart(tweet, explain):
    # Daniela è andato
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == 'PROPN' or tag == 'NOUN' and det == 'nsubj':
            continue
        if tag == 'AUX' and det == 'aux':
            if 'Person' in morph:
                if morph['Person'] == '3' and morph['Number'] == 'Sing':
                    if idx + 1 < len(tweet):
                        if tweet[idx + 1][1] == 'VERB' and tweet[idx + 1][2] == 'ROOT':
                            if 'Gender' in morph and 'VerbForm' in morph and 'Number' in morph:
                                if tweet[idx + 1][3]['Gender'] == 'Masc' and tweet[idx + 1][3]['VerbForm'] == 'Part' and \
                                        tweet[idx + 1][3]['Number'] == 'Sing':
                                    inclusive = - 0.25
                                    if explain:
                                        explanation = "Utilizzare un sostantivo femminile con un verbo al maschile diminuisce l'inclusività"
    return inclusive, explanation


def pronoun_inclusive(tweet, explain):
    # lui/lei
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == 'PRON' or tag == 'NOUN':
            if 'Gender' in morph:
                if morph['Gender'] == 'Masc':
                    if idx + 2 < len(tweet):
                        if tweet[idx + 1][0] == '/' or tweet[idx + 1][0] == '\\':
                            if 'Gender' in tweet[idx + 2][3]:
                                if tweet[idx + 2][1] == 'PRON' or tweet[idx + 2][1] == 'NOUN' and tweet[idx + 2][3][
                                    'Gender'] == 'Fem':
                                    inclusive = 0.10
                                    if explain:
                                        explanation = "Utilizzare i pronomi declinati in più forme aumenta l'inclusività"
    return inclusive, explanation


def article_inclusive(tweet, explain):
    # il/la - un/una
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        print(token, tag, det, morph)
        if tag == 'DET' and det == 'det':
            if 'Gender' in morph:
                if morph['Gender'] == 'Masc':
                    if idx + 2 < len(tweet):
                        if tweet[idx + 1][0] == '/' or tweet[idx + 1][0] == '\\':
                            if 'Gender' in tweet[idx + 2][3]:
                                if tweet[idx + 2][1] == 'DET' and tweet[idx + 2][2] == 'det' and tweet[idx + 2][3][
                                    'Gender'] == 'Fem':
                                    inclusive = 0.10
                                    if explain:
                                        explanation = "Utilizzare gli articoli declinati in più forme aumenta l'inclusività"
    return inclusive, explanation


def words_ends_with2gender(tweet, explain):
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token == '/' or token == '\\':
            if idx + 1 < len(tweet):
                if tweet[idx + 1][0] == 'a' or tweet[idx + 1][0] == 'e':
                    inclusive = 0.10
                    if explain:
                        explanation = "Utilizzare parole declinate in più forme aumenta l'inclusività"
    return inclusive, explanation


def schwa(tweet, explain):
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token.endswith('*') or token.endswith('ə'):
            inclusive = 0.25
            if explain:
                explanation = "Utilizzare caratteri come la schwa o l'asterisco alla fine di una parola aumenta l'inclusività"
    return inclusive, explanation


def male_collettives(tweet, male_list, explain):

    inclusive = 0.0
    pl_male_job = []
    minus_points = False
    explanation = None
    # Se ho che il nome che ho nella frase è un mestiere maschile
    male_female_detected, male_female_words_detected = male_female_jobs(tweet, male_list, female_list)
    if male_female_detected == True:
        print("adding 0.25")
        inclusive += 0.25
        if explain:
            explanation = "Utilizzare sia mestiere maschile plurale che il corrispettivo femminile aumenta l'inclusività!"
    for idx, (token, tag, det, morph) in enumerate(tweet):
        doc = nlp(token)
        counter_propn = 0
        w = [tok for tok in doc]
        # ####
        # if token == 'autoferrotranvieri' or token =='internavigatori':
        #     print(tag, det, morph,w[0].lemma_)
        # ####
        if tag == 'NOUN' and w[0].lemma_ in male_list:
            if 'Number' in morph and morph['Number'] == 'Plur':

                pl_male_job.append(token)
                for word in tweet:
                    token_word, tag_word, det_word, morph_word = word
                    if tag_word == "PROPN":
                        if utils.check_male_name(
                                token_word):  # Controllare se è un nome proprio maschile (da una lista)
                            counter_propn = counter_propn + 1
        if counter_propn > 1:
            inclusive = inclusive
        else:
            minus_points = True
            # per i mestieri plurali identificati nel tweet e nelle parole che invece soddisfano la funzione male_female_jobs
            # controlla che i mestieri plurali identificati non siano proprio le parole che hanno triggerato male_female_jobs
            # Se c'è almeno un maschile plurale che non ha triggerato la regola (dunque che ci sia solo il maschile plurale)
            # Sottrai 0.25
    print(pl_male_job, male_female_words_detected)
    for job in pl_male_job:
        if job not in male_female_words_detected and minus_points == True:
            print("il booleano minus_points è stato settato a true")
            inclusive += -0.25
            if explain:
                explanation = "Utilizzare un nome collettivo maschile diminuisce l'inclusività!"

    return inclusive, explanation


def male_expressions(sentence, explain):
    with open('docs/uomini_di.txt', 'r', encoding='utf-8') as f:
        myExpressions = set(line.strip() for line in f)
    inclusive = 0.0
    explanation = None
    for expression in myExpressions:
        if "desiderio di paternità" not in sentence:
            if str(expression).lower() in str(sentence).lower():
                inclusive = - 0.25
                if explain:
                    explanation = "Utilizzare espressioni comuni riferite solo agli uomini diminuisce l'inclusività"

    return inclusive, explanation


def save_postag(df):
    tweets = []
    phrase_pos = []
    pos_tagging = []
    for t in df['tweet']:
        result = utils.clean_tweet(t)
        tweets.append(result)
        doc = nlp(result)
        phrase_pos = []
        for token in doc:
            phrase_dict = {}
            for j in token.morph:
                if len(j) != 0:
                    couple_list = j.split('=')
                    phrase_dict[couple_list[0]] = couple_list[1]
            # mette i vari capturing group in phrase_pos
            phrase_pos.append((token.text, token.pos_, token.dep_, phrase_dict))

        pos_tagging.append(phrase_pos)
    return tweets, pos_tagging


def main(sentences, ph, explain):

    d = []


    for sentence, phrase in zip(sentences, ph):

        scores = []
        explanations = []
        #print(phrase)

        score, explanation = words_ends_with2gender(phrase, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = schwa(phrase, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = article_noun(phrase, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = pronoun_inclusive(phrase, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = femaleName_maleAppos(phrase, male_crafts, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = art_donna_noun(phrase, male_crafts, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation =noun_donna(phrase, male_crafts, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = femaleSub_malePart(phrase, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = maleAppos_femaleName(phrase, male_crafts, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = article_inclusive(phrase, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = male_collettives(phrase, male_list, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = male_female_jobs(phrase, male_list, female_list, explain)
        scores.append(score)
        explanations.append(explanation)

        score, explanation = male_expressions(sentence, explain)
        scores.append(score)
        explanations.append(explanation)


        inclusive = sum(scores)
        explanations = [x for x in explanations if x is not None]
        print(scores, explanations)
        d.append(
            {
                'Tweet': sentence.replace("\t", ""),
                'inclusive_rate': inclusive,
                'explanation': explanations
            }
        )

    pd.DataFrame(d).to_csv('../../tweets.csv', sep='\t', encoding='utf-8-sig', index=False)


if __name__ == "__main__":

    nlp = spacy.load("it_core_news_lg")
    ## inclusivity for the whole dataset
    crafts_path = '../../script/inclusivity_management/docs/list.tsv'
    crafts = utils.read_tsv(crafts_path)
    male_list = list(crafts['itemLabel'])
    female_list = list(crafts['femaleLabel'])
    male_crafts = set(crafts['itemLabel'].unique())
    female_crafts = set(crafts['femaleLabel'].unique())

    parser = argparse.ArgumentParser(description='Inclusivity rate calculator')

    parser.add_argument('--userid', type=str, help="This parameter should be a Twitter user id, "
                                                   "the inclusion rate is calculated on the last tweets of "
                                                   "the indicated user")
    parser.add_argument('--path', type=str, help="This parameter should be a path to the csv with a list of tweet")
    parser.add_argument('--explain', type=bool,
                        help="This parameter should be set True if you want the explanation, False otherwise")
    args = parser.parse_args()

    userid = args.userid
    path_csv = args.path
    explain = args.explain

    if userid is not None:
        with open("../../script/search_tweets/search_tweets.config", "r") as params_file:
            params = yaml.safe_load(params_file)
        params['twitter']['search']['user'] = userid

        with open("../../script/search_tweets/search_tweets.config", "w") as params_file:
            yaml.dump(params, params_file, default_flow_style=False)

        search_tweets.main()
        process_tweet.main()
        manage_tweets.main()
        sentences, ph = rp.runtimePos('../../data.json')
        main(sentences, ph, explain)

    if path_csv is not None:
        tweets = pd.read_csv(path_csv)
        sentences, ph = save_postag(tweets)
        d = []
        main(sentences, ph, explain)
