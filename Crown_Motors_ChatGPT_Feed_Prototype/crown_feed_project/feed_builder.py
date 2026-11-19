#!/usr/bin/env python3
"""Build a *draft* OpenAI discovery JSONL file from Crown Motors PDX public listings.

No publishing is performed. This script must only run when the website permits automated
retrieval. Used automobile eligibility in OpenAI commerce is not yet confirmed.
"""
import argparse
import datetime as dt
import gzip
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE = 'https://www.crownmotorspdx.com'
INDEX = BASE + '/used-vehicles/?_exclude=condition'
UA = 'CrownMotorsPDX-InventoryFeed/0.1 (dealer-owned audit; contact sales@crownmotorspdx.com)'
VIN_RE = re.compile(r'\b[A-HJ-NPR-Z0-9]{17}\b')
MONEY_RE = re.compile(r'(?:Sale\s*price\s*)?\$\s*([0-9]{2,3}(?:,[0-9]{3})+)', re.I)


def soup_from(html):
    return BeautifulSoup(html, 'html.parser')


def extract_links(html):
    soup = soup_from(html)
    out = {}
    for a in soup.find_all('a', href=True):
        url = urljoin(BASE, a['href']).split('#')[0]
        if urlparse(url).hostname not in {'www.crownmotorspdx.com', 'crownmotorspdx.com'}:
            continue
        if '/vehicle/used-' not in urlparse(url).path.lower():
            continue
        title = a.get_text(' ', strip=True)
        if not title or len(title) < 14:
            continue
        out[url] = title
    return out


def get_jsonld(soup):
    objs = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.string or tag.get_text())
        except (ValueError, TypeError):
            continue
        def walk(node):
            if isinstance(node, list):
                for x in node: walk(x)
            elif isinstance(node, dict):
                objs.append(node)
                for x in node.get('@graph', []): walk(x)
        walk(data)
    return objs


def text_after_label(soup, label):
    # DealerTower's rendered basic-information section uses label/value pairs.
    # Search tightly: do not fall back to marketing copy for mileage/price.
    pat = re.compile(r'^' + re.escape(label) + r'$', re.I)
    for s in soup.find_all(string=pat):
        node = s.parent
        if not node:
            continue
        for candidate in [node.find_next_sibling(), node.parent.find_next_sibling() if node.parent else None]:
            if candidate:
                v = candidate.get_text(' ', strip=True)
                if v and len(v) < 160: return v
    return None


def meta(soup, *names):
    for name in names:
        tag = soup.find('meta', attrs={'property': name}) or soup.find('meta', attrs={'name': name})
        if tag and tag.get('content'): return tag['content'].strip()
    return None


def direct_image(soup):
    """Find a likely vehicle photograph, including lazy-loaded/CDN image URLs."""
    candidates = []

    def add(value, weight=0):
        if isinstance(value, dict):
            value = value.get('url') or value.get('contentUrl')
        if isinstance(value, str):
            value = value.strip()
            if value and not value.startswith(('data:', 'blob:', '#')):
                candidates.append((weight, urljoin(BASE, value)))

    # Website's preview image and vehicle-specific structured data.
    add(meta(soup, 'og:image', 'twitter:image'), 75)
    for obj in get_jsonld(soup):
        imgs = obj.get('image')
        if isinstance(imgs, list):
            for val in imgs: add(val, 85)
        else:
            add(imgs, 85)

    # Lazy-loaded galleries often put the real picture in one of these attributes.
    attrs = ('data-full', 'data-full-src', 'data-zoom-image', 'data-large-image',
             'data-original', 'data-src', 'data-lazy-src', 'src', 'poster')
    for img in soup.find_all(['img', 'source']):
        context = ' '.join(str(img.get(k, '')) for k in ('alt', 'class', 'id')).lower()
        score = 55 if any(w in context for w in ('vehicle', 'gallery', 'slider', 'ford',
                  'gmc', 'cadillac', 'ram', 'truck', 'photo', 'inventory')) else 20
        for attr in attrs:
            add(img.get(attr), score + (12 if attr != 'src' else 0))
        for attr in ('srcset', 'data-srcset'):
            val = img.get(attr)
            if val:
                # Prefer the last (typically largest) srcset candidate.
                for option in val.split(','):
                    add(option.strip().split(' ')[0], score + 10)

    # Some galleries place URLs in data attributes and inline background styles.
    for tag in soup.find_all(True):
        for k, v in tag.attrs.items():
            if k.startswith('data-') and any(w in k for w in ('image', 'photo', 'thumb')):
                if isinstance(v, str): add(v, 40)
        style = tag.get('style', '')
        if isinstance(style, str):
            for url in re.findall(r'url\([\"\']?([^\)\"\']+)', style):
                add(url, 35)

    def valid(url):
        parts = urlparse(url)
        if parts.scheme != 'https' or not parts.netloc:
            return False
        low = (parts.path + '?' + parts.query).lower()
        if any(x in low for x in ('logo', 'favicon', 'sprite', 'placeholder', 'icon',
                                   'avatar', 'badge', 'tracking', 'pixel')):
            return False
        return True

    for score, url in sorted(candidates, key=lambda p: p[0], reverse=True):
        if valid(url):
            return url
    return None


