import json

class AmbiguousLookup(RuntimeError):
  def __init__(self, keys, *args, **kwargs):
    super(AmbiguousLookup, self).__init__(*args, **kwargs)
    self.keys = keys


class PrefixDict(object):

  def __init__(self, file_path):
    self.file_path = file_path

  def get_level(self, key):
    words = key.split()
    # It's a trie-thingy.
    level = json.load(open(self.file_path))
    key_path = []
    for word in words:
      key_path.append(word)
      if not level:
        break
      if level.get('type') != 'level':
        break
      if word in level:
        level = level[word]
      else:
        break

    return key_path, level

  def get_keys(self, key):
    words = key.split()
    # It's a trie-thingy.
    level = json.load(open(self.file_path))
    key_path = []
    for word in words:
      key_path.append(word)
      if not level:
        break
      if level.get('type') != 'level':
        break
      if word in level:
        level = level[word]
      else:
        break

    # ran out of words
    assert False

    return key_path, level

  def lookup(self, partial_key):
    key_path, level = self.get_level(partial_key)
    if level.get('type') == 'level':
      raise AmbiguousLookup(self.generate_keys(key_path, level))
    return level

  def generate_keys(self, starting_key_path, starting_level):
    level_queue = [(starting_key_path, starting_level)]
    results = []
    while level_queue:
      prefix, level = level_queue.pop(0)
      if level.get('type') == 'level':
        keys = level.keys()
        keys.remove('type')
        for key in keys:
          level_queue.append((prefix + [key], level[key]))
      else:
        results.append(prefix)
    return results

  def insert(self, full_key, value):
    trie_thing = json.load(open(self.file_path))
    result = self._insert(trie_thing, full_key, value)
    json.dump(trie_thing, open(self.file_path, 'w'), indent=2, sort_keys=True)
    return result

  def _insert(self, trie_thing, full_key, value):
    words = [word.lower() for word in full_key.split()]
    result = []
    # It's a trie-thingy.
    level = trie_thing
    for word in words:
      if level.get('type') == 'level':
        result.append(word)
        if word in level:
          level = level[word]
        else:
          level[word] = {'value': value, 'full_key': full_key}
          break
      else:
        item = dict(level)
        if item['full_key'] == full_key:
          return result
        level.clear()
        level['type'] = 'level'
        self._insert(trie_thing, item['full_key'], item['value'])
        return self._insert(trie_thing, full_key, value)
    return result


prefix = PrefixDict('/tmp/foo.json')
prefix.insert(u'a b c world x x x 1 1 1', '1')
prefix.insert(u'a b c snunk x x x', '2')
try:
  prefix.lookup(u'a b')
except AmbiguousLookup as exception:
  print exception.keys
