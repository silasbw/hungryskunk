#!/usr/bin/env python

import argparse
import logging
import os

import goodeggs_crawler
import goodeggs_parser


log = logging.getLogger(__name__)


def main(args):
  result_directory_path = os.path.join(args.destination, 'results')
  result_files = goodeggs_crawler.FileResults(result_directory_path)
  for result_file in result_files.results:
    html_string = open(result_file['file_path']).read()
    parser = goodeggs_parser.get_parser(
        result_file['url_pathname'], html_string)
    if parser is goodeggs_parser.ProductPageParser:
      product_parse = parser(html_string)
      print product_parse.product_attributes


def process_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('destination',
                      help='Directory to save crawl results')
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
