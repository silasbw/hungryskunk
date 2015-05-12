#!/usr/bin/env python

import argparse
import logging
import os
import requests
import urlparse

import goodeggs_parser


log = logging.getLogger(__name__)


def main(args):
  query_string = ' '.join(args.query)
  search_url = 'https://www.goodeggs.com/sfbay/search?q=' + query_string
  result = requests.get(search_url)
  parsed_items = goodeggs_parser.ItemGridParser(result.text)
  for product_id, product_path in parsed_items.products[:args.max_results]:
    product_url = urlparse.urljoin('https://www.goodeggs.com/', product_path)
    product_result = requests.get(product_url)
    parsed_product = goodeggs_parser.ProductPageParser(product_result.text)
    print product_url, parsed_product.product_attributes


def process_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('query', nargs='+',
                      help='Directory to save crawl results')
  parser.add_argument('--max-results', default=5, type=int,
                      help='Maximum number of results to fetch')
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
