import unittest
import numpy as np
import cv2
from features import propose_features
from pipeline import window_starts,imagery_plan,project,unproject

class FeatureTests(unittest.TestCase):
    def test_unknown_proposals_do_not_invent_confidence(self):
        image=np.full((512,512,3),70,dtype=np.uint8)
        cv2.circle(image,(180,200),35,(245,245,245),-1)
        p=propose_features(image,.5)
        self.assertGreaterEqual(len(p),1)
        self.assertTrue(all('confidence' not in x for x in p))
        self.assertTrue(all('unknown' in x['description'] for x in p))
        self.assertEqual(propose_features(image,.5,[p[0]['box']]),[])
    def test_tiles_cover_small_and_large_images(self):
        for width in (128,211,422,640,2110,4096):
            for size in (512,640,1024):
                starts=window_starts(width,size)
                self.assertEqual(starts[0],0)
                self.assertGreaterEqual(starts[-1]+size,width)
                self.assertTrue(all(b-a<=size for a,b in zip(starts,starts[1:])))
    def test_closeup_georeferencing_and_requested_detail(self):
        p=imagery_plan({'latitude':37.2232,'longitude':38.9214,'radiusKm':.05,'zoom':20})
        self.assertLessEqual(p['width'],4096)
        lat,lon=unproject(*project(37.2232,38.9214))
        self.assertAlmostEqual(lat,37.2232)
        self.assertAlmostEqual(lon,38.9214)
        self.assertEqual(p['requestedZoom'],20)
    def test_antimeridian_explicitly_rejected(self):
        with self.assertRaises(ValueError):imagery_plan({'latitude':0,'longitude':179.99,'radiusKm':5})

if __name__=='__main__':unittest.main()
