import unittest,tempfile
from unittest.mock import patch
from types import SimpleNamespace
from PIL import Image
import torch
from animals import animal_species,organism_categories,needs_person_detector,needs_overhead_locator
from overhead import deduplicate_points
from pipeline import Pipeline

class OrganismTests(unittest.TestCase):
    def test_routing_and_review_only_categories(self):
        base={'classes':['Living Organisms']}
        marine={**base,'organismCategories':['Aquatic/Marine Animals','Reptilian Creatures']}
        self.assertEqual(animal_species(marine),[])
        self.assertFalse(needs_person_detector(marine));self.assertFalse(needs_overhead_locator(marine))
        self.assertTrue(needs_person_detector({**base,'organismCategories':['Humans']}))
        self.assertFalse(needs_overhead_locator({**base,'organismCategories':['Humans']}))
        land={**base,'organismCategories':['Land Mammals']}
        self.assertNotIn('Bird',animal_species(land));self.assertTrue(needs_overhead_locator(land))
        self.assertFalse(needs_overhead_locator({**land,'useAerialWildlife':False}))
        with self.assertRaises(ValueError):organism_categories({**base,'organismCategories':['Whale']})
    def test_peak_deduplication_keeps_highest_score(self):
        points=deduplicate_points([{'x':10,'y':10,'score':.2},{'x':11,'y':11,'score':.8},{'x':50,'y':50,'score':.4}])
        self.assertEqual(len(points),2);self.assertEqual(points[0]['score'],.8)
    def test_spatial_corroboration_and_unclassified_points_keep_distinct_evidence(self):
        class Model:
            def predict(self,*args,**kw):return [SimpleNamespace(boxes=[SimpleNamespace(cls=torch.tensor([20]),conf=torch.tensor([.8]),xyxy=torch.tensor([[100.,100.,130.,130.]]))],masks=None)]
        image=Image.new('RGB',(256,256),'gray');info={'width':256,'height':256,'bounds3857':[-3.84,-3.84,3.84,3.84],'groundResolutionMeters':.03,'sourceType':'aerial','provider':'Test survey','nativeGsdCm':3,'licenseReference':'Test licence','analysisPermitted':True,'displayPermitted':True}
        c={'latitude':0,'longitude':0,'radiusKm':.5,'classes':['Living Organisms'],'organismCategories':['Land Mammals','Unclassified Wildlife'],'model':'yolov8n','tileSize':640,'confidence':25}
        with tempfile.TemporaryDirectory() as root:
            e=Pipeline(root)
            with patch('pipeline.acquire',return_value=(image,info)),patch.object(e,'load_model',return_value=Model()),patch.object(e.overhead,'predict',return_value=([{'x':115,'y':115,'score':.75},{'x':180,'y':180,'score':.6}],{'status':'available'})):
                r=e.run(c,root)
        a,b=r['detections'];self.assertEqual(a['wildlifeFlag'],'probable');self.assertEqual(a['organismGroup'],'Land Mammals')
        self.assertEqual(b['wildlifeFlag'],'possible');self.assertIsNone(b['confidence']);self.assertIsNone(b['dimensionsMeters']);self.assertTrue(b['reviewWindowOnly']);self.assertEqual(b['category'],'Living Organisms')
        self.assertFalse(r['organismAnalysis']['accuracyImprovementMeasured'])
