# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import logging
import json
from datetime import datetime

from dotenv import load_dotenv
import sys
import os
from twisted.internet import reactor
from time import sleep
import pdb
from multiprocessing import Pool


load_dotenv(".env")



class SaveByApi:
  api = None
  numbers = 1
  async def process_item(self, item, spider):     
    # Create items directory
    items_dir = "items"
    os.makedirs(items_dir, exist_ok=True)
    
    # Generate filename: spider_name.json
    filename = f"{items_dir}/{spider.name}.json"
    
    # Save item as JSON
    with open(filename, 'a', encoding='utf-8') as f:
        json.dump(dict(item), f, ensure_ascii=False, indent=4)
    
    print(f"Item saved to {filename}")
    return item
