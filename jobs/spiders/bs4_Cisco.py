import scrapy
from jobs.items import JobsItem
from jobs.libabang import API
from jobs.locations import Locations
from bs4 import BeautifulSoup
import pdb


class CiscoSpider(scrapy.Spider):
    name = "Cisco"
    allowed_domains = ["jobs.cisco.com"]
    start_urls = [
                  "https://jobs.cisco.com/jobs/SearchJobs"
                  ]
    driver = None
    api = API()

    def parse(self, response):
        soup = BeautifulSoup(response.text, 'html.parser')
        # pdb.set_trace()
        jobs = soup.select("tbody tr")
        for job in jobs:
            item = JobsItem()
            item["company_name"] ="Cisco"
            # pdb.set_trace()
            item["job_title"]  = job.find("a").text
            item["job_href"]  = job.find("a").get("href")
            
            job_location = job.select("[data-th='Location']")[0].text
            in_monitor = Locations().if_in_monitor(job_location)
            print(f"-------- job_location:{job_location}, in_monitor:{in_monitor}")
            if not in_monitor:
              continue

            item["job_city_des"] = job_location
            item["details_job"] = job.select("[data-th='Actions']")[0].text
            job_title_infos = f'{item["job_title"]};{item["details_job"]}'

            tagids = self.api.analyze(item)
            if len(tagids) == 0:
              continue
            yield item

        ####next page
        for page_link in soup.select(".pagination_bottom a"):
          if "Next" in page_link.text:
            url = page_link.get("href")
            # print("------------ next_url:", url)
            yield scrapy.Request(url, callback=self.parse)
        pass
