import scrapy
from jobs.items import JobsItem
from jobs.libabang import API
from jobs.locations import Locations
from datetime import datetime, timedelta
import json
import pdb

class AppleSpider(scrapy.Spider):
    name = "Apple"
    allowed_domains = ["jobs.apple.com"]
    api = API()
    page = 1
    base_url = "https://jobs.apple.com"

    HEADERS = {
        'accept': '*/*',
        'accept-language': 'en,zh;q=0.9',
        'browserlocale': 'en-us',
        'content-type': 'application/json',
        'locale': 'en_US',
        'origin': 'https://jobs.apple.com',
        'priority': 'u=1, i',
        'referer': 'https://jobs.apple.com/en-us/search?sort=newest',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }

    def start_requests(self):
        payload = {
            "query": "",
            "filters": {},
            "page": self.page,
            "locale": "en-us",
            "sort": "newest",
            "format": {
                "longDate": "MMMM D, YYYY",
                "mediumDate": "MMM D, YYYY"
            }
        }
        url = f"{self.base_url}/api/v1/search"
        yield scrapy.Request(
            url,
            method='POST',
            headers=self.HEADERS,
            body=json.dumps(payload),
            callback=self.parse
        )

    def parse(self, response):
        data = json.loads(response.text)
        jobs = data.get("res").get("searchResults", [])
        
        for job in jobs:
            # Check posting date if available
            posting_date = job.get("postDateInGMT")
            if posting_date:
                try:
                    posted_time = datetime.strptime(posting_date.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                    now = datetime.now(posted_time.tzinfo)
                    if (now - posted_time) > timedelta(days=2):
                        continue
                except ValueError:
                    continue

            item = JobsItem()
            item["company_name"] = "Apple"
            item["job_title"] = job.get("postingTitle", "")
            transformedPostingTitle = job["transformedPostingTitle"]
            positionId = job["positionId"]

            item["job_href"] = f"https://jobs.apple.com/en-us/details/{positionId}/{transformedPostingTitle}"
            
            # pdb.set_trace()

            localcoin = job["locations"][0]
            print(localcoin)
            job_location = f"{localcoin['name']}"
            print(f"------------ job_location:{job_location}")
            in_monitor = Locations().if_in_monitor(job_location)
            if not in_monitor:
                continue

            item["job_city_des"] = job_location
            item["details_job"] = ""
            tagids = self.api.analyze(item)
            if len(tagids) == 0:
                continue
                
            yield item


        # Pagination
        if self.page < 6:
            self.page += 1
            payload = {
                "query": "",
                "filters": {},
                "page": self.page,
                "locale": "en-us",
                "sort": "newest",
                "format": {
                    "longDate": "MMMM D, YYYY",
                    "mediumDate": "MMM D, YYYY"
                }
            }
            yield scrapy.Request(
                f"{self.base_url}/api/v1/search",
                method='POST',
                headers=self.HEADERS,
                body=json.dumps(payload),
                callback=self.parse
            )
