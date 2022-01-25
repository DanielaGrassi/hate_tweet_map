import spacy
import argparse
import pandas as pd
import yaml
import script.inclusivity_management.utils as utils
from script.search_tweets import search_tweets
import logging

"""
Rules.py:
This module contains Pattern matching and Lexicon-based rules for the detection of non-inclusiveness in Italian language.
Most of the rules use both approaches to reach the objective, for example, when checking the PROPN tag of spaCy, 
also lexicons of proper nouns are used. 
- male_female_jobs():       This rule checks that both male and female plural jobs are used in the same phrase. 
                            If the pattern matches, a score of 0.25 is added to the whole inclusiveness.
                            ex. "Si informano lavoratori e lavoratrici che il giorno 21 gennaio è indetto uno sciopero"
- article_noun():           This rule checks that a surname is not used with an article. 
                            If the pattern article + surname is respected, a score of 0.25 is taken off.
                            ex. "La Boschi"
- femaleName_maleAppos():   This rule checks if a female proper noun is followed by a male apposition. 
                            If this happens, a score of 0.25 is taken off from the whole inclusivity.
                            ex. "Alessia è un avvocato formidabile"
- art_donna_noun():         This rule checks if the noun "donna" is followed by a male noun. 
                            In this case, the score is decreased of 0.25.  
                            ex. "La donna medico è riuscita nell'intervento"
- maleAppos_femaleName():   This rule checks if a male apposition is followed by a female proper noun. 
                            If this happens, a score of 0.25 is taken off from the whole inclusivity.  
                            ex. "L'assessore Daniela ha presenziato la riunione"        
- noun_donna():             This rule checks if a male apposition is followed by the noun "donna". 
                            If this happens, a score of 0.25 is taken off from the whole inclusivity.  
                            ex. "L'assessore donna ha presenziato la riunione"
- femaleSub_malePart():     This rule checks if a female proper noun is used with a male participle tens. 
                            If this happens, a score of 0.25 is taken from the inclusivity score.  
                            ex. "Simona è andato alla spiaggia"
- pronoun_inclusive():      This rule checks if the gender pronouns are used together in the same phrase. 
                            If this happens, the inclusivity score is increased of 0.25.
                            ex. "lui/lei"
- article_inclusive():      This rule checks if the gender articles are used together in the same phrase. 
                            If this happens, the inclusivity score is increased of 0.25.
                            ex. "il/la - un/una"
- word_ends_with2gender():  This rule checks if a word is declinated in more forms, using two genders. 
                            If this happens, the inclusiveness score is increased of 0.10.
                            ex. "andati/e"
- schwa():                  This rule checks if in a phrase there are words that end with the schwa or with an asterisk. 
                            If this happens, for each item found, the score is increased of 0.10.
                            ex. "Taylor è vostr* amic*?"
- male_collettives():       This rule checks if a male plural job is used alone in the phrase. 
                            If this happens, the overall inclusivity score is decreased of 0.25 points.
                            ex. "Gli impiegati sono pregati di spagnere la luce quando lasciano lo studio"
- male_expressions():       This rule checks if a common expression only referred to male gender is used, taking as a reference a corpus built by us. 
                            If this happens, a score of 0.25 is taken from the inclusiveness score.
                            ex. "Beati gli uomini di fede"
"""


def male_female_jobs(tweet, male_list, female_list):
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
                                explanation = "Utilizzare un articolo davanti ad un nome femminile diminuisce l'inclusività!"

    return inclusive, explanation


def femaleName_maleAppos(tweet, male_crafts, explain):
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == 'PROPN' and utils.check_female_name(token):
            if idx + 1 < len(tweet):
                if tweet[idx + 1][2] == 'compound':
                    if tweet[idx + 1][0] in male_crafts:
                        inclusive = - 0.25
                        if explain:
                            explanation = "Utilizzare un nome femminile con un'apposizione maschile diminuisce l'inclusività"

    return inclusive, explanation