def valid_vin(value):
    """Require a plausible 17-character VIN, not a 17-letter model slug."""
    value = (value or '').upper()
    return bool(VIN_RE.fullmatch(value) and sum(c.isdigit() for c in value) >= 4)


def parse_detail(html, url, title_hint=''):
    soup = soup_from(html)
    body = soup.get_text('\n', strip=True)
    title = next((h.get_text(' ', strip=True) for h in soup.find_all('h1') if re.search(r'20\d\d', h.get_text(' ', strip=True))), None) or title_hint
    vin = None
    # Vehicle URLs end with the VIN, e.g. ...-1FT8W4DM1VEC05424/.
    # Never run a free-text VIN search on the entire model slug: the substring
    # F450SUPERDUTYCREW is 17 characters but is NOT a VIN.
    end_slug = urlparse(url).path.rstrip('/').split('-')[-1].upper()
    if valid_vin(end_slug):
        vin = end_slug
    if not vin:
        labeled = re.search(r'\bVIN\s*[:#]?\s*([A-HJ-NPR-Z0-9]{17})\b', body, re.I)
        if labeled and valid_vin(labeled.group(1)):
            vin = labeled.group(1).upper()
    if not vin:
        for obj in get_jsonld(soup):
            for key in ('vehicleIdentificationNumber', 'vin'):
                candidate = str(obj.get(key, '')).upper()
                if valid_vin(candidate):
                    vin = candidate
                    break
            if vin:
                break
    price = None
    for o in get_jsonld(soup):
        offers = o.get('offers')
        if isinstance(offers, dict) and offers.get('price'):
            try: price = int(float(str(offers['price']).replace(',','')))
            except ValueError: pass
            if price: break
    if not price:
        # Prefer price adjacent to the 'Sale price' label; not prices in related vehicles or narrative.
        m = re.search(r'Sale\s*price\s*\$\s*([0-9,]+)', body, re.I)
        if m: price = int(m.group(1).replace(',',''))
    desc_block = soup.find(lambda t: t.name in {'h2','h3'} and t.get_text(' ',strip=True).lower() == 'description')
    description = ''
    if desc_block:
        parts = []
        for sibling in desc_block.next_elements:
            if getattr(sibling, 'name', None) in {'h2','h3'} and sibling is not desc_block: break
            if getattr(sibling, 'name', None) in {'p','li'}:
                tx = sibling.get_text(' ', strip=True)
                if tx and tx not in parts: parts.append(tx)
        description = ' '.join(parts)[:5000]
    if not description:
        description = (meta(soup, 'description', 'og:description') or '')[:5000]
    # Use explicit mileage next to basic information rather than narrative.
    mileage = text_after_label(soup, 'Mileage')
    if not mileage:
        match = re.search(r'Basic information[\s\S]{0,600}?\bMileage\s*\n\s*([0-9,]+\s*miles)', body, re.I)
        if match: mileage = match.group(1)
    if mileage: description = (f'Odometer: {mileage}. ' + description)[:5000]
    brand_match = re.match(r'^20\d\d\s+(Ford|GMC|Cadillac|Ram|Chevrolet|Toyota|Dodge|Jeep|Lincoln|Mercedes-Benz|BMW|Porsche)\b', title, re.I)
    brand = brand_match.group(1) if brand_match else None
    # We cannot infer in-stock status from 'Confirm availability'.
    record = {
        'item_id': vin, 'title': title[:150] if title else None,
        'description': description or None, 'url': url, 'brand': brand,
        'seller_name': 'Crown Motors PDX', 'image_url': direct_image(soup),
        'availability': 'unknown', 'price': f'{price:.2f} USD' if price else None,
        'target_countries': ['US'], 'store_country': 'US', 'condition': 'used',
        'is_eligible_checkout': False,
    }
    return record


