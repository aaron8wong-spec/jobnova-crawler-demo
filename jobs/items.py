# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class JobsItem(scrapy.Item):
  # define the fields for your item here like:
  # role = scrapy.Field()
  # role_herf = scrapy.Field()
  # sub_team = scrapy.Field()
  countryCode = scrapy.Field()
  company_logo = scrapy.Field()
  job_href = scrapy.Field()
  job_title = scrapy.Field()
  company_name = scrapy.Field()
  job_city_des = scrapy.Field()
  details_job = scrapy.Field()
  details_company = scrapy.Field()
  company_href = scrapy.Field()
  search_by = scrapy.Field()
  org_id = scrapy.Field()
  internalType = scrapy.Field()
  category_name = scrapy.Field()
  # jobs_description_text = scrapy.Field()
  # jobs_description_html = scrapy.Field()

  def __init__(self, *args, **kwargs):
      super(JobsItem, self).__init__(*args, **kwargs)
      self['internalType'] = ''  # Set default value
      self['category_name'] = ''  # Set default value
