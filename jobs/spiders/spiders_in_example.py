import scrapy
from jobs.items import JobsItem
from jobs.libabang import API
from jobs.locations import Locations
from bs4 import BeautifulSoup
import pdb

from jobs.spiders.ExampleBase import ExampleBase


### Plaid
class PlaidSpider(ExampleBase):
    name = "Plaid"
    company_name ="Plaid"
    start_url = "https://jobs.example.co/plaid"
    start_urls = [start_url]

### GoodLeap
class GoodLeapSpider(ExampleBase):
    name = "GoodLeap"
    company_name ="GoodLeap"
    start_url = "https://jobs.example.co/goodleap"
    start_urls = [start_url]
