#!/usr/bin/env python

import argparse
import datetime
import json
import logging
import os
import re
import requests
from slackclient import SlackClient
import urlparse
import time

import goodeggs_parser


log = logging.getLogger(__name__)


class ProductRequestLog(object):

  def __init__(self, file_name, *args, **kwargs):
    super(ProductRequestLog, self).__init__(*args, **kwargs)
    self.file_name = file_name

  @property
  def products(self):
    return json.load(open(self.file_name))

  def append(self, product, user_name):
    print product, user_name
    product_id = product['id']
    product_log = json.load(open(self.file_name))
    if product_id not in product_log:
      product_log[product_id] = dict(product)
      product_log[product_id]['requests'] = []
    timestamp = datetime.datetime.now().isoformat()
    product_log[product_id]['requests'].append(
        {'user_name': user_name, 'timestamp': timestamp})
    json.dump(product_log, open(self.file_name, 'w'), indent=2, sort_keys=True)

  def get_unique_requests(self, product_id):
    product_log = json.load(open(self.file_name))
    if product_id in product_log:
      requests = product_log[product_id]['requests']
      unique_requests = {request['user_name'] for request in requests}
      return len(unique_requests)
    return 0


class UserCommandLog(object):

  def __init__(self, file_path):
    self.file_path = file_path

  def append(self, message, command, result):
    try:
      command_log = json.load(open(self.file_path))
    except IOError:
      command_log = []
    command_log.append({'message': message,
                        'command': command,
                        'result': result})
    json.dump(
        command_log, open(self.file_path, 'w'), indent=2, sort_keys=True)

  @property
  def log(self):
    return json.load(open(self.file_path))

  def get_command_log(self, command):
    return [record for record in self.log if record['command'] == command]


def get_product_dict(product_path):
  product_url = urlparse.urljoin('https://www.goodeggs.com/', product_path)
  product_result = requests.get(product_url)
  parsed_product = goodeggs_parser.ProductPageParser(product_result.text)
  product = dict(parsed_product.product_attributes)
  product['id'] = product_path.split('/')[-1]
  product['url'] = product_url
  return product


class BotError(RuntimeError):
  pass


class Bot(object):

  def __init__(self, request_log, user_history_directory, max_suggestions=5):
    self.request_log = request_log
    self.user_history_directory = user_history_directory
    self.max_suggestions = max_suggestions

  def _handle_request(self, message, user_name):
    """`request suggestion-number` or `request product-url`: request a product."""

    pieces = message.split(' ')
    request = ' '.join(pieces[1:])
    try:
      suggest_index = int(request) - 1
      if suggest_index < 0:
        raise ValueError(request)
      command_log = UserCommandLog(
          os.path.join(self.user_history_directory, user_name + '.json'))
      suggestion_history = command_log.get_command_log('suggest')
      try:
        product_summary = suggestion_history[-1]['result'][suggest_index]
      except IndexError:
        raise ValueError(request)
    except ValueError:
      match = re.match(r'.*(/[^/]+/[^/]+/[^/]+/[^/]+).*', request)
      if not match:
        raise BotError('Invalid request {}'.format(request))
      product_path = match.group(1)
    else:
      product_path = product_summary['url']

    product = get_product_dict(product_path)
    self.request_log.append(product, user_name)
    print 'request', product_path
    return 'request', product_path

  def _handle_show(self, message, user_name, max_show=10):
    """`show`: show the requests with the most unique requests."""

    def unique_requests(product):
      unique_requests = {
          request['user_name'] for request in product['requests']}
      return len(unique_requests)
    products = sorted(
        self.request_log.products.values(), key=unique_requests, reverse=True)
    results = [{'name': product['name'],
                'url': product['url'],
                'request_count': unique_requests(product)}
               for product in products]
    print 'show', results[:max_show]
    return 'show', results[:max_show]

  def _handle_suggest(self, message, user_name):
    """`suggest search-query`: show suggestions based on `search-query`."""

    query_string = ' '.join(message.split(' ')[1:])
    if not query_string:
      raise BotError('Missing query')
    search_url = 'https://www.goodeggs.com/sfbay/search?q=' + query_string
    result = requests.get(search_url)
    parsed_items = goodeggs_parser.ItemGridParser(result.text)
    sorted_paths = []
    remaining_product_ids = parsed_items.product_ids
    for product_id in parsed_items.product_ids:
      request_count = self.request_log.get_unique_requests(product_id)
      if request_count:
        sorted_paths.append({
            'path': parsed_items.product_id_to_product_path[product_id],
            'request_count': request_count})
        remaining_product_ids.remove(product_id)
    sorted_paths = sorted_paths + [{
        'path': parsed_items.product_id_to_product_path[product_id],
        'request_count': 0} for product_id in remaining_product_ids]
    sorted_paths = sorted_paths[:self.max_suggestions]
    suggestions = []
    for sorted_path in sorted_paths:
      product = get_product_dict(sorted_path['path'])
      suggestions.append({
          'name': product['name'],
          'url': product['url'],
          'request_count': sorted_path['request_count']})
    command_log = UserCommandLog(
        os.path.join(self.user_history_directory, user_name + '.json'))
    command_log.append(message, 'suggest', suggestions)
    print 'suggest', suggestions
    return 'suggest', suggestions

  def _handle_help(self, message, user_name):
    """`help`: show help."""

    handler_function_name = [
        attribute for attribute in dir(self)
        if attribute.startswith('_handle_')]
    result = []
    for function_name in handler_function_name:
      function = getattr(self, function_name)
      if function.__doc__:
        result.append(function.__doc__)
    print 'help', result
    return 'help', result


  def handle_message(self, message, user_name):
    message = message.strip()
    command = message.split(' ', 1)[0]

    handler = getattr(self, '_handle_' + command, None)
    if handler:
      return handler(message, user_name)
    return None, None




