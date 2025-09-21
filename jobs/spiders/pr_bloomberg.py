import scrapy
from jobs.items import JobsItem
from jobs.libabang import API
from jobs.locations import Locations
import pdb
from playwright.sync_api import sync_playwright
import re

def handle_cookie_popup(page):
    if page.locator(".cookiesButtonAccept").is_visible():
        # Adjust the selector to match your website's cookie popup
        page.locator(".cookiesButtonAccept").click()
    
class BloombergSpider(scrapy.Spider):
    name = "bloomberg"
    allowed_domains = ["careers.bloomberg.com"]
    start_urls = ["https://www.baidu.com"]
    base_url = "https://careers.bloomberg.com"
    driver = None
    def parse(self, response):
        urls=["https://bloomberg.avature.net/en_US/careers/SearchJobs/?1686=%5B55478%2C55479%5D&1686_format=2312&listFilterMode=1&jobRecordsPerPage=12&#",
              "https://bloomberg.avature.net/en_US/careers/SearchJobs"]
        api = API()
        with sync_playwright() as p:
          for browser_type in [p.chromium]:
            self.browser = browser = browser_type.launch(headless = True)
            context = browser.new_context(locale=r"en-US,en;q=0.9")
            page = context.new_page()
            # page = browser.new_page()
            page.set_default_timeout(120000)
            page.route("**/*", lambda route: {route.abort() if route.request.resource_type == 'image' else route.continue_() } )
            for url in urls:
                page_size = 0 
                page.goto(url)
                while True:
                    page.wait_for_timeout(3000)
                    handle_cookie_popup(page)
                    jobs = page.locator(".article--result").all()
                    page.wait_for_timeout(3000)
                    print("---page.url:",page.url)
                    for job in jobs:
                        item = JobsItem()
                        item["company_name"] ="Bloomberg"         
                        job_location = job.locator(".list-item-location").text_content()
                        #### This Locations().if_in_monitor call cannot be omitted.
                        in_monitor = Locations().if_in_monitor(job_location)
                        print(f"-------- job_location:{job_location}, in_monitor:{in_monitor}")
                        if not in_monitor:
                          continue

                        item["job_city_des"] = job_location
                        link = job.locator('.article__header__text__title a')
                        # pdb.set_trace()
                        item["job_href"] = link.get_attribute("href")
                        item["job_title"] = link.text_content().strip()
                        # pdb.set_trace()
                        item["details_job"] =  ""
                        ##### Determine/analyze if this job meets the criteria based on job title, save conditions
                        job_title_infos = f'{item["job_title"]};{item["details_job"]}'
                        #### This api.analyze call cannot be omitted.
                        tagids = api.analyze(item)
                        if len(tagids) == 0:
                          continue  

                        yield item      
                    ### goto next page
                    last_link = page.locator(".list-controls__pagination a").all()[-1]
                    link_text = last_link.text_content().strip()
                    if "next" not in  link_text.lower() or page_size > 10:
                      break
                    else:
                      page_size += 1  
                      last_link.click()

            browser.close()
            pass
