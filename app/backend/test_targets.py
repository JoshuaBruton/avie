import unittest,tempfile
from unittest.mock import patch
from types import SimpleNamespace
import requests
import torch
from PIL import Image
from pipeline import Pipeline,vehicle_class_ids
from animals import animal_species
from agriculture import mapped_features,clip_polygon,fetch_agriculture

class TargetTests(unittest.TestCase):
    def test_road_transport_group_and_legacy_inputs(self):
        self.assertEqual(set(vehicle_class_ids({'classes':['Road Transport']})),{2,5,7})
        self.assertEqual(set(vehicle_class_ids({'classes':['Road Transport','Train','Boat']})),{2,5,7,6,8})
        self.assertNotIn(4,vehicle_class_ids({'classes':['Road Transport','Train','Boat']}))
        self.assertEqual(vehicle_class_ids({'classes':['Car']}),[2])
    def test_person_only_and_living_animal_selections(self):
        self.assertEqual(animal_species({'classes':['Living Organisms'],'wildlifeSpecies':[]}),[])
        self.assertEqual(animal_species({'classes':['Living Organisms'],'wildlifeSpecies':['Bird']}),['Bird'])
        with self.assertRaises(ValueError):animal_species({'classes':['Wildlife','Living Organisms'],'wildlifeSpecies':[]})
    def test_living_targets_include_person_and_selected_animals_once(self):
        requested=[]
        class Model:
            def predict(self,tile,**kwargs):
                requested.append(kwargs['classes']);boxes=[SimpleNamespace(cls=torch.tensor([i]),conf=torch.tensor([.7]),xyxy=torch.tensor([[100.,100.,130.,130.]])) for i in [0,14,20,2,5,7] if i in kwargs['classes']]
                return [SimpleNamespace(boxes=boxes,masks=None)]
        image=Image.new('RGB',(256,256),'gray');info={'width':256,'height':256,'bounds3857':[-3.84,-3.84,3.84,3.84],'groundResolutionMeters':.03,'sourceType':'aerial','provider':'Test survey','nativeGsdCm':3,'licenseReference':'Test licence','analysisPermitted':True,'displayPermitted':True}
        c={'latitude':0,'longitude':0,'radiusKm':.5,'classes':['Road Transport','Wildlife','Living Organisms'],'wildlifeSpecies':['Bird'],'model':'yolov8n','tileSize':640,'confidence':25}
        with tempfile.TemporaryDirectory() as root:
            engine=Pipeline(root)
            with patch('pipeline.acquire',return_value=(image,info)),patch.object(engine,'load_model',return_value=Model()):r=engine.run(c,root)
        self.assertEqual(set(requested[0]),{0,14,2,5,7});self.assertEqual(len(requested[0]),len(set(requested[0])))
        person=next(d for d in r['detections'] if d['type']=='Person');self.assertEqual(person['origin'],'person-model');self.assertEqual(person['category'],'Living Organisms')
        self.assertTrue(any('does not identify people' in n for n in r['notices']))
    def test_crop_tags_are_map_evidence_not_image_predictions(self):
        info={'width':1000,'height':1000,'bounds3857':[-1000,-1000,1000,1000]}
        geometry=[{'lat':-.003,'lon':-.003},{'lat':-.003,'lon':.003},{'lat':.003,'lon':.003},{'lat':.003,'lon':-.003},{'lat':-.003,'lon':-.003}]
        features=mapped_features([{'id':1,'type':'way','tags':{'landuse':'farmland','crop':'wheat'},'geometry':geometry},{'id':2,'type':'way','tags':{'landuse':'vineyard'},'geometry':geometry}],info)
        self.assertEqual(len(features),2);self.assertEqual(features[0]['cropFromMap'],'wheat');self.assertIsNone(features[1]['cropFromMap']);self.assertNotIn('confidence',features[0]);self.assertIn('not an image-based',features[0]['description'])
        clipped=clip_polygon([[-10,-10],[110,-10],[110,110],[-10,110]],100,100)
        self.assertTrue(all(0<=x<=100 and 0<=y<=100 for x,y in clipped))
    def test_unavailable_agriculture_does_not_claim_absence(self):
        config={'latitude':0,'longitude':0,'radiusKm':.1};info={'width':100,'height':100,'bounds3857':[-100,-100,100,100]}
        with patch('agriculture.read_map_api',side_effect=ValueError('unavailable')),patch('agriculture.requests.get',side_effect=requests.RequestException('unavailable')):
            features,meta,notice=fetch_agriculture(config,info,lambda **kw:None)
        self.assertEqual(features,[]);self.assertEqual(meta['status'],'unavailable');self.assertFalse(meta['imageCropClassification']);self.assertIn('not evidence',notice)

if __name__=='__main__':unittest.main()
