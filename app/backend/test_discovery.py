import unittest,tempfile
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
import cv2,numpy as np,torch
import xml.etree.ElementTree as ET
from PIL import Image
from archaeology import propose_archaeology,mapped_heritage
from people import PersonDetector
from pipeline import Pipeline

class DiscoveryTests(unittest.TestCase):
    def test_blank_terrain_is_not_a_site_and_cluster_search_is_coordinate_free(self):
        frame=np.full((256,256,3),(50,110,55),np.uint8)
        self.assertEqual(propose_archaeology(frame,.2),[])
        for angle in range(0,360,30):
            x=128+round(45*np.cos(np.deg2rad(angle)));y=128+round(45*np.sin(np.deg2rad(angle)))
            cv2.rectangle(frame,(x,y),(x+7,y+10),(140,145,140),-1);cv2.rectangle(frame,(x+4,y-10),(x+10,y),(15,35,18),-1)
        ps=propose_archaeology(frame,.2)
        self.assertTrue(ps);self.assertTrue(any(p['box'][0]<130<p['box'][2] and p['box'][1]<130<p['box'][3] for p in ps));self.assertTrue(all('NOT established' in p['description'] for p in ps))
    def test_map_identity_is_independent_of_image_discovery(self):
        root=ET.fromstring('<osm><node id="1" lat="0" lon="0"><tag k="historic" v="archaeological_site"/><tag k="name" v="Known site"/></node><node id="2" lat="40" lon="40"><tag k="historic" v="ruins"/></node></osm>')
        findings=mapped_heritage(root,{'bounds3857':[-100,-100,100,100],'width':1000,'height':1000,'groundResolutionMeters':.2})
        self.assertEqual(len(findings),1);self.assertEqual(findings[0]['label'],'Known site');self.assertIn('not an image-model discovery',findings[0]['description'])
    def test_aerial_human_tiles_are_magnified_and_duplicates_removed(self):
        class Model:
            names={0:'pedestrian',1:'people'}
            def predict(self,tile,**kw):
                self.kw=kw
                return [SimpleNamespace(boxes=[SimpleNamespace(cls=torch.tensor([0]),conf=torch.tensor([.6]),xyxy=torch.tensor([[10.,10.,20.,30.]])),SimpleNamespace(cls=torch.tensor([1]),conf=torch.tensor([.5]),xyxy=torch.tensor([[10.,10.,20.,30.]]))])]
        with tempfile.TemporaryDirectory() as root:
            d=PersonDetector(root);d.model=Model();findings,meta=d.predict(np.zeros((200,200,3),np.uint8),.15)
        self.assertEqual(len(findings),1);self.assertEqual(meta['inferencePixels'],960);self.assertEqual(meta['cropPixels'],320);self.assertFalse(meta['countIsCensus'])
    def test_pipeline_keeps_mapped_and_image_sources_separate(self):
        info={'width':256,'height':256,'bounds3857':[-3.84,-3.84,3.84,3.84],'groundResolutionMeters':.03,'sourceType':'aerial','provider':'Test survey','nativeGsdCm':3,'licenseReference':'Test licence','analysisPermitted':True,'displayPermitted':True}
        c={'latitude':0,'longitude':0,'radiusKm':.5,'classes':['Archaeology','Living Organisms'],'organismCategories':['Humans'],'useAerialPeople':True,'personConfidence':15,'model':'yolov8n','tileSize':640,'confidence':31}
        model=SimpleNamespace(predict=lambda *a,**k:[SimpleNamespace(boxes=[],masks=None)])
        proposal={'box':[90,90,140,140],'polygon':[[90,90],[140,90],[140,140]],'rank':2.,'componentCount':8,'description':'Image geometry candidate'}
        heritage={'box':[90,90,140,140],'polygon':None,'label':'Known site','mapTags':{'historic':'ruins'},'osmElementId':'1','osmElementType':'node','mapUrl':'https://www.openstreetmap.org/node/1','description':'Mapped context'}
        with tempfile.TemporaryDirectory() as root:
            e=Pipeline(root)
            with patch('pipeline.acquire',return_value=(Image.new('RGB',(256,256),'green'),info)),patch.object(e,'load_model',return_value=model),patch.object(e.people,'predict',return_value=([{'box':[150,150,160,165],'score':.3,'sourceClass':'pedestrian'}],{'status':'available'})),patch('pipeline.propose_archaeology',return_value=[proposal]),patch('pipeline.fetch_heritage',return_value=([heritage],{'status':'available'})):
                r=e.run(c,root)
        self.assertEqual(r['analysisVersion'],7);self.assertTrue(r['humanAnalysis']);self.assertEqual(len(r['detections']),3)
        a=next(d for d in r['detections'] if d['origin']=='archaeology-proposal');b=next(d for d in r['detections'] if d['origin']=='mapped-heritage')
        self.assertTrue(a['isImageDiscovery']);self.assertFalse(b['isImageDiscovery']);self.assertIsNone(a['confidence']);self.assertIsNone(b['confidence']);self.assertFalse(r['archaeologyAnalysis']['ageOrHumanOriginConfirmed'])

class TrainingTests(unittest.TestCase):
    def fixture(self,path,sites):
        import io,json,zipfile
        buffer=io.BytesIO();Image.new('RGB',(24,24),'gray').save(buffer,format='JPEG');examples=[]
        with zipfile.ZipFile(path,'w') as z:
            for i in range(60):
                site=i%sites;name=f'crops/sample-{i}.jpg';z.writestr(name,buffer.getvalue());examples.append({'id':f'sample-{i}','imageFile':name,'reviewed':True,'label':'human' if i<30 else 'not-human','rootScanId':f'scan-{site}','latitude':site*.1,'longitude':0,'bboxCropNormalized':[.25,.25,.75,.75]})
            z.writestr('manifest.json',json.dumps({'format':'avie-reviewed-examples-v1','examples':examples}))
    def test_single_site_is_not_independent_validation(self):
        from train_people import prepare
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);self.fixture(root/'data.zip',1)
            with self.assertRaisesRegex(ValueError,'3 geographically separated'):prepare(root/'data.zip',root/'output')
    def test_reviewed_positives_and_negatives_split_by_site(self):
        from train_people import prepare
        import json
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);self.fixture(root/'data.zip',3);dataset=prepare(root/'data.zip',root/'output');self.assertTrue(dataset.exists());p=json.loads((root/'output'/'split-provenance.json').read_text());splits={}
            for e in p['examples']:splits.setdefault(e['rootScanId'],set()).add(e['split'])
            self.assertTrue(all(len(v)==1 for v in splits.values()));self.assertEqual(set(e['split'] for e in p['examples']),{'train','val'})