def art_donna_noun(tweet, crafts, explain):
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token == 'donna' and idx != 0:
            if idx + 1 < len(tweet):
                if tweet[idx + 1][1] == 'NOUN' and tweet[idx + 1][2] == 'compound':
                    if tweet[idx + 1][0] in crafts:

                        inclusive = - 0.25
                        if explain:
                            explanation = "Utilizzare il sostantivo 'donna' con un' apposizione maschile' diminuisce l'inclusività"
    return inclusive, explanation


def maleAppos_femaleName(tweet, male_crafts, explain):
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
    inclusive = 0.0
    explanation = None
    for idx, (token, tag, det, morph) in enumerate(tweet):
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
    counter_propn = 0
    explanation = None

    male_female_detected, male_female_words_detected = male_female_jobs(tweet, male_list, female_list)
    if male_female_detected == True:
        inclusive += 0.25
        if explain:
            explanation = "Utilizzare sia mestiere maschile plurale che il corrispettivo femminile aumenta l'inclusività!"

    for idx, (token, tag, det, morph) in enumerate(tweet):
        doc = nlp(token)

        w = [tok for tok in doc]
        if tag == 'NOUN' and w[0].lemma_ in male_list:
            if 'Number' in morph and morph['Number'] == 'Plur':

                pl_male_job.append(token)
                for word in tweet:
                    token_word, tag_word, det_word, morph_word = word
                    if tag_word == "PROPN":

                        if utils.check_male_name(
                                token_word):
                            counter_propn = counter_propn + 1

    for job in pl_male_job:
        if job not in male_female_words_detected:
            if counter_propn > 1:
                inclusive = 0.0
            else:
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
    pos_tagging = []
    for t in df['Tweet']:
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


def rules(sentences, ph, explain):
    d = []
    for sentence, phrase in zip(sentences, ph):
        scores = []
        explanations = []

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

        score, explanation = noun_donna(phrase, male_crafts, explain)
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

        score, explanation = male_expressions(sentence, explain)
        scores.append(score)
        explanations.append(explanation)

        inclusive = sum(scores)
        explanations = [x for x in explanations if x is not None]

        sentence = sentence.replace(",", "")
        sentence = sentence.replace("\"", "")

        d.append(
            {
                'Tweet': sentence.replace("\t", " "),
                'inclusive_rate': inclusive,
                'explanation': explanations
            }
        )

        logging.info(sentence)
        logging.info(phrase)
        logging.info(inclusive)
        logging.info(explanations)

    return d


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
    parser.add_argument('--n_tweet', type=int, help="This parameter should be the number of the tweet to retrieve")
    parser.add_argument('--explain', dest='explain', action='store_true',
                        help="This parameter return the explaination of the score")
    parser.add_argument('--no_explain', dest='explain', action='store_false',
                        help="This parameter don't return the explaination of the score")
    parser.set_defaults(explain=True)
    parser.add_argument('--verbose', dest='verbose', action='store_true')
    parser.set_defaults(explain=True)
    parser.set_defaults(verbose=False)
    args = parser.parse_args()

    userid = args.userid
    path_csv = args.path
    n_tweet = args.n_tweet
    explain = args.explain
    verbose = args.verbose

    if verbose:
        logging.basicConfig(filename="../../log.txt", level=logging.INFO)

    if userid is not None:
        with open("../../script/search_tweets/search_tweets.config", "r") as params_file:
            params = yaml.safe_load(params_file)
        params['twitter']['search']['user'] = userid
        params['twitter']['search']['n_results'] = n_tweet

        with open("../../script/search_tweets/search_tweets.config", "w") as params_file:
            yaml.dump(params, params_file, default_flow_style=False)

        search_tweets.main()
        tweets = pd.read_csv('../../input.csv')
        sentences, ph = save_postag(tweets)
        d = rules(sentences, ph, explain)

    if path_csv is not None:
        tweets = pd.read_csv(path_csv)
        sentences, ph = save_postag(tweets)
        d = rules(sentences, ph, explain)

    pd.DataFrame(d).  to_csv('../../results.csv', sep=',', encoding='utf-8-sig', index=False)
