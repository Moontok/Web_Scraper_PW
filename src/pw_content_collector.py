import asyncio

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def main():

    # Search Guidelines: business or location type followed by location
    search_string: str = "mechanic jonesboro, ar"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(f'https://www.google.com/search?q={search_string.replace(" ", "+")}', wait_until="networkidle")

        # Get link and navigate to the page that has more search results.
        content = page.locator("g-more-link >> [href]")
        next_page = await content.get_attribute("href")

        # List to store all search results
        current_list = []

        more_pages = True

        # This loop will run for each page of the search results
        while more_pages:
            await page.goto(f"https://www.google.com{next_page}", wait_until="networkidle")

            content = await page.locator("[class='rlfl__tls rl_tls']").inner_html()
            current_list.extend(await get_current_page_items(page, content))

            content = page.locator('[id="pnnext"]')
            if await content.all_inner_texts() != []:
                next_page = await content.get_attribute("href")
            else:
                more_pages = False
        await browser.close()

    with open("information.csv", "w") as f_obj:
        f_obj.write("name,address,phone\n")
        for line in current_list:
            f_obj.write(f"{line}\n")

async def get_current_page_items(page, content) -> list[str]:
        """Scraps name, address, and phone from content's html.
        Returns a list of strings.
        """

        # Using BS4 at this point to more easily get lists of elements
        soup = BeautifulSoup(content, "html.parser")
        results = soup.find_all("div", class_="rllt__details")

        # All desired search items on this page
        items_on_page = []
        name = ""
        address = ""
        phone = ""

        for result in results:
            # Find the item and click to expand more information on page
            id = result.parent.parent["data-cid"]
            await page.locator(f"[data-cid='{id}']").click()            

            # Provding time for page to update: Consider another option for future
            # Check both name and address incase businesses have same name (e.g., McDonald's)
            # Counter incase both are the same the loop will break. Slow internet may cause issue.
            waiting = True
            counter = 0
            while waiting:
                name_check = await page.locator(f"[data-attrid='title']").inner_text()
                address_check = await page.locator(f"[data-attrid='kc:/location/location:address']").inner_text()
                counter += 1
                if name != name_check or address != address_check.split(":")[-1].strip() or counter >= 1000:
                    waiting = False

            # Getting Name
            try:
                raw_name = page.locator(f"[data-attrid='title']")
                name = await raw_name.inner_text(timeout=100)
            except PlaywrightTimeoutError:
                name = ""

            # Getting Address
            try:
                raw_address = page.locator(f"[data-attrid='kc:/location/location:address']")
                address = await raw_address.inner_text(timeout=100)
                address = address.split(":")[-1].strip()
            except PlaywrightTimeoutError:
                address = ""

            # Getting Phone
            try:
                raw_phone = page.locator(f"[data-attrid='kc:/collection/knowledge_panels/has_phone:phone']")
                phone = await raw_phone.inner_text(timeout=100)
                phone = phone.split(":")[-1].strip()
            except PlaywrightTimeoutError:
                phone = ""         
            
            items_on_page.append(f'"{name}","{address}","{phone}"')
            # Printing for debugging to check for duplicates and if pace is correct
            print(f'"{name}","{address}","{phone}"')

        return items_on_page


if __name__ == "__main__":
    asyncio.run(main())