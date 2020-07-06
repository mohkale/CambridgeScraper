# Cambridge Book Scraper

In April of 2020, Cambridge University [released][source] all of their textbooks for
free on their site. This is the ~~quick and dirty~~ scrapy project I setup download
all of those books :grin:.

I've uploaded it here for educational purposes.

[scrapy]: https://scrapy.org/
[source]: https://www.reddit.com/r/worldnews/comments/fksiiw/all_cambridge_university_textbooks_are_free_in/

## Usage
```shell
scrapy crawl cambridge-spider -a url='URL'
```

The index url I was using was
`https://www.cambridge.org/core/what-we-publish/textbooks/listing?aggs[productSubject][filters]=A57E10708F64FB69CE78C81A5C2A6555`,
but any valid index page should work with the spider. For a list of available
subdindexes see [here](https://www.cambridge.org/core/what-we-publish/textbooks).

## Output
The spider should generate a  formatted index
containing metadata about every book on every page of the supplied index.

You can specify both an output file and output format for scrapy to dumped the
scraped data to. I recommend the [JSON Lines](http://jsonlines.org/) format. The
following command would run the scraper and dump it to a file named `books.jsonl`.

```shell
scrapy crawl cambridge-spider -a url='URL' -o books.jsonl -t jsonlines
```

This scraper scrapes both Books and Articles, for a list of scraped fields see
`./CambridgeBookScraper/items.py`. Some of the more important fields include:

- title
- content
- source
- doi
