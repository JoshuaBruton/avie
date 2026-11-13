"""OWL-C overhead animal localization. Heatmap scores are not probabilities."""
from pathlib import Path
import hashlib,time
import requests
import numpy as np
import torch
from torch.nn import functional as F
from third_party.owl_c import OWLC

OWL_URL='https://zenodo.org/api/records/20802844/files/OWL-C.pth/content'
OWL_SHA256='de97b6bbc50e20d914b179372a1ea42c569795591a3cf33b926ba1a6e659939a'
OWL_SIZE=216392299

def deduplicate_points(points,distance=12):
    kept=[];cells={};distance_sq=distance**2
    for p in sorted(points,key=lambda p:p['score'],reverse=True):
        gx,gy=int(p['x']//distance),int(p['y']//distance)
        if any((p['x']-q['x'])**2+(p['y']-q['y'])**2<distance_sq for dx in (-1,0,1) for dy in (-1,0,1) for q in cells.get((gx+dx,gy+dy),[])):continue
        kept.append(p);cells.setdefault((gx,gy),[]).append(p)
    return kept

class OverheadLocator:
    def __init__(self,model_dir):self.model_dir=Path(model_dir);self.model=None
    def load(self,progress=lambda **kw:None):
        if self.model is not None:return self.model
        path=self.model_dir/'OWL-C.pth';path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            temp=path.with_suffix('.download');downloaded=0;last=time.monotonic()
            with requests.get(OWL_URL,stream=True,timeout=(15,90)) as response:
                response.raise_for_status()
                with temp.open('wb') as stream:
                    for chunk in response.iter_content(1024*1024):
                        downloaded+=len(chunk)
                        if downloaded>OWL_SIZE:raise ValueError('Overhead checkpoint exceeds the published size.')
                        stream.write(chunk)
                        if time.monotonic()-last>4:progress(stage=f'Loading aerial wildlife model · {downloaded//1000000}/{OWL_SIZE//1000000} MB',progress=70);last=time.monotonic()
            temp.replace(path)
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
        if path.stat().st_size!=OWL_SIZE or digest.hexdigest()!=OWL_SHA256:raise ValueError('Overhead checkpoint integrity check failed.')
        checkpoint=torch.load(path,map_location='cpu',weights_only=True,mmap=True);state=checkpoint['model_state_dict'];model=OWLC(pretrained=False,down_ratio=2,head_conv=64)
        state={k.removeprefix('model.'):v for k,v in state.items()};model.load_state_dict(state,strict=True);self.model=model.eval().requires_grad_(False);return self.model
    def predict(self,rgb,threshold=.35,progress=lambda **kw:None):
        model=self.load(progress);height,width=rgb.shape[:2];h=max(512,(height+1)//2*2);w=max(512,(width+1)//2*2)
        array=np.asarray(rgb,dtype=np.float32)/255.;array=(array-np.array([.485,.456,.406],dtype=np.float32))/np.array([.229,.224,.225],dtype=np.float32)
        tensor=torch.from_numpy(array).permute(2,0,1).unsqueeze(0).contiguous();tensor=F.pad(tensor,(0,w-width,0,h-height))
        def starts(length):
            values=list(range(0,length-512+1,352))
            if values[-1]!=length-512:values.append(length-512)
            return values
        windows=[(x,y) for y in starts(h) for x in starts(w)];sums=torch.zeros((1,1,h//2,w//2));counts=torch.zeros_like(sums)
        with torch.inference_mode():
            for i,(x,y) in enumerate(windows,1):
                heat=model(tensor[:,:,y:y+512,x:x+512]).cpu();sums[:,:,y//2:y//2+256,x//2:x//2+256]+=heat;counts[:,:,y//2:y//2+256,x//2:x//2+256]+=1
                progress(stage=f'Aerial wildlife locator · {i}/{len(windows)} tiles',progress=71+int(13*i/len(windows)))
        heat=(sums/counts.clamp_min(1))[:,:,:height//2,:width//2]
        if not torch.isfinite(heat).all():raise ValueError('Invalid overhead heatmap.')
        maximum=float(heat.max());cutoff=max(float(threshold),.3*maximum,.1);peaks=(heat==F.max_pool2d(heat,3,stride=1,padding=1))&(heat>=cutoff)
        points=[{'x':float(x*2),'y':float(y*2),'score':float(heat[0,0,y,x])} for y,x in torch.nonzero(peaks[0,0],as_tuple=False).tolist()]
        points=deduplicate_points(points)[:500]
        return points,{'status':'available','model':'OWL-C','domain':'Aerial/drone wildlife localization; AVIE satellite performance not validated','checkpoint':OWL_URL,'sha256':OWL_SHA256,'license':'CC BY-NC-SA 4.0','licenseUrl':'https://creativecommons.org/licenses/by-nc-sa/4.0/','source':'https://github.com/microsoft/MegaDetector-Overhead','threshold':threshold,'scoreType':'Localization heatmap activation; not a calibrated probability','geometry':'Point locations with fixed review windows; not animal outlines','tiles':len(windows),'accuracyImprovementMeasured':False}
