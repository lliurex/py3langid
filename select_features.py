MAX_NGRAM_ORDER = 4
TOP_DOC_FREQ = 15000
FEATURES_PER_LANG = 300
PROCESS_COUNT = 32 

import numpy

import tempfile
import collections
import shutil
import os
import marshal


import collections
import marshal
import tempfile

class disklist(collections.Iterable, collections.Sized):
  """
  Disk-backed queue. Not to be used for object persistence.
  Items can be added to the queue, and the queue can be iterated,
  """
  def __init__(self, temp_dir=None):
    self.fileh = tempfile.TemporaryFile(dir=temp_dir)
    self.count = 0

  def __iter__(self):
    self.fileh.seek(0)
    while True:
      try:
        yield marshal.load(self.fileh)
      except (EOFError, ValueError, TypeError):
        break

  def __len__(self):
    return self.count

  def append(self, value):
    marshal.dump(value, self.fileh)
    self.count += 1


from itertools import tee, izip, repeat
class Tokenizer(object):
  def __init__(self, max_order):
    self.max_order = max_order

  def __call__(self, seq):
    max_order = self.max_order
    t = tee(seq, max_order)
    for i in xrange(max_order):
      for j in xrange(i):
        # advance iterators, ignoring result
        t[i].next()
    while True:
      token = tuple(tn.next() for tn in t)
      if len(token) < max_order: break
      for n in xrange(max_order):
        yield token[:n+1]
    for a in xrange(max_order-1):
      for b in xrange(1, max_order-a):
        yield token[a:a+b]

import multiprocessing as mp
from collections import defaultdict
class Enumerator(object):
  """
  Enumerator object. Returns a larger number each call. 
  Can be used with defaultdict to enumerate a sequence of items.
  """
  def __init__(self, start=0):
    self.n = start

  def __call__(self):
    retval = self.n
    self.n += 1
    return retval

def entropy(v, axis=0):
  """
  Optimized implementation of entropy. This version is faster than that in 
  scipy.stats.distributions, particularly over long vectors.
  """
  v = numpy.array(v, dtype='float')
  s = numpy.sum(v, axis=axis)
  with numpy.errstate(divide='ignore', invalid='ignore'):
    r = numpy.log(s) - numpy.nansum(v * numpy.log(v), axis=axis) / s
  return r


def split_info(arg):
  """
  Helper for the infogain class. This lives as its own top-level function
  to allow it to work with multiprocessing.
  """
  f_masks, class_map = arg
  num_inst = f_masks.shape[1]
  f_count = f_masks.sum(1) # sum across instances
  f_weight = f_count / float(num_inst) 
  f_entropy = numpy.empty((f_masks.shape[0], f_masks.shape[2]), dtype=float)
  # TODO: This is the main cost. See if this can be made faster. 
  for i, band in enumerate(f_masks):
    f_entropy[i] = entropy((class_map[:,None,:] * band[...,None]).sum(0), axis=-1)
  # nans are introduced by features that are entirely in a single band
  # We must redefine this to 0 as otherwise we may lose information about other bands.
  # TODO: Push this back into the definition of entropy?
  f_entropy[numpy.isnan(f_entropy)] = 0
  return (f_weight * f_entropy).sum(0) #sum across discrete bands



class InfoGain(object):
  def __init__(self, chunksize=50, num_process=None):
    self.chunksize = chunksize
    self.num_process = num_process if num_process else mp.cpu_count()
 
  def weight(self, feature_map, class_map):
    # Feature map should be a boolean map
    num_inst, num_feat = feature_map.shape

    # We can eliminate unused classes as they do not contribute to entropy
    class_map = class_map[:,class_map.sum(0) > 0]
    
    # Calculate  the entropy of the class distribution over all instances 
    H_P = entropy(class_map.sum(0))
      
    # unused features have 0 information gain, so we skip them
    nz_index = numpy.array(feature_map.sum(0).nonzero())[0]
    nz_fm = feature_map[:, nz_index]
    nz_num = len(nz_index)

    # compute the information gain of nonzero features
    pool = mp.Pool(self.num_process)
    def chunks():
      for chunkstart in range(0, nz_num, self.chunksize):
        chunkend = min(nz_num, chunkstart+self.chunksize)
        v = nz_fm[:,chunkstart:chunkend]
        nonzero = numpy.zeros(v.shape, dtype=bool)
        nonzero[v.nonzero()] = True
        zero = numpy.logical_not(nonzero)
        retval = numpy.concatenate((zero[None], nonzero[None]))
        yield (retval, class_map)
    x = pool.imap(split_info, chunks())
    nz_fw = H_P - numpy.hstack(x)

    # return 0 for unused features
    feature_weights = numpy.zeros(num_feat, dtype=float)
    feature_weights[nz_index] = nz_fw
    return feature_weights

