# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
import time
from selenium import webdriver
from scrapy.http.response.html import HtmlResponse
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from jobs.libabang import API

from scrapy import signals

# useful for handling different item types with a single interface
from itemadapter import is_item, ItemAdapter


class JobsDownloaderMiddleware:
  # Not all methods need to be defined. If a method is not defined,
  # scrapy acts as if the downloader middleware does not modify the
  # passed objects.

  @classmethod
  def from_crawler(cls, crawler):
    # This method is used by Scrapy to create your spiders.
    s = cls()
    crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
    return s

  def process_request(self, request, spider):
    # return None
    # driver_path = r'E:\Python_Project\Scrapy\chromedriver.exe'
    # if 'https://www.uber.com/us/en/careers/list/' in request.url:
    #   return self.process_uber(request)
    # else:
    #   return None
    return None
    
  def process_response(self, request, response, spider):
    # Called with the response returned from the downloader.

    # Must either;
    # - return a Response object
    # - return a Request object
    # - or raise IgnoreRequest 
    return response

  def process_exception(self, request, exception, spider):
    # Called when a download handler or a process_request()
    # (from other downloader middleware) raises an exception.

    # Must either:
    # - return None: continue processing this exception
    # - return a Response object: stops process_exception() chain
    # - return a Request object: stops process_exception() chain
    pass

  def spider_opened(self, spider):
    spider.logger.info('Spider opened: %s' % spider.name)



from scrapy import signals

class CrawlerSpiderMiddleware:
  # Not all methods need to be defined. If a method is not defined,
  # scrapy acts as if the spider middleware does not modify the
  # passed objects.
  # priority = 600

  def __init__(self, stats):
      self.stats = stats
      # Used to track if each spider has errors
      self.spider_has_error = {}


  @classmethod
  def from_crawler(cls, crawler):
      # Check if this Middleware is enabled
      if not crawler.settings.getbool('SPIDER_SUCCESS_MIDDLEWARE_ENABLED', True):
          raise NotConfigured("SpiderSuccessMiddleware is not enabled")

      # Get stats object
      stats = crawler.stats
      middleware = cls(stats)
      
      crawler.signals.connect(middleware.spider_error, signal=signals.spider_error)
      crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
      # Listen for Spider close event
      crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
      return middleware
      
            

  def process_spider_input(self, response, spider):
      # Called for each response that passes through the spider middleware and enters the spider
      spider.logger.info(" CrawlerSpiderMiddleware process_spider_input")
      # Should return None or raise an exception
      return None

  def process_spider_output(self, response, result, spider):
      # Called with the results returned from the Spider after processing the response.
      # Must return an iterable of Request, dict or Item objects.
      for i in result:
          yield i

  def process_spider_exception(self, response, exception, spider):
      # Called when the spider or process_spider_input() method (from other spider middleware) raises an exception.
      spider.logger.info(f" Spider got Exception: {exception}")
     # Should return None or an iterable of Response, dict or Item objects.
      # ######## Set fence job detection status: 0 unclassified, 1 success, 2 failure
      self.spider_has_error[spider.name] = True
      pass

  def process_start_requests(self, start_requests, spider):
      # Called with the start requests of the spider, works similar to process_spider_output() method, but without associated response.
      spider.logger.info(" CrawlerSpiderMiddleware process_start_requests start")
      # Must return requests
      for r in start_requests:
          yield r
      spider.logger.info(" CrawlerSpiderMiddleware process_start_requests end")

  def spider_opened(self, spider):
      # print("-----------------------spider_opened numbers:",spider.numbers)
      spider.logger.info(' CrawlerSpiderMiddleware Spider opened: %s' % spider.name)

  def spider_closed(self, spider,reason):
      ### Close opened browser, in the future with basespider parent class, can implement in parent class closed function
      if hasattr(spider, "driver") and spider.driver:
          spider.driver.quit()

      if hasattr(spider, "browser") and spider.browser:
        spider.browser.close()
      # Get Spider close reason
      finish_reason = self.stats.get_value('finish_reason', 'unknown')
      # Get number of scraped items
      item_count = self.stats.get_value('item_scraped_count', 0)
      # Get total number of requests
      request_count = self.stats.get_value('downloader/request_count', 0)
      # Get total number of responses
      response_count = self.stats.get_value('downloader/response_count', 0)

      # Determine if Spider succeeded
      # Check if this spider has errors, if no errors and meets other conditions, update status to 0
      if finish_reason == 'finished' and item_count == 0 and not self.spider_has_error.get(spider.name, False):
          spider.logger.info(f"Spider '{spider.name}' ran successfully.")
          spider.logger.info(f"Items scraped: {item_count}")
          spider.logger.info(f"Requests made: {request_count}")
          spider.logger.info(f"Responses received: {response_count}")
          # ######## Set fence job detection status: 0 unclassified, 1 success, 2 failure
      # Spider middleware
      spider.logger.info(' CrawlerSpiderMiddleware in Spider closed: %s' % spider.name)

  def spider_error(self, failure, response, spider):
      spider.logger.info(f" CrawlerSpiderMiddleware spider_error: {failure}, {spider.name}")
      # Record that this spider had an error
      self.spider_has_error[spider.name] = True

  def item_scraped(self, item, response, spider):
      spider.logger.info(' CrawlerSpiderMiddleware item_scraped: %s' % spider.name)
