import asyncio

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def main():

    # Search Guidelines: business or location type followed by location
    search_string: str = "mechanics walnut ridge ar"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(f'https://www.google.com/search?q={search_string.replace(" ", "+")}', wait_until="networkidle")

        # Get link and navigate to the page that has more search results.
        content = page.locator("g-more-link >> [href]")
        start_href = await content.get_attribute("href")
        hrefs = []
        first_href = [start_href, 1]

        # List to store all search results
        current_list = []

        more_pages = True

        # This loop will run for each page of the search results
        while more_pages:
            hrefs.append(first_href)
            # Go to the first page to get all visibile hrefs
            await page.goto(f"https://www.google.com{first_href[0]}", wait_until="networkidle")
            hrefs.extend(await get_visable_pages_links(page, hrefs[-1][-1]))
            
            
            tasks = []
            for href in hrefs:
                tasks.append(asyncio.ensure_future(get_target_page_items(p, href[0])))
            all_lists = await asyncio.gather(*tasks, return_exceptions=True)

            for list in all_lists:
                current_list.append(["NEW LIST", href[-1]])
                if type(list) == type([]):
                    for item in list:
                        current_list.append(item)
                else:
                    print("Something went wrong with this page...")
            
            more_pages = await check_for_next_page(browser, hrefs[-1][0])
            first_href = hrefs[-1]
            hrefs.clear()
        await browser.close()

    unique_list = set(current_list)
    with open("information.csv", "w") as f_obj:
        f_obj.write("name,address,phone\n")
        for line in unique_list:
            f_obj.write(f"{line}\n")


async def get_target_page_items(p, href) -> list[str]:
        """Scraps name, address, and phone from content's html.
        Returns a list of strings.
        """

        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto(f"https://www.google.com{href}", wait_until="networkidle")
        content = await page.locator("[class='rlfl__tls rl_tls']").inner_html()

        # Using BS4 at this point to more easily get lists of elements
        soup = BeautifulSoup(content, "html.parser")
        results = soup.find_all("div", class_="rllt__details")

        # All desired search items on this page
        items_on_page = []

        for result in results:
            name = ""
            address = ""
            phone = ""
            # Find the item and click to expand more information on page
            id = result.parent.parent["data-cid"]
            await page.locator(f"[data-cid='{id}']").click()

            # Getting Name
            while name == "":
                try:
                    raw_name = page.locator("[data-attrid='title']")
                    name = await raw_name.inner_text(timeout=100)
                except PlaywrightTimeoutError:
                    name = ""

            # Getting Address
            while address == "":
                try:
                    raw_address = page.locator("[data-attrid='kc:/location/location:address']")
                    address = await raw_address.inner_text(timeout=100)
                    if ":" in address:
                        address = address.split(":")[-1].strip()
                except PlaywrightTimeoutError:
                    address = ""

            # Getting Phone
            while phone == "":
                try:
                    raw_phone = page.locator("[data-attrid='kc:/collection/knowledge_panels/has_phone:phone']")
                    phone = await raw_phone.inner_text(timeout=100)
                    if ":" in phone:
                        phone = phone.split(":")[-1].strip()
                except PlaywrightTimeoutError:
                    phone = ""         
            
            items_on_page.append(f'"{name}","{address}","{phone}"')
            await page.locator("[aria-label='Close']:visible").click()

            # Printing for debugging to check for duplicates and if pace is correct
            # print(f'"{name}","{address}","{phone}"')

        await browser.close()
        return items_on_page[1:]


async def get_visable_pages_links(page, page_number):

    page_hrefs = []
    for i in range(page_number + 1, page_number + 11):
        content = page.locator(f"[aria-label='Page {i}']")
        if await content.all_inner_texts() != []:
            href =   await content.get_attribute("href")             
            page_hrefs.append([href, i])
    
    return page_hrefs


async def check_for_next_page(browser, href):

    page = await browser.new_page()
    await page.goto(f"https://www.google.com{href}", wait_until="networkidle")

    content = page.locator('[id="pnnext"]')
    if await content.all_inner_texts() != []:
        return True
    else:
        return False


if __name__ == "__main__":
    asyncio.run(main())