def pass1(path):
  """
  Read a file on disk and return the set of types it contains.
  """
  extractor = Tokenizer(MAX_NGRAM_ORDER)
  with open(path) as f:
    retval = set(extractor(f.read()))
  return retval


if __name__ == "__main__":
  import os, sys
  target_dir = sys.argv[1]
  print "target dir: ", target_dir
  paths = []
  for dirpath, dirnames, filenames in os.walk(target_dir):
    for f in filenames:
      paths.append(os.path.join(dirpath, f))
  print "found %d files" % len(paths)


  # Initialize language and domain indexers
  lang_index = defaultdict(Enumerator())
  domain_index = defaultdict(Enumerator())
  doc_keys = []

  # Index the paths
  for path in paths:
    # split the path into identifying components
    path, docname = os.path.split(path)
    path, lang = os.path.split(path)
    path, domain = os.path.split(path)

    # obtain a unique key for the file
    key = domain,lang,docname
    doc_keys.append(key)

    # index the language and the domain
    lang_id = lang_index[lang]
    domain_id = domain_index[domain]

  print "langs:", lang_index.keys()
  print "domains:", domain_index.keys()

  # First pass: Construct candidate set of types
  def get_paths():
    for i,p in enumerate(paths):
      if i % 100 == 0:
        print "%d..." % i
      yield p

  pool = mp.Pool(PROCESS_COUNT)

  termsets = pool.imap(pass1, get_paths())
  doc_count = defaultdict(int)
  term_index = defaultdict(Enumerator())
  doc_reprs = disklist() # list of lists of termid-count pairs
  for termset in termsets:
    doc_repr = set()
    for term in termset:
      doc_count[term] += 1
      doc_repr.add(term_index[term])
    doc_reprs.append(doc_repr)
  pool.close()
  print "first pass complete"

  # Work out the set of features to compute IG
  candidate_features = set()
  for i in range(1, MAX_NGRAM_ORDER+1):
    d = dict( (k, doc_count[k]) for k in doc_count if len(k) == i)
    candidate_features |= set(sorted(d, key=d.get, reverse=True)[:TOP_DOC_FREQ])
  candidate_features = sorted(candidate_features)
  print "candidate features: ", len(candidate_features)

  # Compute indices of features to retain
  feats = tuple(term_index[f] for f in candidate_features)

  # Initialize feature and class maps 
  num_instances = len(doc_keys)
  feature_map = numpy.zeros((num_instances, len(candidate_features)), dtype='bool')
  cm_domain = numpy.zeros((num_instances, len(domain_index)), dtype='bool')
  cm_lang = numpy.zeros((num_instances, len(lang_index)), dtype='bool')

  # Populate the feature map
  for docid, doc_repr in enumerate(doc_reprs):
    for featid, termid in enumerate(feats):
      feature_map[docid, featid] = termid in doc_repr

  # Populate the class maps
  for docid, (domain, lang, docname) in enumerate(doc_keys):
    cm_domain[docid, domain_index[domain]] = True
    cm_lang[docid, lang_index[lang]] = True

  print "computing information gain"
  # Compute the information gain WRT domains and binary for each language
  ig = InfoGain(num_process=PROCESS_COUNT)
  w_domain = ig.weight(feature_map, cm_domain)
  w_lang = dict()
  for lang in lang_index:
    print "infogain: ", lang
    pos = cm_lang[:, lang_index[lang]]
    neg = numpy.logical_not(pos)
    cm = numpy.hstack((neg[:,None], pos[:,None]))
    w_lang[lang] = ig.weight(feature_map, cm)

  # Compute LD weights and obtain a final feature set
  final_feature_set = set()
  for lang in w_lang:
    ld_w = dict(zip(candidate_features, w_lang[lang] - w_domain))
    final_feature_set |= set(sorted(ld_w, key=ld_w.get, reverse=True)[:FEATURES_PER_LANG])

  # Output
  print "selected %d features" % len(final_feature_set)
  with open('weights','w') as f:
    for feat in final_feature_set:
      print >>f, repr(''.join(feat))

  #TODO: Build a nice optparse interface
    
