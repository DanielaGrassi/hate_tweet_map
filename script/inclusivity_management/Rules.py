import spacy
from spacy.lang.it.examples import sentences
from spacy.pipeline import morphologizer
import RuntimePos as rp
import pandas as pd


def read_tsv(tsv):

    rd = pd.read_csv(tsv,sep='\t')
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



def article_noun(tweet):
# Articolo femminile + nome proprio (spesso si riferisce solo alle donne)
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag =="PROPN":
            if (check_surname(str(token).lower()) or check_female_name(str(token).lower())) and idx != 0:
                if tweet[idx-1][1] == 'DET':
                    if 'Gender' in tweet[idx-1][3] and 'PronType' in tweet[idx-1][3]:
                        if tweet[idx-1][3]['Gender'] == 'Fem' and tweet[idx-1][3]['PronType'] == 'Art':
                           inclusive = -0.5
                           print("Utilizzare un articolo davanti ad un nome femminile diminuisce di molto l'inclusività!")

    return inclusive


def femaleName_maleAppos(tweet, male_crafts):
# Alessia è un avvocato formidabile
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == 'PROPN' and check_female_name(token):
            if (idx + 1 < len(tweet)):
                if tweet[idx+1][2] == 'compound':
                    if tweet[idx+1][0] in male_crafts:
                        print("Utilizzare un nome femminile con un'apposizione maschile diminuisce l'inclusività")
                        inclusive = - 0.25

    return inclusive

def art_donna_noun(tweet, crafts):
    inclusive= 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token == 'donna' and idx != 0:
            if (idx + 1 < len(tweet)):
                if tweet[idx+1][1] == 'NOUN' and tweet[idx+1][2] == 'compound':
                    if tweet[idx+1][0] in crafts:
                        inclusive = - 0.25
                        print("Utilizzare il sostantivo 'donna' con un' apposizione maschile' diminuisce l'inclusività")
    return inclusive


def maleAppos_femaleName(tweet, male_crafts):
    # L'assessore Alessia
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token in male_crafts:
            if (idx + 1 < len(tweet)):
                if tweet[idx + 1][1] == 'PROPN' and check_female_name(tweet[idx + 1][0]):
                    inclusive = - 0.25
                    print("Utilizzare un'apposizione  maschile con un nome femminile diminuisce l'inclusività")
    return inclusive

def noun_donna(tweet, male_crafts):
    inclusive= 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if (idx + 1 < len(tweet)):
            if tweet[idx+1][0] in male_crafts:
                if token == 'donna' and idx != 0:
                  if tweet[idx+1][1] == 'NOUN' and tweet[idx+1][2] == 'compound':
                     inclusive = - 0.25
                     print("Utilizzare un'apposizione maschile con il sostantivo 'donna' diminuisce l'inclusività")
    return inclusive


def femaleSub_malePart(tweet):
    inclusive= 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == 'PROPN' or tag == 'NOUN' and det == 'nsubj':
            continue
        if tag == 'AUX' and det == 'aux':
            if 'Person' in morph:
                if morph['Person'] == '3' and morph['Number'] == 'Sing':
                    if (idx + 1 < len(tweet)):
                        if tweet[idx+1][1] == 'VERB' and tweet[idx+1][2] == 'ROOT':
                            if 'Gender' in morph and 'VerbForm' in morph and 'Number' in morph:
                                if tweet[idx+1][3]['Gender'] == 'Masc' and tweet[idx+1][3]['VerbForm'] == 'Part' and tweet[idx+1][3]['Number'] == 'Sing':
                                    inclusive = - 0.25
                                    print("Utilizzare un sostantivo femminile con un verbo al maschile diminuisce l'inclusività")
    return inclusive


def article_inclusive(tweet):
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == 'PRON' or tag == 'NOUN':
            if 'Gender' in morph:
               if morph['Gender'] == 'Masc':
                   if (idx+2 < len(tweet)):
                       if tweet[idx + 1][0] == '/' or tweet[idx + 1][0] == '\\':
                          if tweet[idx + 2][1] == 'PRON' or tweet[idx + 2][1] == 'NOUN' and morph[idx + 2]['Gender'] == 'Fem':
                             inclusive = 0.25
                             print("Utilizzare gli articoli declinati in più forme aumenta l'inclusività")
    return inclusive


def male_collettives(tweet, male_crafts):
    inclusive = 0.0
    # Se ho che il nome che ho nella frase è un mestiere maschile
    for idx, (token, tag, det, morph) in enumerate(tweet):
        doc=nlp(token)
        for w in doc:
            if tag == 'NOUN' and w.lemma_ in male_crafts:
                if 'Number' in morph and morph['Number'] == 'Plur':
                    counter_propn=0
                    for words in tweet:
                        token_words, tag_words, det_words, morph_words= words
                        if tag_words=="PROPN":
                            if check_male_name(token_words): # Controllare se è un nome proprio maschile (da una lista)
                                counter_propn= counter_propn+1
                    if counter_propn > 1:
                        inclusive=inclusive
                    else:
                        inclusive= -0.25
                        print("Utilizzare un nome collettivo maschile diminuisce l'inclusività!")
    return inclusive

def male_expressions(sentence):
    with open('docs/uomini_di.txt', 'r', encoding='utf-8') as f:
        myExpressions = set(line.strip() for line in f)
    inclusive = 0.0
    for expression in myExpressions:
        if str(expression).lower() in str(sentence).lower():
            inclusive = - 0.25
    return inclusive

def male_female_jobs(tweet, male_list, female_list):
    inclusive= 0.0
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
                            if tag_words =='NOUN' and d.lemma_ in female_list:
                                pos1=female_list.index(d.lemma_)
                                if pos == pos1:
                                    if 'Number' in morph_words and morph_words['Number'] == 'Plur':
                                        inclusive = 0.25
                                        print("Utilizzare sia il femminile che il maschile per esprimere i lavori aumenta l'inclusività")
    return inclusive

if __name__ == "__main__":
    path = '../../data.json'
    nlp = spacy.load("it_core_news_lg")
    crafts_path = '../../script/inclusivity_management/docs/list.tsv'

    ## inclusivity for the whole dataset
    crafts = read_tsv(crafts_path)
    male_list=list(crafts['itemLabel'])
    female_list=list(crafts['femaleLabel'])
    male_crafts = set(crafts['itemLabel'].unique())
    female_crafts = set(crafts['femaleLabel'].unique())
    sentences, ph = rp.runtimePos(path)
    for sentence, phrase in zip(sentences, ph):
        inclusive = 0.0
        inclusive += article_noun(phrase)
        inclusive += femaleName_maleAppos(phrase, male_crafts)
        inclusive += art_donna_noun(phrase, male_crafts)
        inclusive += noun_donna(phrase, male_crafts)
        inclusive += femaleSub_malePart(phrase)
        inclusive += maleAppos_femaleName(phrase, male_crafts)
        inclusive += article_inclusive(phrase)
        inclusive += male_collettives(phrase, male_crafts)
        inclusive += male_expressions(sentence)
        inclusive += male_female_jobs(phrase, male_list, female_list)
        print(sentence)

        print(inclusive)


