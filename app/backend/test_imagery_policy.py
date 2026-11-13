import base64
import io
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from imagery_policy import assess_imagery, capture_label, load_baseline
from pipeline import Pipeline


def eligible():
    return dict(provider='Historical survey', sourceType='aerial', nativeGsdCm=3,
                groundResolutionMeters=.03, licenseReference='Contract',
                analysisPermitted=True, displayPermitted=True, width=256, height=256,
                bounds3857=[-3.84,-3.84,3.84,3.84],captureDate='2001-01-01')


class ImageryPolicyTests(unittest.TestCase):
    def test_age_and_capture_precision(self):
        self.assertTrue(assess_imagery(eligible())['eligible'])
        self.assertEqual(capture_label(eligible()),'2001-01-01 (capture time unavailable)')
        self.assertEqual(capture_label({'acquiredAt':'2026-11-13T12:00:00Z'}),'Capture date/time unavailable')
        self.assertEqual(capture_label({'captureDateRange':{'start':'2001-01-01','end':'2001-12-31'}}),'2001-01-01 to 2001-12-31 (exact capture date/time unavailable)')
        for bad in [None,True,'3',0,6,float('nan')]:
            self.assertFalse(assess_imagery({**eligible(),'nativeGsdCm':bad})['eligible'])
        self.assertFalse(assess_imagery({**eligible(),'groundResolutionMeters':.1})['eligible'])

    def test_native_image_is_not_resized_and_dimensions_are_checked(self):
        raw=io.BytesIO();Image.new('RGB',(256,256),'green').save(raw,format='PNG')
        record={'imagery':eligible(),'imageBase64':base64.b64encode(raw.getvalue()).decode()}
        image,info=load_baseline(record);self.assertEqual(image.size,(256,256))
        with self.assertRaises(ValueError):load_baseline({**record,'imagery':{**eligible(),'width':300}})

    def test_unverified_context_never_invokes_detectors_or_implies_absence(self):
        config={'latitude':0,'longitude':0,'radiusKm':.05,'classes':['Living Organisms','Building','Unknown feature'],'organismCategories':['Humans','Land Mammals','Unclassified Wildlife'],'useAerialPeople':True,'useAerialWildlife':True,'model':'yolov8n','tileSize':640,'confidence':30}
        info={**eligible(),'sourceType':'context','nativeGsdCm':None}
        with tempfile.TemporaryDirectory() as folder:
            engine=Pipeline(folder)
            with patch('pipeline.acquire',return_value=(Image.new('RGB',(256,256)),info)),patch.object(engine,'load_model') as models,patch.object(engine,'load_building_model') as buildings,patch.object(engine.people,'predict') as people,patch.object(engine.overhead,'predict') as animals,patch('pipeline.propose_features') as features:
                report=engine.run(config,folder)
                for mock in [models,buildings,people,animals,features]:mock.assert_not_called()
        self.assertEqual(report['detectionStatus'],'not_run_insufficient_imagery')
        self.assertEqual(report['humanAnalysis']['status'],'not_assessed_insufficient_imagery')
        self.assertEqual(report['detections'],[])
        self.assertIn('not current conditions',report['findingsContext'])


if __name__=='__main__':unittest.main()
