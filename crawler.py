#!/usr/bin/env python

import argparse
import logging
import os

import goodeggs_crawler


log = logging.getLogger(__name__)

_SFBAY_PATHNAMES = (
    '/sfbay/bakery',
    '/sfbay/drinks',
    '/sfbay/snacks',
    '/sfbay/kitchen',
    '/sfbay/dairy',
    '/sfbay/produce',
    '/sfbay/meat',
    '/sfbay/floral',
)


def main(args):
  queue_path = os.path.join(args.destination, 'queue')
  result_path = os.path.join(args.destination, 'results')

  if args.init:
    os.mkdir(queue_path)
    os.mkdir(result_path)
    path_queue = goodeggs_crawler.PathQueue(queue_path)
    for path in _SFBAY_PATHNAMES:
      path_queue.push(path)

  if args.max_gets <= 0:
    return

  crawl_count = [0]

  def crawl_callback(url):
    crawl_count[0] += 1
    print crawl_count[0], url
    return crawl_count[0] < args.max_gets

  goodeggs_crawler.crawl(queue_path, result_path, callback=crawl_callback)


def process_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('destination',
                      help='Directory to save crawl results')
  parser.add_argument('--init', default=False, action='store_true',
                      help='Start a new crawl for sfbay')
  parser.add_argument('--max-gets', default=10, type=int,
                      help='Maximum number of HTTP GETs to execute')
  parser.add_argument('--debug',
                      action='store_true', default=False,
                      help='Display debug messages')
  args = parser.parse_args()
  if args.debug:
    log.setLevel(logging.DEBUG)
    logging.getLogger('root').setLevel(logging.DEBUG)
  return args


if __name__ == '__main__':
  main(process_args())
