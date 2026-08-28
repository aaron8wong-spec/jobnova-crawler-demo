import scrapy
import json
from datetime import datetime, timedelta
from dateutil.parser import parse
from memory_profiler import profile

from jobs.items import JobsItem
from jobs.libabang import API
from jobs.locations import Locations


class Remote3APISpider(scrapy.Spider):
    name = "remote3"
    allowed_domains = ["remote3.co"]
    base_url = "https://ojpncdvueyetebptprsv.supabase.co/rest/v1/jobs"
    api = API()

    def start_requests(self):
        offset, limit = 0, 10
        params = (
            "?select=*,companies(*)&is_draft=eq.false"
            "&order=is_sticky.desc,live_at.desc"
            f"&offset={offset}&limit={limit}"
        )
        url = f"{self.base_url}{params}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Origin": "https://www.remote3.co",
            "Referer": "https://www.remote3.co/",
            "Accept": "application/json",
            "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qcG5jZHZ1ZXlldGVicHRwcnN2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk1MjM3MjUsImV4cCI6MjA1NTA5OTcyNX0.NbC4nC4PcFS6QGLXBsBuM0t7GACbkkC6tGVW3TwLCXU"
        }
        yield scrapy.Request(url=url, headers=headers, callback=self.parse, cb_kwargs={"offset": offset, "limit": limit}, dont_filter=True)

    def parse(self, response, offset=0, limit=10):
        data = json.loads(response.text)
        has_recent = False

        for job in data:
            created_at = job.get("created_at")
            if created_at:
                job_time = parse(created_at).replace(tzinfo=None)
                current_time = datetime.now()
                if current_time - job_time <= timedelta(days=2):
                    has_recent = True

            job_location = job.get("location", "")
            if job_location.strip().lower() == "worldwide":
                job_location = "remote"
            in_monitor = Locations().if_in_monitor(job_location)
            print(f"-------- job_location:{job_location}, in_monitor:{in_monitor}")
            if not in_monitor:
                continue

            item = JobsItem()
            item["company_name"] = job.get("companies", {}).get("name", "")
            item["job_href"] = job.get("apply_url")
            item["job_title"] = job.get("title")
            item["job_city_des"] = job_location
            item["details_job"] = ""

            tagids = self.api.analyze(item)
            if len(tagids) == 0:
                continue

            yield item

        if has_recent and len(data) == limit:
            next_offset = offset + limit
            next_url = f"https://ojpncdvueyetebptprsv.supabase.co/rest/v1/jobs?select=*,companies(*)&is_draft=eq.false&order=is_sticky.desc,live_at.desc&offset={next_offset}&limit={limit}"
            yield scrapy.Request(url=next_url, headers=response.request.headers, callback=self.parse, cb_kwargs={"offset": next_offset, "limit": limit})