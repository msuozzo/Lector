# Lector
An API for your Kindle data.

Python bindings are provided but any language that can run the JavaScript
found in `api.py` from within a Kindle Cloud Reader session may easily access
this data.

### Dependencies
**PhantomJS**:

* macOS (Homebrew)
    * ```brew install --cask phantomjs```
* Ubuntu (at least 14.04)
    * Guide provided and maintained by @julionc
      [here](https://gist.github.com/julionc/7476620)

### Usage
```python
import lector

api = lector.KindleCloudReaderAPI('my_amazon_username', 'my_amazon_password')
my_library = api.get_library_metadata()
book = my_library[0]
book_progress = api.get_book_progress(book.asin)
_, current_page, last_page = book_progress.page_nums

print 'Currently reading %s (Page %d of %d)' % (book.title, current_page, last_page)
```
