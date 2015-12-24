"""Interface for extracting Kindle Library data from Kindle Cloud Reader."""
from . import api

from textwrap import dedent
from contextlib import contextmanager

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import PhantomJS
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.wait import WebDriverWait


class Error(Exception):
  """Base Lector error."""


class APIError(Error):
  """Indicates an error executing an API call."""


class ConnectionError(Error):
  """Indicates an error connecting to a webpage."""


class LoginError(Error):
  """Indicates an error logging into Kindle Cloud Reader."""


class BrowserError(Error):
  """Indicates a problem with the browser."""


class KindleBook(object):
  """A Kindle Book.

  Args:
    asin: The "Amazon Standard Item Number" of the book. Essentially a
        UUID for Kindle books.
    title: The book title
    authors: An iterable of the book's authors.
  """

  def __init__(self, asin, title, authors=()):
    self.asin = unicode(asin)
    self.title = unicode(title)
    self.authors = tuple(unicode(author) for author in authors)

  def __str__(self):
    if not self.authors:
      ret = u'"{}"'.format(self.title)
    elif len(self.authors) == 1:
      ret = u'"{}" by {}'.format(self.title, self.authors[0])
    elif len(self.authors) == 2:
      ret = u'"{}" by {} and {}'.format(
          self.title, self.authors[0], self.authors[1])
    else:
      ret = u'"{}" by {}, and {}'.format(
          self.title, u', '.join(self.authors[:-1]), self.authors[-1])
    return ret.encode('utf8')

  def __repr__(self):
    author_str = u', '.join(u'"%s"' % author for author in self.authors)
    return (u'Book(asin={}, title="{}", authors=[{}])'
            .format(self.asin, self.title, author_str)
            .encode('utf8'))


class ReadingProgress(object):
  """Represents a reader's progress through a KindleBook.

  Args:
    positions: A 3-tuple (start_position, current_position, end_position)
    locs: A 3-tuple (start_location, current_location, end_location)
    page_nums (optional): A 3-tuple (start_page, current_page, end_page)

  Notes on Progress Formats:

  Page Numbers:
    The page number measurement directly corresponds to the page
    numbers in a physical copy of the book. In other words, the page
    number N reported by the Kindle should correspond to that same
    page N in a hard copy.

  Locations:
    According to (http://www.amazon.com/forum/kindle/Tx2S4K44LSXEWRI)
    and various other online discussions, a single 'location' is
    equivalent to 128 bytes of code (in the azw3 file format).

    For normal books, this ranges from 3-4 locations per Kindle page with
    a large font to ~16 locs/Kpg with a small font. However, book elements
    such as images or charts may require many more bytes and, thus,
    locations to represent.

    In spite of this extra noise, locations provide a more granular
    measurement of reading progress than page numbers.

    Additionally, locations are available on every Kindle title while
    page numbers are frequently absent from Kindle metadata.

  Positions:
    Positions are the representation used to represent reading progress in
    the Kindle service. As such, it is the most granular measure
    available. I was unable to find any documentation on their meaning but
    the formulae found in the code indicate the equivalence between
    positions and locations is something like 150 to 1.
  """

  def __init__(self, positions, locs, page_nums=None):
    self.positions = tuple(positions)
    self.locs = tuple(locs)
    self.page_nums = tuple(page_nums) if page_nums is not None else None

  def has_page_progress(self):
    """Returns whether page numbering data is available."""

    return self.page_nums is not None

  def __eq__(self, other):
    return (self.positions == other.positions and
            self.locs == other.locs and
            self.page_nums == other.page_nums)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __gt__(self, other):
    return (self.positions[1] > other.positions[1] and
            self.locs[1] > other.locs[1] and
            self.page_nums[1] > other.page_nums[1])

  def __lt__(self, other):
    return (self.positions[1] < other.positions[1] and
            self.locs[1] < other.locs[1] and
            self.page_nums[1] < other.page_nums[1])

  def __str__(self):
    if self.has_page_progress():
      return 'Page %d of %d' % (self.page_nums[1], self.page_nums[2])
    else:
      return 'Location %d of %d' % (self.locs[1], self.locs[2])

  def __repr__(self):
    if self.has_page_progress():
      return ('ReadingProgress(Loc=(%d of %d), Page=(%d of %d))' %
              (self.locs[1], self.locs[2],
               self.page_nums[1], self.page_nums[2]))
    else:
      return 'ReadingProgress(Loc=(%d of %d))' % (self.locs[1], self.locs[2])


