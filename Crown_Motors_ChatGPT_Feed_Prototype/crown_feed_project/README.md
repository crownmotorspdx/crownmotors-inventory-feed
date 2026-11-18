# Crown Motors PDX — ChatGPT vehicle feed prototype

**Status: PROTOTYPE / NOT CONNECTED TO BUSINESS HUB**

## Purpose
Read the publicly visible `https://www.crownmotorspdx.com/used-vehicles/?_exclude=condition` pages, extract individual vehicle detail pages and create a gzipped JSON Lines feed matching OpenAI's 11 discovery fields. It uses the VIN as stable `item_id`, includes the complete detail URL and a publicly hosted image URL, and sets availability to `unknown` unless a live inventory source is verified. It never uploads to OpenAI.

## Prerequisites before ANY publishing
1. **Used automobile category eligibility:** OpenAI's generic `used` condition does not establish automobile eligibility. Obtain confirmation from OpenAI support / Business Hub.
2. **Website access policy:** Ensure the public website permits scheduled automated extraction. This script checks `robots.txt` and fails closed if access is disallowed or policy cannot be read; also check the site's terms.
3. **Data quality:** Check mileage, prices, description, actual image bytes, VIN, sold status, all pages, and inventory count. Generic structured descriptions can be stale. Compare the result to DealerCenter's active inventory count.
4. **No manual publishing until test passes.** Avoid uploading outdated/unavailable vehicle offers. The current draft uses `availability: unknown`, not `in_stock`.
5. **No private information:** Only public listing details are read; no DealerCenter credentials, sales profit, customer details, or financial data.

## Install and run
```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python feed_builder.py --min-vehicles 18
```
Successful output: `output/crown_inventory.jsonl.gz` with one JSON object per line. **Do not upload yet**.

## Automatic audit, not live publishing
The `.github/workflows/draft-feed-check.yml` workflow is a **daily draft check**. It runs Python tests, attempts the website extraction, and makes a private downloadable GitHub Actions artifact; it does NOT create a permanent hosted URL or submit inventory to OpenAI. Scheduled workflows may be delayed or require repository setup. The feed will only be hosted after eligibility, validation, and a separate publishing step are approved.

## Next engineering iteration
- Test the script in a network-connected environment against actual dealer HTML. The current development environment cannot reach public websites from Python, so HTML-selector accuracy has NOT been verified live.
- Handle JavaScript-rendered pages and image-gallery srcsets if necessary. If the extractor fails due to missing images or data, fix selectors based on real saved HTML; do not simply disable validation.
- Add a stateful inventory inventory-count check and fail if VINs disappear unexpectedly.
- Validate image responses (HTTP 200, image content type) and all price/availability differences.
- Create a persistent hosted HTTPS file (e.g. GitHub Pages or storage/CDN) only after all prior checks are satisfied; feed's visibility may expose stock publicly.
- Configure the hosted URL in ChatGPT Business Hub and monitor its processing errors.

Documentation: https://developers.openai.com/commerce/specs/file-upload/products