import slacker

class SlackBot(object):

  def __init__(self, token, channel_id):
    self.token = token
    self.channel_id = channel_id
    # https://github.com/os/slacker/blob/master/slacker/__init__.py
    self._web_client = slacker.Slacker(token)
    # https://github.com/slackhq/python-slackclient
    self._rtm_client = SlackClient(token)
    assert self._rtm_client.rtm_connect()

  def poll(self):
    messages = []
    rtm_messages = self._rtm_client.rtm_read()
    for rtm_message in rtm_messages:
      if rtm_message['type'] != 'message':
        continue
      if rtm_message['channel'] == self.channel_id:
        message_text = rtm_message['text']
        message_text = message_text.strip()
        if '@hungry' not in message_text:
          continue
        bot_message = message_text.split('@hungry')[-1].strip()
        if not bot_message:
          continue

        user = self._web_client.users.info(rtm_message['user']).body
        if not user['ok']:
          raise SlackBotError(user)
        messages.append({
            'message': bot_message,
            'user': user['user']})
    return messages

  def handle_response(self, message, response_type, response):
    if response_type == 'help':
      reply = 'Here to help @{}!\n'.format(message['user']['name'])
      self.post_message(reply + '\n'.join(response))
    elif response_type == 'show':
      product_blurbs = []
      for index, product in enumerate(response):
        votes = product['request_count']      
        if votes == 1:
          vote_string = '{} vote'.format(votes)
        else:
          vote_string = '{} votes'.format(votes)
        blurb = '{number} - <{url}|{name}> ({votes})'.format(
              number=index + 1,
              url=product['url'],
              name=product['name'],
              votes=vote_string)
        product_blurbs.append(blurb)
      reply = 'The top requests so far:\n'
      self.post_message(reply + '\n'.join(product_blurbs))
    elif response_type == 'request':
      self.post_message(response)
    elif response_type == 'suggest':
      product_blurbs = []
      for index, product in enumerate(response):
        votes = product['request_count']      
        if votes == 1:
          vote_string = '{} vote'.format(votes)
        else:
          vote_string = '{} votes'.format(votes)
        blurb = '{number} - <{url}|{name}> ({votes})'.format(
              number=index + 1,
              url=product['url'],
              name=product['name'],
              votes=vote_string)
        product_blurbs.append(blurb)
      reply = 'Here are some suggestions:\n'
      self.post_message(reply + '\n'.join(product_blurbs))
      

  def post_message(self, message):
    self._web_client.chat.post_message(
        self.channel_id, message)


def main(args):
  user_history_directory = 'test0'
  request_log = ProductRequestLog('test0/log.json')
  bot = Bot(request_log, user_history_directory)
  slack_bot = SlackBot(args.token, args.channel_id)
  while True:
    messages = slack_bot.poll()
    if messages:
      for message in messages:
        try:
          response_type, response = bot.handle_message(
              message['message'], message['user']['name'])
        except BotError as error:
          log.warn('Oops', exc_info=True)
          continue
        if not response_type:
          continue
        slack_bot.handle_response(message, response_type, response)
    else:
      time.sleep(1)

  return

  # Command-line test bot..
  bot = Bot(request_log, user_history_directory)
  user_name = 'sbw'

  while True:
    message = raw_input('> ')
    bot.handle_message(message, user_name)


def process_args():
  parser = argparse.ArgumentParser()
  parser.add_argument('--token', required=True,
                      help='Slack token')
  parser.add_argument('--channel-id', required=True,
                      help='Channel ID (e.g., C04QNCB0X')
  parser.add_argument('--debug',
                      action='store_true', default=False,
                      help='Display debug messages')
  args = parser.parse_args()
  if args.debug:
    log.setLevel(logging.DEBUG)
    logging.getLogger('root').setLevel(logging.DEBUG)
  return args


if __name__ == '__main__':
  logging.basicConfig()
  main(process_args())
