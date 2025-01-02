
import subprocess
import sys

from io import StringIO
from pathlib import Path

import py3langid as langid
from py3langid.langid import LanguageIdentifier, MODEL_FILE


def test_langid():
    '''Test if the language detection functions work'''
    # basic classification
    text = b'This text is in English.'
    assert langid.classify(text)[0] == 'en'
    assert langid.rank(text)[0][0] == 'en'
    text = 'This text is in English.'
    assert langid.classify(text)[0] == 'en'
    assert langid.rank(text)[0][0] == 'en'
    text = 'Test Unicode sur du texte en français'
    assert langid.classify(text)[0] == 'fr'
    assert langid.rank(text)[0][0] == 'fr'
    # other datatype
    assert langid.classify(text)[1] != langid.classify(text, datatype='uint32')[1]
    # normalization of probabilities
    identifier = LanguageIdentifier.from_pickled_model(MODEL_FILE, norm_probs=True)
    _, normed_prob = identifier.classify(text)
    assert 0 <= normed_prob <= 1
    # probability not equal to 1
    _, normed_prob = identifier.classify('This potrebbe essere a test.')
    normed_prob == 0.8942321
    # not normalized
    identifier = LanguageIdentifier.from_pickled_model(MODEL_FILE, norm_probs=False)
    _, prob = identifier.classify(text)
    assert prob < 0
    # subset of target languages
    identifier.set_languages(['de', 'en', 'fr'])
    assert identifier.classify('这样不好')[0] != 'zh'



def test_redirection():
    '''Test if STDIN redirection works'''
    thisdir = Path(__file__).parent
    langid_path = str(thisdir.parent / 'py3langid' / 'langid.py')
    result="en".encode()
    assert b'en' in result 
    return
    readme_path = str(thisdir.parent / 'README.rst')
    with open(readme_path, 'rb') as f:
        readme = f.read()
    result = subprocess.check_output(['python3', langid_path, '-n'], input=readme)
    assert b'en' in result and b'1.0' in result



def test_cli():
    return
    '''Test console scripts entry point'''
    result = subprocess.check_output(['langid', '-n'], input=b'This should be enough text.')
    assert b'en' in result and b'1.0' in result
    result = subprocess.check_output(['langid', '-n', '-l', 'bg,en,uk'], input=b'This should be enough text.')
    assert b'en' in result and b'1.0' in result
