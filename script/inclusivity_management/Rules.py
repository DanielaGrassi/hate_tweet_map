import spacy
import RuntimePos as rp
import pandas as pd
import yaml
from script.search_tweets import search_tweets
from script.process_tweets import process_tweet
from script.manage_tweets import manage_tweets

mylist = []


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


def article_noun(tweet, explain):
    # Articolo femminile + nome proprio (spesso si riferisce solo alle donne)
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == "PROPN":
            if (check_surname(str(token).lower()) or check_female_name(str(token).lower())) and idx != 0:
                if tweet[idx - 1][1] == 'DET':
                    if 'Gender' in tweet[idx - 1][3] and 'PronType' in tweet[idx - 1][3]:
                        if tweet[idx - 1][3]['Gender'] == 'Fem' and tweet[idx - 1][3]['PronType'] == 'Art':
                            inclusive = -0.5
                            if explain:
                                print(
                                    "Utilizzare un articolo davanti ad un nome femminile diminuisce di molto l'inclusività!")

    return inclusive


def femaleName_maleAppos(tweet, male_crafts, explain):
    # Alessia è un avvocato formidabile
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == 'PROPN' and check_female_name(token):
            if idx + 1 < len(tweet):
                if tweet[idx + 1][2] == 'compound':
                    if tweet[idx + 1][0] in male_crafts:
                        inclusive = - 0.25
                        if explain:
                            print("Utilizzare un nome femminile con un'apposizione maschile diminuisce l'inclusività")

    return inclusive


def art_donna_noun(tweet, crafts, explain):
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token == 'donna' and idx != 0:
            if idx + 1 < len(tweet):
                if tweet[idx + 1][1] == 'NOUN' and tweet[idx + 1][2] == 'compound':
                    if tweet[idx + 1][0] in crafts:
                        inclusive = - 0.25
                        if explain:
                            print(
                                "Utilizzare il sostantivo 'donna' con un' apposizione maschile' diminuisce l'inclusività")
    return inclusive


def maleAppos_femaleName(tweet, male_crafts, explain):
    # L'assessore Alessia
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token in male_crafts:
            if idx + 1 < len(tweet):
                if tweet[idx + 1][1] == 'PROPN' and check_female_name(tweet[idx + 1][0]):
                    inclusive = - 0.25
                    if explain:
                        print("Utilizzare un'apposizione  maschile con un nome femminile diminuisce l'inclusività")
    return inclusive


def noun_donna(tweet, male_crafts, explain):
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if idx + 1 < len(tweet):
            if tweet[idx + 1][0] in male_crafts:
                if token == 'donna' and idx != 0:
                    if tweet[idx + 1][1] == 'NOUN' and tweet[idx + 1][2] == 'compound':
                        inclusive = - 0.25
                        if explain:
                            print(
                                "Utilizzare un'apposizione maschile con il sostantivo 'donna' diminuisce l'inclusività")
    return inclusive


def femaleSub_malePart(tweet, explain):
    inclusive = 0.0
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
                                        print(
                                            "Utilizzare un sostantivo femminile con un verbo al maschile diminuisce l'inclusività")
    return inclusive


def pronoun_inclusive(tweet, explain):
    inclusive = 0.0
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
                                        print("Utilizzare i pronomi declinati in più forme aumenta l'inclusività")
    return inclusive


def article_inclusive(tweet, explain):
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        #print(token, tag, det, morph)
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
                                        print("Utilizzare gli articoli declinati in più forme aumenta l'inclusività")
    return inclusive


def words_ends_with2gender(tweet, explain):
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        #print(token, tag, det, morph)
        if token == '/' or token == '\\':
            if idx + 1 < len(tweet):
                if tweet[idx + 1][0] == 'a' or tweet[idx + 1][0] == 'e':
                    inclusive = 0.10
                    if explain:
                        print("Utilizzare parole declinate in più forme aumenta l'inclusività")
    return inclusive


def schwa(tweet, explain):
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token.endswith('*') or token.endswith('ə'):
            inclusive = 0.25
            if explain:
                print("Utilizzare caratteri come la schwa o l'asterisco alla fine di una parola aumenta l'inclusività")
    return inclusive


def male_collettives_cases(tweet, male_crafts, explain):
    inclusive = 0.0
    both_detected = False
    # Se ho che il nome che ho nella frase è un mestiere maschile
    for idx, (token, tag, det, morph) in enumerate(tweet):
        doc = nlp(token)
        for w in doc:
            if tag == 'NOUN' and w.lemma_ in male_crafts:
                if 'Number' in morph and morph['Number'] == 'Plur':
                    pos = male_list.index(w.lemma_)
                    counter_propn = 0
                    for words in tweet:
                        token_words, tag_words, det_words, morph_words = words
                        doc_token = nlp(token_words)
                        for d in doc_token:
                            if tag_words == 'NOUN' and d.lemma_ in female_list:
                                pos1 = female_list.index(d.lemma_)
                                if pos == pos1:
                                    if 'Number' in morph_words and morph_words['Number'] == 'Plur':
                                        both_detected = True  # Flag per capire se sono stati trovati sia lavoro femminile che maschile
                                        inclusive = +0.50
                                        if explain:
                                            print(
                                                "Utilizzare un nome collettivo maschile con il corrispettivo femminile aumenta l'inclusività!")
                            if tag_words == "PROPN":
                                if check_male_name(
                                        token_words):  # Controllare se è un nome proprio maschile (da una lista)
                                    counter_propn = counter_propn + 1
                    if counter_propn > 1:
                        inclusive = inclusive
                    else:
                        if both_detected == False:  # Se non sono stati trovati sia lavoro femminile che maschile
                            inclusive += -0.25
                            if explain:
                                print(
                                    "Utilizzare un nome collettivo maschile senza il corrispettivo femminile o senza nomi propri maschili associati diminuisce l'inclusività!")

    return inclusive


