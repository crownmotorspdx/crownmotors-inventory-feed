import unittest
from feed_builder import extract_links, parse_detail, validate

class FeedTests(unittest.TestCase):
 def test_links(self):
  html='<a href="/vehicle/used-2027-Ford-F450-1FT8W4DM1VEC05424/">2027 Ford F450 Platinum</a>'
  self.assertEqual(len(extract_links(html)),1)
 def test_detail(self):
  html='''<html><head><meta property="og:image" content="https://imagesdl.dealercenter.net/1024/768/202605-3b6b3c8e4fb24038a64ee449c9bb54e4/202611-0e9a0eca01d0422e84bc0fe8052f609e.jpg"><meta name="description" content="Crown Signature Reserve truck"></head><body><h1>2027 Ford F450 Platinum</h1><p>Sale price $122,900</p><div>VIN 1FT8W4DM1VEC05424</div></body></html>'''
  row=parse_detail(html,'https://www.crownmotorspdx.com/vehicle/used-2027-Ford-F450-1FT8W4DM1VEC05424/')
  self.assertFalse(validate([row]));self.assertEqual(row['availability'],'unknown')
  self.assertEqual(row['price'],'122900.00 USD')
 def test_no_picture_fails(self):
  html='<h1>2027 Ford F450</h1><p>Sale price $122,900</p>'
  row=parse_detail(html,'https://www.crownmotorspdx.com/vehicle/used-2027-Ford-F450-1FT8W4DM1VEC05424/')
  self.assertTrue(any('image_url' in e for e in validate([row])))


 def test_silver_reserve_video_and_build_sheet_choose_photo_three(self):
  preview='https://imagesdl.dealercenter.net/1024/768/preview.jpg'
  sheet='https://imagesdl.dealercenter.net/1024/768/sheet.jpg'
  truck='https://imagesdl.dealercenter.net/1024/768/exterior.jpg'
  html=f'''<h1>2027 Ford F450 Signature Reserve</h1>
  <img alt="2027 Ford F450 Signature Reserve video preview" src="{preview}">
  <img alt="2027 Ford F450 Signature Reserve - Image 1" src="{preview}">
  <img alt="2027 Ford F450 Signature Reserve - Image 2" src="{sheet}">
  <img alt="2027 Ford F450 Signature Reserve - Image 3" src="{truck}">'''
  from feed_builder import soup_from, direct_image
  self.assertEqual(direct_image(soup_from(html),vin='1FT8W4DM1VEC05424'),truck)

 def test_silver_reserve_fails_without_approved_photo(self):
  preview='https://imagesdl.dealercenter.net/1024/768/preview.jpg'
  sheet='https://imagesdl.dealercenter.net/1024/768/sheet.jpg'
  html=f'''<h1>2027 Ford F450 Signature Reserve</h1>
  <img alt="2027 Ford F450 Signature Reserve video preview" src="{preview}">
  <img alt="2027 Ford F450 Signature Reserve - Image 1" src="{preview}">
  <img alt="2027 Ford F450 Signature Reserve - Image 2" src="{sheet}">'''
  from feed_builder import soup_from, direct_image
  self.assertIsNone(direct_image(soup_from(html),vin='1FT8W4DM1VEC05424'))

 def test_other_vehicle_does_not_select_untested_promo_graphic(self):
  original='https://imagesdl.dealercenter.net/1024/768/cadillac-original.jpg'
  promotion='https://imagesdl.dealercenter.net/1024/768/cadillac-advertisement.jpg'
  html=f'''<meta property="og:image" content="{original}">
  <h1>2026 Cadillac Escalade</h1>
  <img alt="2026 Cadillac Escalade video preview" src="{original}">
  <img alt="2026 Cadillac Escalade - Image 2" src="{promotion}">'''
  from feed_builder import soup_from, direct_image
  self.assertEqual(direct_image(soup_from(html),vin='1GYS9GKL2TR310580'),original)

if __name__=='__main__':unittest.main()
