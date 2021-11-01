from urllib.parse import urljoin
from urllib.parse import urlparse

from lxml import html
from lxml.html.clean import Cleaner


class Sanitizer(Cleaner):
    def __init__(self, base_url=None):
        super().__init__(remove_tags=['a', 'img'], style=True)

        self.base_url = base_url

    def allow_element(self, el):
        if el.tag == 'a':
            self._make_absolute_url(el, 'href')
            return True
        elif el.tag == 'img':
            if el.get('width') == '1' and el.get('height') == '1':
                # Remove 1x1 image used most probably for user-tracking
                return False
            self._make_absolute_url(el, 'src')
            return True
        return super().allow_element(el)

    def _make_absolute_url(self, el, attr):
        old_url = el.get(attr)
        if old_url and not urlparse(old_url).netloc:
            new_url = urljoin(self.base_url, old_url)
            el.set(attr, new_url)

    def clean_html(self, content_html):
        return super().clean_html(content_html)


def sanitize_entry_content(content, base_url):
    if content is None:
        return None

    content_value = content['value']
    content_html = html.fragment_fromstring(content_value, create_parent='div')

    sanitizer = Sanitizer(base_url=base_url)

    sanitized_content_html = sanitizer.clean_html(content_html)
    sanitized_content_value = html.tostring(sanitized_content_html, encoding='unicode')

    return dict(
        type=content['type'],
        language=content['language'],
        value=sanitized_content_value,
    )
