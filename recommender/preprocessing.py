import contractions
import nltk
import string
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)

def expand_words(text):
    return contractions.fix(text)

def remove_punctuations(text):
    spaced_punc = "!#$%'&\()*+,-./:;<=>?@[\\]^_`{|}~…"
    non_spaced_punc = "'\'\""
    text = text.translate(str.maketrans(spaced_punc, ' ' * len(spaced_punc)))
    text = text.translate(str.maketrans('', '', non_spaced_punc))
    return ' '.join(text.split())

def remove_stopwords(text):
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    return ' '.join(word for word in tokens if word.lower() not in stop_words)

def clean_data(text):
    text = remove_punctuations(text)
    text = remove_stopwords(text)
    return text.lower()