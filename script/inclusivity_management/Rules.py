import spacy
import RuntimePos as rp
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


def male_female_jobs(tweet, male_list, female_list):
    #Controlla che ci siano sia il mestiere maschile plurale che quello femminile
    male_female_detected = False
    male_female_words_detected=[]
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
                                pos1 = female_list.index(d.lemma_)
                                if pos == pos1:
                                    if 'Number' in morph_words and morph_words['Number'] == 'Plur':
                                        male_female_detected = True
                                        male_female_words_detected.append(token)
                                        male_female_words_detected.append(token_words)

    return male_female_detected,male_female_words_detected

def article_noun(tweet, explain):
    # Articolo femminile + nome proprio (spesso si riferisce solo alle donne)-> La Boschi
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if tag == "PROPN":
            if (check_surname(str(token).lower()) or check_female_name(str(token).lower())) and idx != 0:
                if tweet[idx - 1][1] == 'DET':
                    if 'Gender' in tweet[idx - 1][3] and 'PronType' in tweet[idx - 1][3]:
                        if tweet[idx - 1][3]['Gender'] == 'Fem' and tweet[idx - 1][3]['PronType'] == 'Art':
                            inclusive = -0.25
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
                        print("Utilizzare un'apposizione maschile con un nome femminile diminuisce l'inclusività")
    return inclusive


def noun_donna(tweet, male_crafts, explain):
    #L'assessore donna
    inclusive = 0.0
    for idx, (token, tag, det, morph) in enumerate(tweet):
        if token in male_crafts:
            if idx + 1 < len(tweet):
                if tweet[idx + 1][0] == 'donna':
                    inclusive = - 0.25
                    if explain:
                        print("Utilizzare un'apposizione maschile seguito da 'donna' diminuisce l'inclusività")
    return inclusive


def femaleSub_malePart(tweet, explain):
    # Daniela è andato
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
    # lui/lei
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
    # il/la - un/una
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

def male_collettives(tweet, male_list, explain):
    inclusive = 0.0
    pl_male_job=[]
    minus_points=False
    # Se ho che il nome che ho nella frase è un mestiere maschile
    male_female_detected, male_female_words_detected = male_female_jobs(tweet, male_list, female_list)
    if male_female_detected == True:
        inclusive += 0.25
        if explain:
            ("Utilizzare sia mestiere maschile plurale che il corrispettivo femminile aumenta l'inclusività!")
    for idx, (token, tag, det, morph) in enumerate(tweet):
        doc = nlp(token)
        counter_propn = 0
        w = [tok for tok in doc]
        if tag == 'NOUN' and w[0].lemma_ in male_list:
            if 'Number' in morph and morph['Number'] == 'Plur':
                pl_male_job.append(token)
                for word in tweet:
                    token_word, tag_word, det_word, morph_word = word
                    if tag_word == "PROPN":
                        if check_male_name(token_word): #Controllare se è un nome proprio maschile (da una lista)
                            counter_propn = counter_propn+1
        if counter_propn > 1:
            inclusive = inclusive


    # per i mestieri plurali identificati nel tweet e nelle parole che invece soddisfano la funzione male_female_jobs
    # controlla che i mestieri plurali identificati non siano proprio le parole che hanno triggerato male_female_jobs
    # Se c'è almeno un maschile plurale che non ha triggerato la regola (dunque che ci sia solo il maschile plurale)
    # Sottrai 0.25
    print(pl_male_job, male_female_words_detected)
    for job in pl_male_job:
        # questo controllo fallisce non so perchè, infatti risulta sempre True questo booleano, quindi fallisce il controllo successivo
        if job not in male_female_words_detected:
            print("il booleano minus_points è stato settato a true")
            minus_points = True

#todo: il controllo ora va bene però ci sono dei problemi per quanto riguarda gli array pl_male_job e male_female_words che non si svuotano.
    if minus_points==True:
        inclusive += -0.25
        if explain:
            print("Utilizzare un nome collettivo maschile diminuisce l'inclusività!")
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




if __name__ == "__main__":
    d = []
    path = '../../data.json'
    nlp = spacy.load("it_core_news_lg")
    crafts_path = '../../script/inclusivity_management/docs/list.tsv'

    ## inclusivity for the whole dataset
    crafts = read_tsv(crafts_path)
    male_list = list(crafts['itemLabel'])
    female_list = list(crafts['femaleLabel'])
    male_crafts = set(crafts['itemLabel'].unique())
    female_crafts = set(crafts['femaleLabel'].unique())
    sentences, ph = rp.runtimePos(path)

    df = pd.DataFrame({'Tweet': sentences, })
    df['Tweet'].to_csv('../../tweets.csv', encoding='utf-8-sig', index=False)

    for sentence, phrase in zip(sentences, ph):
        inclusive = 0.0
        explain = True
        # inclusive += words_ends_with2gender(phrase, explain)
        # inclusive += schwa(phrase, explain)
        # inclusive += article_noun(phrase, explain)
        # inclusive += pronoun_inclusive(phrase, explain)
        # inclusive += femaleName_maleAppos(phrase, male_crafts, explain)
        # inclusive += art_donna_noun(phrase, male_crafts, explain)
        # inclusive += noun_donna(phrase, male_crafts, explain)
        # inclusive += femaleSub_malePart(phrase, explain)
        # inclusive += maleAppos_femaleName(phrase, male_crafts, explain)
        # inclusive += article_inclusive(phrase, explain)
        inclusive += male_collettives(phrase, male_list, explain)
        #inclusive += male_female_jobs(phrase, male_list, female_list, explain)
        #inclusive += male_expressions(sentence, explain)

    #     d.append(
    #         {
    #             'Tweet': sentence.replace("\t", ""),
    #             'inclusive_rate': inclusive
    #         }
    #     )
        print(sentence)
        print(inclusive)
    #
    # pd.DataFrame(d).to_csv('../../tweets.csv', sep='\t', encoding='utf-8-sig', index=False)