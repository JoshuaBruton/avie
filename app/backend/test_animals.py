import unittest
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
from PIL import Image
import torch
from animals import ANIMAL_CLASS_IDS,animal_species,animal_resolution_context
from pipeline import Pipeline

class AnimalTests(unittest.TestCase):
    def test_only_supported_selected_classes(self):
        self.assertEqual(animal_species({'classes':['Building']}),[])
        self.assertEqual(animal_species({'classes':['Wildlife'],'wildlifeSpecies':['Elephant','Bird','Elephant']}),['Elephant','Bird'])
        self.assertEqual(len(animal_species({'classes':['Wildlife']})),10)
        for names in ([],['Deer'],['Whale']):
            with self.assertRaises(ValueError):animal_species({'classes':['Wildlife'],'wildlifeSpecies':names})
        self.assertEqual(ANIMAL_CLASS_IDS['Elephant'],20)
        self.assertEqual(ANIMAL_CLASS_IDS['Bird'],14)
    def test_sampling_is_not_claimed_to_be_native_resolution(self):
        p=animal_resolution_context({'groundResolutionMeters':.5})
        self.assertTrue(p['experimental']);self.assertFalse(p['nativeResolutionKnown'])
        self.assertEqual(p['exampleFourMeterAnimalPixels'],8)
    def test_pipeline_routes_animals_and_vehicles_without_species_leakage(self):
        requested=[]
        class FakeModel:
            def predict(self,tile,**kwargs):
                requested.append(kwargs['classes'])
                boxes=[SimpleNamespace(cls=torch.tensor([c]),conf=torch.tensor([.8]),xyxy=torch.tensor([[100.,100.,130.,130.]])) for c in [20,7,22] if c in kwargs['classes']]
                return [SimpleNamespace(boxes=boxes,masks=None)]
        image=Image.new('RGB',(256,256),'gray')
        info={'width':256,'height':256,'bounds3857':[-128,-128,128,128],'groundResolutionMeters':1}
        config={'latitude':0,'longitude':0,'radiusKm':.5,'classes':['Wildlife','Truck'],'wildlifeSpecies':['Elephant'],'model':'yolov8n','tileSize':640,'confidence':25}
        with tempfile.TemporaryDirectory() as root:
            engine=Pipeline(root)
            with patch('pipeline.acquire',return_value=(image,info)),patch.object(engine,'load_model',return_value=FakeModel()):result=engine.run(config,root)
        self.assertEqual(set(requested[0]),{20,7})
        animal=next(d for d in result['detections'] if d['type']=='Elephant')
        truck=next(d for d in result['detections'] if d['type']=='Truck')
        self.assertEqual(animal['origin'],'animal-model');self.assertEqual(animal['category'],'Wildlife')
        self.assertIn('not validated',animal['description']);self.assertEqual(truck['origin'],'vehicle-model')
        self.assertFalse(any(d['type']=='Zebra' for d in result['detections']))
        self.assertTrue(result['wildlifeAnalysis']['experimental'])
        self.assertTrue(any('does not establish' in n for n in result['notices']))

if __name__=='__main__':unittest.main()
