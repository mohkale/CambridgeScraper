# -*- coding: utf-8 -*-
import re
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from ..items import BookItem, ArticleItem

import scrapy

class CambridgeSpider(scrapy.Spider):
    name = 'cambridge-spider'
    allowed_domains = ['www.cambridge.org']
    # start_urls = ['http://www.cambridge.org/']

    def __init__(self, url=None, *args, **kwargs):
        self.start_urls = [url] if url else []
        super().__init__(*args, **kwargs)

    def parse(self, response):
        url_attribs = urlparse(response.url)

        if url_attribs.path.startswith('/core/what-we-publish'):
            # on pagination page, iterate over every other page.
            # and iterate over every book on the page :P.
            last_page_elem = response.css('ul.pagination > li:last-child > a')

            if len(last_page_elem) != 0:
                # more then a single page exists
                query = parse_qs(url_attribs.query)
                query = {x: y[0] if isinstance(y, list) else y for x, y in query.items()}
                page_max = int(last_page_elem[0].attrib['data-page-number'])
                page_min = int(query.get('pageNum', 1))

                for page in range(page_min+1, page_max+1):
                    query['pageNum'] = page

                    yield scrapy.Request(
                        urlunparse((url_attribs.scheme, url_attribs.netloc,
                                    url_attribs.path, url_attribs.params,
                                    urlencode(query), url_attribs.fragment)),
                        callback=self._parse_contents,
                        dont_filter=True)

            yield from self._parse_contents(response)
        elif url_attribs.path.startswith('/core/books'):
            yield from self._parse_book_or_article(response)
        else:
            self.logger.warning('unknown URL path: ' + url_attribs.path)

    def _parse_contents(self, response):
        url_attribs = urlparse(response.url)

        for book_path in response.css('div.results div.row a.part-link::attr(href)').getall():
            yield scrapy.Request(
                urlunparse((url_attribs.scheme, url_attribs.netloc,
                            book_path, '', '', '')),
                callback=self._parse_book_or_article)

    def _parse_book_or_article(self, response):
        chapter = response.css('div.chapter')
        if len(chapter) != 0:
            # is just one article, that we can download.
            yield from self._parse_article(response, chapter)
        else:
            # is paginated and divided into multiple sub-books
            yield from self._parse_book(response)

    def _parse_book(self, response):
        url_attribs = urlparse(response.url)

        if 'item' not in response.meta:
            item = BookItem()
            response.meta['item'] = item
            item['title'] = response.css('h1[data-test-id=book-title]::text').get()

            info = response.css('li.meta-info::text').get()
            if info: info = info.strip()
            item['info'] = info

            item['authors'] = ''.join(response.css('li.author *::text').getall()).strip().split('\n')

            # WTF
            details = {
                x.css('span:first-child::text').get().rstrip(': ').lower():
                  ''.join(x.css('*::text').getall()[2:]).strip().split('\n')
                for x in response.css('div.details:not(.main-details) > ul > li') }
            item['published'] = details.get('print publication year', None)
            item['published_online'] = details.get('online publication date', None)
            item['isbn'] = details.get('online isbn', None)
            item['doi'] = details.get('doi', None)
            item['subjects'] = details.get('subjects', None)

            # iterate for all subpages for the current book
            max_page = response.css('ul.pagination > li:last-child > a::attr(data-page-number)')
            # WARN doesn't allow you to download a book starting from a different page to 1.
            if len(max_page) != 0:
                query = parse_qs(url_attribs.query)
                query = {x: y[0] if isinstance(y, list) else y for x, y in query.items()}

                for page in range(2, int(max_page.get())+1):
                    query['pageNum'] = page

                    yield scrapy.Request(
                        urlunparse((url_attribs.scheme, url_attribs.netloc,
                                    url_attribs.path, url_attribs.params,
                                    urlencode(query), url_attribs.fragment)),
                        callback=self._parse_book,
                        meta={'item': item},
                        dont_filter=True)

        for sub_chapter in response.css('.results-listing .overview'):
            item = response.meta['item'].deepcopy()
            view_elem = sub_chapter.css('a')
            chapter_title = view_elem.css('::text').get().strip()
            view_path = view_elem.css('::attr(href)').get()

            item['source'] = view_elem.css('.pages::text').get()
            if item['source']:
                item['source'] = item['source'].strip()
            item['title'] = '%s ((%s))' % (item['title'], chapter_title)
            item['chapter'] = chapter_title

            view_link, _ = self._parse_view_link(sub_chapter, url_attribs)
            if view_link is None:
                self.logger.error('unable to locate view path for page.')
                yield response.meta['item']
            else:
                yield self._make_body_request(view_link, response.url, meta={'item': item})

    def _parse_article(self, response, chapter):
        url_attribs = urlparse(response.url)
        book = ArticleItem()

        published = chapter.css('.details .published > .date::text').getall()
        book['published_online'] = published[1] if len(published) == 2 else None
        book['published'] = published[0]

        book['title'] = response.css('h1.article-title::text').get()

        overview = response.css('ul.overview')
        book['authors'] = ''.join(overview.css('li.author *::text').getall()).strip().split('\n')
        publisher = overview.css('li.publisher::text').get().strip()
        if publisher.lower().startswith('publisher:\n'):
            publisher = publisher[11:]
        book['publisher'] = publisher
        book['doi'] = overview.css('li.doi > a.doi::attr(href)').get()
        source = response.css('ul.overview > li.source')[-1]
        if source.attrib.get('class', None) != 'source':
            source = None
        if source:
            book['source'] = source.css('::text').get()

        view_link, referer = self._parse_view_link(response, url_attribs)
        if view_link is None:
            self.logger.error('unable to locate view path for page.')
            yield book
        else:
            yield self._make_body_request(view_link, referer, meta={'item': book})

    def _parse_view_link(self, response, url_attribs):
        view_id = None
        view_url = None
        for path in response.css('ul.file-actions, ul.links').css('a::attr(href)').getall():
            match = re.search('/core/product/(.+)/online-view', path)
            if match is not None:
                view_url = urlunparse((url_attribs.scheme, url_attribs.netloc,
                                       path, '', '', ''))
                view_id = 'https://www.cambridge.org/core/services/online-view/get/' + match[1]
                break
        return view_id, view_url

    # make body of book
    def _make_body_request(self, url, referer, **kwargs):
        return scrapy.Request(
            url,
            headers={
                'referer': referer,
                'accept': '*/*',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'no-cache',
                'pragma': 'no-cache',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'x-requested-with': 'XMLHttpRequest'
            },
            callback=self._parse_assign_body,
            **kwargs)

    def _parse_assign_body(self, response):
        response.meta['item']['content'] = response.text
        yield response.meta['item']
