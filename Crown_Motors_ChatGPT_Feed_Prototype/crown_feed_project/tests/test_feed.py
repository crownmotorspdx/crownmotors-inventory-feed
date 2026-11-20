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


 def test_numbered_gallery_beats_video_preview(self):
  video='https://imagesdl.dealercenter.net/1024/768/video-preview.jpg'
  correct='https://imagesdl.dealercenter.net/1024/768/first-real-photo.jpg'
  unrelated='https://imagesdl.dealercenter.net/1024/768/related-truck.jpg'
  html=f'''<html><head><meta property="og:image" content="{video}"></head><body>
  <h1>2027 Ford F450 Platinum</h1>
  <img src="{video}" alt="2027 Ford F450 Platinum video preview">
  <img src="{correct}" alt="2027 Ford F450 Platinum - Image 2">
  <img src="{unrelated}" alt="Other truck - Image 1">
  </body></html>'''
  from feed_builder import direct_image, soup_from
  self.assertEqual(direct_image(soup_from(html)),correct)

 def test_numbered_gallery_one_is_first(self):
  a='https://imagesdl.dealercenter.net/1024/768/photo1.jpg'
  b='https://imagesdl.dealercenter.net/1024/768/photo2.jpg'
  html=f'''<h1>2027 Ford F450 Neptune Blue</h1>
  <img src="{b}" alt="2027 Ford F450 Neptune Blue - Image 2">
  <img src="{a}" alt="2027 Ford F450 Neptune Blue - Image 1">'''
  from feed_builder import direct_image, soup_from
  self.assertEqual(direct_image(soup_from(html)),a)

 def test_gallery_falls_back_when_not_numbered(self):
  preview='https://imagesdl.dealercenter.net/1024/768/known-photo.jpg'
  html=f'''<meta property="og:image" content="{preview}"><h1>2027 Ford F450</h1>'''
  from feed_builder import direct_image, soup_from
  self.assertEqual(direct_image(soup_from(html)),preview)

if __name__=='__main__':unittest.main()