class _KindleCloudReaderBrowser(PhantomJS):
  """A selenium webdriver wrapper for interacting with Kindle Cloud Reader.

  Args:
    username: The email address associated with the Kindle account.
    password: The password associated with the Kindle account.
    user_agent: The user agent to be used for the browser.
  """

  _CLOUD_READER_URL = u'https://read.amazon.com'
  _SIGNIN_URL = u'https://www.amazon.com/ap/signin'
  _USER_AGENT = (
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) '
      'AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/44.0.2403.155 Safari/537.36')

  def __init__(self, username, password, user_agent=_USER_AGENT):
    # Kindle Cloud Reader does not broadcast support for PhantomJS
    # This is easily circumvented by modifying the User Agent
    dcap = DesiredCapabilities.PHANTOMJS.copy()
    dcap['phantomjs.page.settings.userAgent'] = user_agent

    super(_KindleCloudReaderBrowser, self).__init__(
        desired_capabilities=dcap, service_args=['--disk-cache=false'])

    self.set_window_size(1920, 1080)
    self.set_script_timeout(5)

    self._uname = username
    self._pword = password

    self._init_browser()

  def _wait(self, timeout=10):
    """Returns a `WebDriverWait` instance set to `timeout` seconds."""

    return WebDriverWait(self, timeout=timeout)

  def _init_browser(self):
    """Initializes a browser and navigates to the KCR reader page."""

    self._to_reader_home()
    self._to_reader_frame()
    self._wait_for_js()

  def _create_browser(self):
    """Creates a new instance of the selenium driver."""

  def _to_reader_home(self):
    """Navigate to the Cloud Reader library page.

    Raises:
      BrowserError: If the KCR homepage could not be loaded.
      ConnectionError: If there was a connection error.
    """
    # NOTE: Prevents QueryInterface error caused by getting a URL
    # while switched to an iframe
    self.switch_to_default_content()
    self.get(_KindleCloudReaderBrowser._CLOUD_READER_URL)

    if self.title == u'Problem loading page':
      raise ConnectionError

    # Wait for either the login page or the reader to load
    login_or_reader_loaded = lambda br: (
        br.find_elements_by_id('amzn_kcr') or
        br.find_elements_by_id('KindleLibraryIFrame'))
    self._wait(5).until(login_or_reader_loaded)

    try:
      self._wait(5).until(lambda br: br.title == u'Amazon.com Sign In')
    except TimeoutException:
      raise BrowserError('Failed to load Kindle Cloud Reader.')
    else:
      self._login()

  def _login(self, max_tries=2):
    """Logs in to Kindle Cloud Reader.

    Args:
      max_tries: The maximum number of login attempts that will be made.

    Raises:
      BrowserError: If method called when browser not at a signin URL.
      LoginError: If login unsuccessful after `max_tries` attempts.
    """

    if not self.current_url.startswith(_KindleCloudReaderBrowser._SIGNIN_URL):
      raise BrowserError(
          'Current url "%s" is not a signin url ("%s")' %
          (self.current_url, _KindleCloudReaderBrowser._SIGNIN_URL))

    email_field_loaded = lambda br: br.find_elements_by_id('ap_email')
    self._wait().until(email_field_loaded)
    tries = 0
    while tries < max_tries:
      # Enter the username
      email_elem = self.find_element_by_id('ap_email')
      email_elem.clear()
      email_elem.send_keys(self._uname)

      # Enter the password
      pword_elem = self.find_element_by_id('ap_password')
      pword_elem.clear()
      pword_elem.send_keys(self._pword)

      def creds_entered(_):
        """Returns whether the credentials were properly entered."""

        email_ok = email_elem.get_attribute('value') == self._uname
        pword_ok = pword_elem.get_attribute('value') == self._pword
        return email_ok and pword_ok

      kcr_page_loaded = lambda br: br.title == u'Kindle Cloud Reader'
      try:
        self._wait(5).until(creds_entered)
        self.find_element_by_id('signInSubmit-input').click()
        self._wait(5).until(kcr_page_loaded)
      except TimeoutException:
        tries += 1
      else:
        return

    raise LoginError

  def _to_reader_frame(self):
    """Navigate to the KindleReader iframe."""

    reader_frame = 'KindleReaderIFrame'
    frame_loaded = lambda br: br.find_elements_by_id(reader_frame)
    self._wait().until(frame_loaded)

    self.switch_to.frame(reader_frame)  # pylint: disable=no-member

    reader_loaded = lambda br: br.find_elements_by_id('kindleReader_header')
    self._wait().until(reader_loaded)

  def _wait_for_js(self):
    """Wait for the Kindle Cloud Reader JS modules to initialize.

    These modules provide the interface used to execute API queries.
    """
    # Wait for the Module Manager to load
    mod_mgr_script = ur"return window.hasOwnProperty('KindleModuleManager');"
    mod_mgr_loaded = lambda br: br.execute_script(mod_mgr_script)
    self._wait(5).until(mod_mgr_loaded)

    # Wait for the DB Client to load
    db_client_script = dedent(ur"""
        var done = arguments[0];
        if (!window.hasOwnProperty('KindleModuleManager') ||
            !KindleModuleManager
                .isModuleInitialized(Kindle.MODULE.DB_CLIENT)) {
           done(false);
        } else {
            KindleModuleManager
                .getModuleSync(Kindle.MODULE.DB_CLIENT)
                .getAppDb()
                .getAllBooks()
                .done(function(books) { done(!!books.length); });
        }
        """)
    db_client_loaded = lambda br: br.execute_async_script(db_client_script)
    self._wait(5).until(db_client_loaded)