def validate(rows, expected_min=1):
    required = ['item_id','title','description','url','brand','seller_name','image_url','availability','price','target_countries','store_country']
    errors = []
    seen = set()
    for i, row in enumerate(rows, 1):
        for field in required:
            if not row.get(field): errors.append(f'Row {i}: missing {field}')
        if row.get('item_id') and not valid_vin(row['item_id']): errors.append(f'Row {i}: invalid VIN {row["item_id"]}')
        if row.get('item_id') in seen: errors.append(f'Row {i}: duplicate VIN {row.get("item_id")}')
        seen.add(row.get('item_id'))
        if row.get('price') and not re.match(r'^\d+(?:\.\d{2}) USD$', row['price']): errors.append(f'Row {i}: invalid price')
        for key in ['url','image_url']:
            if row.get(key) and not row[key].startswith('https://'): errors.append(f'Row {i}: invalid {key}')
    if len(rows) < expected_min: errors.append(f'Count {len(rows)} below expected minimum {expected_min}')
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='output/crown_inventory.jsonl.gz')
    ap.add_argument('--min-vehicles', type=int, default=18)
    ap.add_argument('--offline-fixture', help='Test with saved HTML for one detail page; no network')
    args = ap.parse_args()
    if args.offline_fixture:
        html = Path(args.offline_fixture).read_text(encoding='utf8')
        rows = [parse_detail(html, 'https://www.crownmotorspdx.com/vehicle/used-2027-Ford-F450-1FT8W4DM1VEC05424/')]
        errors = validate(rows, expected_min=1)
    else:
        sess = requests.Session(); sess.headers.update({'User-Agent':UA})
        # Honor robots.txt; fail closed if unreachable or disallowed.
        parser = RobotFileParser()
        try:
            robots_response = sess.get(BASE + '/robots.txt', timeout=20)
            robots_response.raise_for_status()
            parser.parse(robots_response.text.splitlines())
        except requests.RequestException as e:
            sys.exit(f'Cannot retrieve robots policy: {e}')
        if not parser.can_fetch(UA, INDEX):
            sys.exit('Automated inventory fetch not permitted')
        links = {}
        for page in (1,2,3,4,5):
            target = INDEX if page==1 else INDEX+'&page='+str(page)
            if not parser.can_fetch(UA, target): sys.exit('robots policy disallows inventory page')
            response=sess.get(target,timeout=25);response.raise_for_status()
            found = extract_links(response.text)
            if page>1 and (not found or all(url in links for url in found)): break
            links.update(found)
            if page>1 and len(found)<12: break
            time.sleep(1.5)
        if len(links)<args.min_vehicles: sys.exit(f'Only found {len(links)} URLs; refusing incomplete export')
        rows=[]
        for url,title in links.items():
            if not parser.can_fetch(UA,url): sys.exit(f'robots policy disallows {url}')
            r=sess.get(url,timeout=25);r.raise_for_status()
            rows.append(parse_detail(r.text,url,title))
            time.sleep(1.5)
        errors=validate(rows, expected_min=args.min_vehicles)
    if errors:
        print('VALIDATION FAILED; previous feed will not be overwritten:',file=sys.stderr)
        for e in errors[:50]:print('  '+e,file=sys.stderr)
        sys.exit(2)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    with gzip.open(tmp,'wt',encoding='utf8') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
    tmp.replace(path)
    print(f'Created {len(rows)} rows: {path} (DRAFT only; automotive eligibility still unverified)')

if __name__=='__main__':main()
