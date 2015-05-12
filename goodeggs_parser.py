from HTMLParser import HTMLParser


class ItemGridParser(HTMLParser):

  def __init__(self, html_string, *args, **kwargs):
    HTMLParser.__init__(self, *args, **kwargs)
    self.products = []
    HTMLParser.feed(self, html_string)

  @property
  def product_id_to_product_path(self):
    return dict(self.products)

  @property
  def product_ids(self):
    return [product[0] for product in self.products]

  def handle_starttag(self, tag, attrs):
    if tag == 'a':
      attrs = dict(attrs)
      class_values = attrs.get('class', '').split()
      if ['js-product-link'] == class_values:
        product_path = attrs['href']
        product_id = product_path.split('/')[-1]
        self.products.append((product_id, product_path))

  def feed(*args, **kwargs):
    raise NotImplementedError('ItemGridParser.feed')


class ProductPageParser(HTMLParser):

  READY = 0
  RECORD_DATA = 1
  RECORD_CATEGORIES = 2

  def __init__(self, html_string, *args, **kwargs):
    HTMLParser.__init__(self, *args, **kwargs)
    self.state = self.READY
    self.product_attributes = {
        'currency': 'USD',
        'categories': []
    }
    self.record_data_value = None
    HTMLParser.feed(self, html_string)

  def handle_starttag(self, tag, attrs):
    attrs = dict(attrs)
    class_values = attrs.get('class', '').split()

    if self.state == self.RECORD_CATEGORIES:
      if tag == 'a' and not class_values:
        # Examples: /sfbay/meat or /sfbay/meat/pork
        category = attrs['href'].strip('/').split('/')[1:]
        self.product_attributes['categories'].append(category)
      return

    if self.state == self.RECORD_DATA:
      return

    # self.state == self.READY
    if tag == 'h2' and 'producer-name' in class_values:
      self.state = self.RECORD_DATA
      self.record_data_value = 'producer_name'
    elif tag == 'h1' and 'product-name' in class_values:
      self.state = self.RECORD_DATA
      self.record_data_value = 'name'
    elif tag == 'div' and 'description-body' in class_values:
      self.state = self.RECORD_DATA
      self.record_data_value = 'description'
    elif tag == 'meta' and 'itemprop' in attrs:
      if attrs['itemprop'] == 'price':
        self.product_attributes['price'] = float(attrs['content'])
    elif tag =='div' and 'breadcrumbs' in class_values:
      self.state = self.RECORD_CATEGORIES

  def handle_endtag(self, tag):
    if self.state == self.RECORD_CATEGORIES and tag == 'div':
      self.state = self.READY

  def handle_data(self, data):
    if self.state == self.RECORD_DATA:
      self.product_attributes[self.record_data_value] = data
      self.state = self.READY
      self.record_data_value = None

  def feed(*args, **kwargs):
    raise NotImplementedError('ProductPageParser.feed')


def get_parser(url_pathname, html_string):
  if url_pathname.count('/') == 2:
    return ItemGridParser
  elif url_pathname.count('/') == 4:
    return ProductPageParser
  raise RuntimeError('get_parser: unexpected {}'.format(url_pathname))
