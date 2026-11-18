import unittest
from feed_builder import extract_links, parse_detail, validate

class FeedTests(unittest.TestCase):
 def test_links(self):
  html='<a href="/vehicle/used-2027-Ford-F450-1FT8W4DM1VEC05424/">2027 Ford F450 Platinum</a>'
  self.assertEqual(len(extract_links(html)),1)
 def test_detail(self):
  html='''<html><head><meta property="og:image" content="https://example.com/truck.jpg"><meta name="description" content="Crown Signature Reserve truck"></head><body><h1>2027 Ford F450 Platinum</h1><p>Sale price $122,900</p><div>VIN 1FT8W4DM1VEC05424</div></body></html>'''
  row=parse_detail(html,'https://www.crownmotorspdx.com/vehicle/used-2027-Ford-F450-1FT8W4DM1VEC05424/')
  self.assertFalse(validate([row]));self.assertEqual(row['availability'],'unknown')
  self.assertEqual(row['price'],'122900.00 USD')
 def test_no_picture_fails(self):
  html='<h1>2027 Ford F450</h1><p>Sale price $122,900</p>'
  row=parse_detail(html,'https://www.crownmotorspdx.com/vehicle/used-2027-Ford-F450-1FT8W4DM1VEC05424/')
  self.assertTrue(any('image_url' in e for e in validate([row])))

if __name__=='__main__':unittest.main()
