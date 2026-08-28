import scrapy
import json
from datetime import datetime, timedelta
from dateutil.parser import parse
from memory_profiler import profile

from jobs.items import JobsItem
from jobs.libabang import API
from jobs.locations import Locations


class BreezyBase(scrapy.Spider):
    """
    Base spider for companies hosted on the Breezy HR ATS.

    How the data source was found
    -------------------------------
    Every company using Breezy HR gets a subdomain career site at:
        https://{company}.breezy.hr/
    That HTML page renders its job list client-side, but Breezy also exposes
    an unauthenticated, plain-JSON mirror of the same listing at:
        https://{company}.breezy.hr/json
    This was confirmed by inspecting network requests on a live Breezy career
    page (e.g. https://barloworldequipment.breezy.hr/json, given as an example
    in the assignment) and cross-checking the field names against Breezy's
    public API "Position" model (https://developer.breezy.hr/reference/model-position),
    which documents the same schema (name, friendly_id, location, category, ...).
    No API key is required for this endpoint since it is the same JSON the
    public career page itself fetches to render the list.

    Each subclass only needs to set:
        name           -- scrapy spider name
        company_name   -- display name written into the JobsItem
        company_slug   -- the Breezy subdomain, e.g. "nucamp" for nucamp.breezy.hr
    """

    api = API()

    # Filled in by subclasses
    company_slug = None

    @property
    def base_url(self):
        return f"https://{self.company_slug}.breezy.hr"

    @property
    def start_urls(self):
        return [f"{self.base_url}/json"]

    def start_requests(self):
        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        for url in self.start_urls:
            yield scrapy.Request(url, headers=headers, callback=self.parse)

    @profile
    def parse(self, response):
        print(
            f"----- this spider name:{self.name}, "
            f"company_name:{self.company_name}, start_urls:{self.start_urls}"
        )

        try:
            postings = json.loads(response.text)
        except json.JSONDecodeError:
            self.logger.warning(f"Non-JSON response from {response.url}, skipping.")
            return

        # Breezy's /json feed returns either a bare list of postings, or a
        # dict with the list under a "positions"/"data" key depending on
        # account configuration -- handle both defensively.
        if isinstance(postings, dict):
            postings = postings.get("positions") or postings.get("data") or []

        for job in postings:
            item = JobsItem()
            item["company_name"] = self.company_name

            job_title = job.get("name", "")
            item["job_title"] = job_title

            friendly_id = job.get("friendly_id", "")
            item["job_href"] = f"{self.base_url}/p/{friendly_id}" if friendly_id else ""

            job_location = self._format_location(job.get("location", {}))
            in_monitor = Locations().if_in_monitor(job_location)
            print(f"-------- job_location:{job_location}, in_monitor:{in_monitor}")
            if not in_monitor:
                continue

            # Filter to postings published within the last 2 days, when a
            # publish date is present in the feed (published_date / creation_date).
            posted_raw = job.get("published_date") or job.get("creation_date")
            if posted_raw:
                try:
                    job_time = parse(posted_raw).replace(tzinfo=None)
                    if datetime.now() - job_time > timedelta(days=2):
                        continue
                except (ValueError, TypeError):
                    pass

            item["job_city_des"] = job_location
            category = job.get("category", {}) or {}
            department = job.get("department", "")
            item["details_job"] = category.get("name", "") or department

            tagids = self.api.analyze(item)
            if len(tagids) == 0:
                continue
            yield item

    @staticmethod
    def _format_location(location):
        if not location:
            return ""
        if location.get("is_remote"):
            return "Remote"
        parts = [
            location.get("name") or location.get("city"),
            (location.get("state") or {}).get("name"),
            (location.get("country") or {}).get("name"),
        ]
        return ", ".join(p for p in parts if p)