class KindleCloudReaderAPI(object):
  """Provides an interface for accessing Kindle Cloud Reader data.

  Args:
    username: The email address associated with the Kindle account.
    password: The password associated with the Kindle account.
  """

  def __init__(self, username, password):
    self._browser = _KindleCloudReaderBrowser(username, password)

  def _get_api_call(self, function_name, *args):
    """Runs an api call with javascript-formatted arguments.

    Args:
      function_name: The name of the KindleAPI call to run.
      *args: Javascript-formatted arguments to pass to the API call.

    Returns:
      The result of the API call.

    Raises:
      APIError: If the API call fails or times out.
    """
    api_call = dedent("""
        var done = arguments[0];
        KindleAPI.%(api_call)s(%(args)s).always(function(a) {
            done(a);
        });
    """) % {
        'api_call': function_name,
        'args': ', '.join(args)
    }
    script = '\n'.join((api.API_SCRIPT, api_call))
    try:
      return self._browser.execute_async_script(script)
    except TimeoutException:
      # FIXME: KCR will occassionally not load library and fall over
      raise APIError

  @staticmethod
  def _kbm_to_book(kbm):
    """Converts a KindleBookMetadata object to a `KindleBook` instance.

    KindleBookMetadata is the Javascript object used by Kindle Cloud Reader to
    represent book metadata.

    Args:
      kbm: A KindleBookMetadata object.

    Returns:
      A KindleBook instance corresponding to the KindleBookMetadata param.
    """
    return KindleBook(**kbm)  # pylint: disable=star-args

  @staticmethod
  def _kbp_to_progress(kbp):
    """Converts a KindleBookProgress object to a `ReadingProgress` instance.

    KindleBookProgress is the Javascript object used by Kindle Cloud Reader to
    represent reading progress.

    Args:
      kbp: A KindleBookProgress object.

    Returns:
      A ReadingProgress instance constructed using the KindleBookMetadata param.
    """
    return ReadingProgress(**kbp)  # pylint: disable=star-args

  def get_book_metadata(self, asin):
    """Returns a book's metadata.

    Args:
      asin: The ASIN of the book to be queried.

    Returns:
      A `KindleBook` instance corresponding to the book associated with
      `asin`.
    """
    kbm = self._get_api_call('get_book_metadata', '"%s"' % asin)
    return KindleCloudReaderAPI._kbm_to_book(kbm)

  def get_library_metadata(self):
    """Returns the metadata on all books in the kindle library.

    Returns:
      A list of `KindleBook` instances corresponding to the books in the
      current user's library.
    """
    return map(KindleCloudReaderAPI._kbm_to_book,
               self._get_api_call('get_library_metadata'))

  def get_book_progress(self, asin):
    """Returns the progress data available for a book.

    NOTE: A summary of the two progress formats can be found in the
    docstring for `ReadingProgress`.

    Args:
      asin: The asin of the book to be queried.

    Returns:
      A `ReadingProgress` instance corresponding to the book associated with
      `asin`.
    """
    kbp = self._get_api_call('get_book_progress', '"%s"' % asin)
    return KindleCloudReaderAPI._kbp_to_progress(kbp)

  def get_library_progress(self):
    """Returns the reading progress for all books in the kindle library.

    Returns:
      A mapping of ASINs to `ReadingProgress` instances corresponding to the
      books in the current user's library.
    """
    kbp_dict = self._get_api_call('get_library_progress')
    return {asin: KindleCloudReaderAPI._kbp_to_progress(kbp)
            for asin, kbp in kbp_dict.iteritems()}

  def close(self):
    """End the browser session."""
    self._browser.quit()

  @staticmethod
  @contextmanager
  def get_instance(*args, **kwargs):
    """Context manager for an instance of `KindleCloudReaderAPI`."""

    inst = KindleCloudReaderAPI(*args, **kwargs)
    try:
      yield inst
    except Exception:
      raise
    finally:
      inst.close()
