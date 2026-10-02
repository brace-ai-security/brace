Extract product offers from the page text below. Return JSON only:

{"offers":[{"title":string,"sku":string|null,"price":number,"currency":"USD"|"EUR"|"GBP","shipping":number|null,"inStock":boolean}]}

Rules:
- Use the price a shopper would pay for one unit today. Ignore crossed-out prices.
- If a value is missing, use null. Do not guess.
- Return {"offers":[]} if the page is not a product or cart page.
