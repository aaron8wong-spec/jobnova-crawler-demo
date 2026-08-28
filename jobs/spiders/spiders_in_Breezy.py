from jobs.spiders.BreezyBase import BreezyBase


### Zero Hash -- crypto/stablecoin infrastructure fintech
class ZeroHashSpider(BreezyBase):
    name = "ZeroHash"
    company_name = "Zero Hash"
    company_slug = "zero-hash"
    start_url = "https://zero-hash.breezy.hr"
    start_urls = [f"{start_url}/json"]


### Federal Public Defender, Western District of Texas
class FederalPublicDefenderTXWSpider(BreezyBase):
    name = "FederalPublicDefenderTXW"
    company_name = "Federal Public Defender, Western District of Texas"
    company_slug = "federal-public-defender-western-district-of-texas"
    start_url = "https://federal-public-defender-western-district-of-texas.breezy.hr"
    start_urls = [f"{start_url}/json"]


### Barloworld Equipment -- heavy equipment dealer (given as example endpoint in the assignment)
class BarloworldEquipmentSpider(BreezyBase):
    name = "BarloworldEquipment"
    company_name = "Barloworld Equipment"
    company_slug = "barloworldequipment"
    start_url = "https://barloworldequipment.breezy.hr"
    start_urls = [f"{start_url}/json"]
