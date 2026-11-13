"""Dedicated aerial-person detection on small overlapping, magnified source crops."""
import hashlib
from pathlib import Path
import requests,torch
from ultralytics import YOLO
from torchvision.ops import nms

MODEL_URL='https://huggingface.co/mshamrai/yolov8s-visdrone/resolve/996db9c3fbdf92ecdcf58411449a39232bfbcff6/best.pt'
MODEL_SHA='e3776314790b381f2eb08ed87ccec71e19a7a0308ac064adb704643b73d06947'
class PersonDetector:
    def __init__(self,model_dir):self.model_dir=Path(model_dir);self.model=None
    def load(self):
        if self.model is not None:return self.model
        path=self.model_dir/'visdrone-yolov8s.pt'
        if not path.exists():
            with requests.get(MODEL_URL,stream=True,timeout=(15,90)) as r:
                r.raise_for_status();size=0
                with path.with_suffix('.download').open('wb') as f:
                    for chunk in r.iter_content(1048576):
                        size+=len(chunk)
                        if size>30*1024*1024:raise ValueError('Person model exceeds size limit.')
                        f.write(chunk)
            path.with_suffix('.download').replace(path)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=MODEL_SHA:raise ValueError('Person model integrity check failed.')
        self.model=YOLO(str(path))
        if self.model.names.get(0)!='pedestrian' or self.model.names.get(1)!='people':raise ValueError('Unexpected aerial-person model classes.')
        return self.model
    def predict(self,frame,threshold=.15,progress=lambda **kw:None):
        from pipeline import window_starts
        model=self.load();h,w=frame.shape[:2];windows=[(x,y) for y in window_starts(h,320,.25) for x in window_starts(w,320,.25)];boxes=[];scores=[];labels=[]
        for i,(x,y) in enumerate(windows,1):
            result=model.predict(frame[y:y+320,x:x+320],imgsz=960,classes=[0,1],conf=threshold,device='cpu',verbose=False,iou=.4,max_det=150)[0]
            for b in result.boxes:
                a=b.xyxy[0].detach().cpu().tolist();boxes.append([a[0]+x,a[1]+y,a[2]+x,a[3]+y]);scores.append(float(b.conf[0]));labels.append(model.names[int(b.cls[0])])
            progress(stage=f'Aerial human search · {i}/{len(windows)} small crops',progress=55+int(14*i/len(windows)))
        keep=nms(torch.tensor(boxes,dtype=torch.float32),torch.tensor(scores),.35).tolist() if boxes else []
        return [{'box':boxes[i],'score':scores[i],'sourceClass':labels[i]} for i in keep[:300]],{'status':'available','model':'YOLOv8s-VisDrone','source':'https://huggingface.co/mshamrai/yolov8s-visdrone','sha256':MODEL_SHA,'license':'Model card: OpenRAIL; VisDrone data: research use; Ultralytics license also applies','trainingDomain':'Drone/aerial imagery; AVIE satellite accuracy is unvalidated','cropPixels':320,'inferencePixels':960,'overlap':.25,'threshold':threshold,'tiles':len(windows),'magnificationAddsSourceDetail':False,'countIsCensus':False,'accuracyImprovementMeasured':False}
