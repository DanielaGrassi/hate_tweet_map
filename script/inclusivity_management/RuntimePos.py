import json
import re


path = '../../data.json'



def runtimePos(path):
    with open(path) as f:
        dataset = json.load(f)
    pos=[]
    sentences = []
    for tweet in dataset:
        df = tweet['spacy']
        raw_text = tweet['raw_text']
        sentences.append((raw_text))
        pos.append(df)

    #mette il pos tagging in una lista, senza le entità
    processed_text = [ob['processed_text'] for ob in pos]
    pos_tagging = []
    pattern = '([^\|]*) \| POS : ([^\| ]*) \| DEP : ([^\| ]*) \| MORPH : ([^\| ]*)'

    for phrase in processed_text:
        #dichiaro una lista vuota per ogni parola del tweet, in cui ci sarà l'analisi testuale
        phrase_pos = []
        for word in phrase:
            split = re.match(pattern, word)
            morph = split[4].split('-')

            #un dizionario in cui la chiave sarà per esempio (il gender, il numero.. ) e il valore sarà (feminile, plurale)
            phrase_dict = {}
            for j in morph:
               if len(j) != 0:
                  couple_list = j.split('=')
                  phrase_dict[couple_list[0]] = couple_list[1]
            #mette i vari capturing group in phrase_pos
            phrase_pos.append((split[1], split[2], split[3], phrase_dict))

        pos_tagging.append(phrase_pos)

    return sentences, pos_tagging
