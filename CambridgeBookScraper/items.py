# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class _CScrapeItem(scrapy.Item):
    title   = scrapy.Field()
    content = scrapy.Field()
    authors = scrapy.Field()
    publisher = scrapy.Field()
    source = scrapy.Field()
    chapter = scrapy.Field()
    published = scrapy.Field()
    published_online = scrapy.Field()
    doi = scrapy.Field()

class BookItem(_CScrapeItem):
    info     = scrapy.Field()
    subjects = scrapy.Field()
    isbn     =  scrapy.Field()

class ArticleItem(_CScrapeItem):
    pass