def male_expressions(sentence, explain):
    with open('docs/uomini_di.txt', 'r', encoding='utf-8') as f:
        myExpressions = set(line.strip() for line in f)
    inclusive = 0.0
    for expression in myExpressions:
        if "desiderio di paternità" not in sentence:
            if str(expression).lower() in str(sentence).lower():
                inclusive = - 0.25
                if explain:
                    print("Utilizzare espressioni comuni riferite solo agli uomini diminuisce l'inclusività")
    return inclusive


# def male_female_jobs(tweet, male_list, female_list, explain):
#     inclusive= 0.0
#     for idx, (token, tag, det, morph) in enumerate(tweet):
#         doc = nlp(token)
#         for w in doc:
#             if tag == 'NOUN' and w.lemma_ in male_list:
#                 if 'Number' in morph and morph['Number'] == 'Plur':
#                     pos = male_list.index(w.lemma_)
#                     for words in tweet:
#                         token_words, tag_words, det_words, morph_words = words
#                         doc_token = nlp(token_words)
#                         for d in doc_token:
#                             if tag_words =='NOUN' and d.lemma_ in female_list:
#                                 pos1=female_list.index(d.lemma_)
#                                 if pos == pos1:
#                                     if 'Number' in morph_words and morph_words['Number'] == 'Plur':
#                                         inclusive = 0.50
#                                         if explain:
#                                             print("Utilizzare sia il femminile che il maschile per esprimere
#                                             i lavori aumenta l'inclusività")
#     return inclusive


def main():
    # df = pd.DataFrame({'Tweet': sentences})
    # df['Tweet'].to_csv('../../tweets.csv', encoding='utf-8-sig', index = False)

    path = '../../data.json'
    sentences, ph = rp.runtimePos(path)
    for sentence, phrase in zip(sentences, ph):
        inclusive = 0.0
        explain = True
        inclusive += words_ends_with2gender(phrase, explain)
        inclusive += schwa(phrase, explain)
        inclusive += article_noun(phrase, explain)
        inclusive += pronoun_inclusive(phrase, explain)
        inclusive += femaleName_maleAppos(phrase, male_crafts, explain)
        inclusive += art_donna_noun(phrase, male_crafts, explain)
        inclusive += noun_donna(phrase, male_crafts, explain)
        inclusive += femaleSub_malePart(phrase, explain)
        inclusive += maleAppos_femaleName(phrase, male_crafts, explain)
        inclusive += article_inclusive(phrase, explain)
        inclusive += male_collettives_cases(phrase, male_crafts, explain)
        inclusive += male_expressions(sentence, explain)
        print(sentence)

        print(inclusive)



def menu_list():
    operation = input(
        '''From which source do you want tweets to be taken?:\n [1] List of tweet \n [2] Twitter User-ID \n''')

    if operation == '1':
        print("Type the path to the list of tweet you would like to examine: ")
        number = str(input())
        mylist.append(number)

    elif operation == '2':
        print("Type the Twitter User-ID whose tweets you would like to analyze : ")
        number = str(input())
        mylist.append(number)

    else:
        print('You have not chosen a valid operator, please run the program again.')

    #again()


def again():
    list_again = input('''Would you like to see main menu again? (Y/N)''')

    if list_again.upper() == 'Y':
        menu_list()
    elif list_again.upper() == 'N':
        print('OK. Bye bye. :)')
    else:
        again()


if __name__ == "__main__":

    nlp = spacy.load("it_core_news_lg")
    ## inclusivity for the whole dataset
    crafts_path = '../../script/inclusivity_management/docs/list.tsv'
    crafts = read_tsv(crafts_path)
    male_list = list(crafts['itemLabel'])
    female_list = list(crafts['femaleLabel'])
    male_crafts = set(crafts['itemLabel'].unique())
    female_crafts = set(crafts['femaleLabel'].unique())

    menu_list()

    with open("../../script/search_tweets/search_tweets.config", "r") as params_file:
        params = yaml.safe_load(params_file)
    params['twitter']['search']['user'] = mylist[0]

    with open("../../script/search_tweets/search_tweets.config", "w") as params_file:
        yaml.dump(params, params_file, default_flow_style=False)

    search_tweets.main()
    process_tweet.main()
    manage_tweets.main()

    main()
