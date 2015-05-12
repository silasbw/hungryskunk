import fcntl
import os
import requests
import urlparse

import goodeggs_parser


class PathQueue(object):

  def __init__(self, queue_directory_path):
    self.queue_directory_path = queue_directory_path

  def _ordered_listdir(self):
    file_names = os.listdir(self.queue_directory_path)

    def get_mtime(file_name):
      file_path = os.path.join(self.queue_directory_path, file_name)
      stat_results = os.stat(file_path)
      return stat_results.st_mtime

    return sorted(file_names, key=get_mtime)

  def pop(self):
    file_names = self._ordered_listdir()
    for file_name in file_names:
      file_path = os.path.join(self.queue_directory_path, file_name)
      try:
        open_mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        fd = os.open(file_path, open_mode)
        try:
          fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
          os.close(fd)
        else:
          os.close(fd)
          return file_name.replace('__', '/')
      except OSError:
        pass
    return None

  def push(self, path):
    file_name = path.replace('/', '__')
    file_path = os.path.join(self.queue_directory_path, file_name)
    with open(file_path, 'a'):
      os.utime(file_path, None)

  def acknowledge(self, path):
    file_name = path.replace('/', '__')
    file_path = os.path.join(self.queue_directory_path, file_name)
    os.remove(file_path)


class FileResults(object):

  def __init__(self, result_directory_path):
    self.results = []
    file_names = os.listdir(result_directory_path)
    for file_name in file_names:
      file_path = os.path.join(result_directory_path, file_name)
      url_pathname = file_name.replace('__', '/')
      self.results.append(
          {'file_path': file_path, 'url_pathname': url_pathname})


def crawl(queue_path, result_path, callback=None):
  path_queue = PathQueue(queue_path)

  while True:
    path = path_queue.pop()
    if not path:
      break
    url = urlparse.urljoin('https://www.goodeggs.com', path)
    result = requests.get(url)
    result_file_path = os.path.join(result_path, path.replace('/', '__'))
    with open(result_file_path, 'w') as result_file:
      result_file.write(result.text.encode('utf-8'))
      parser = goodeggs_parser.ItemGridParser(result.text)
      for product_path in parser.product_id_to_product_path.values():
        file_name = product_path.replace('/', '__')
        result_file_path = os.path.join(result_path, file_name)
        if not os.path.isfile(result_file_path):
          path_queue.push(product_path)

    path_queue.acknowledge(path)
    if callback and not callback(url):
      break
