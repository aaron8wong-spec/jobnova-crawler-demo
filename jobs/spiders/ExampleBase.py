import scrapy
from jobs.items import JobsItem
from jobs.libabang import API
from jobs.locations import Locations
from bs4 import BeautifulSoup
import pdb
import json
from memory_profiler import profile
import requests
from datetime import datetime, timedelta
from dateutil.parser import parse

class ExampleBase(scrapy.Spider):
    allowed_domains = ["jobs.Example.co"]
    base_url = "https://jobs.Example.co"
    api = API()

    @profile
    def parse(self, response):
        print(f"----- this spider name:{self.name}, company_name:{self.company_name}, start_urls:{self.start_urls}")


        soup = BeautifulSoup(response.text, 'html.parser')

        # pdb.set_trace()
        jobs = soup.select("a.posting-title")
        for job in jobs:
          item = JobsItem()
          item["company_name"] =self.company_name
          # item["job_href"] =  self.base_url + job.find("a").get("href")
          item["job_title"]  = job.find("h5").text
          url = job.get("href")
          item["job_href"]  = url

          if not job.select("span.location"):
            continue

          job_location = job.select("span.location")[0].text
          in_monitor = Locations().if_in_monitor(job_location)
          print(f"-------- job_location:{job_location}, in_monitor:{in_monitor}")
          if not in_monitor:
            continue
          
          ## 检测发布时间
          dateposted = self.get_dateposted(url)
          ### "dateposted": '2025-03-13'
          if dateposted:
              current_time = datetime.now()
              job_time = parse(dateposted).replace(tzinfo=None)
              # 只抓取 2天内的岗位
              if current_time - job_time > timedelta(days=2):
                  continue

          item["job_city_des"] = job_location
          item["details_job"] = ""
          # print(item)
          job_title_infos = f'{item["job_title"]};{item["details_job"]}'

          tagids = self.api.analyze(item)
          if len(tagids) == 0:
            continue
          yield item

    def get_dateposted(self, url):
        response = requests.get(url)
        return self.parse_dateposted(response)

    def parse_dateposted(self, response):
        soup = BeautifulSoup(response.text, 'html.parser')
        json_data = soup.find("script", type="application/ld+json")
        if json_data:
            job_data = json.loads(json_data.string)
            date_posted = job_data.get("datePosted", None)
            if date_posted:
                # 这里可以将 date_posted 存储到 item 中
                # 例如：item["date_posted"] = date_posted
                return date_posted
        return None


