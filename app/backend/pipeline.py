"""Real satellite-image acquisition, overlapping YOLO tiles, and geospatial reports."""
from __future__ import annotations
import io, math, os, time, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image, UnidentifiedImageError
from geopy.distance import geodesic
import torch
from torchvision.ops import batched_nms
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ultralytics import YOLO
from features import propose_features,overlap as overlap_people
from animals import ANIMAL_CLASS_IDS, ANIMAL_COLORS, animal_species, animal_resolution_context, organism_categories, needs_person_detector, needs_overhead_locator
from agriculture import fetch_agriculture
from overhead import OverheadLocator
from archaeology import propose_archaeology,fetch_heritage
from people import PersonDetector
from imagery_policy import assess_imagery, capture_label, load_baseline
from datetime import datetime, timezone

EARTH_RADIUS=6378137.0
CLASS_IDS={'Car':2,'Truck':7,'Boat':8,'Airplane':4,'Bus':5,'Train':6}

def vehicle_class_ids(config):
    targets=config.get('classes',[])
    labels=[name for name in CLASS_IDS if name in targets]
    if 'Road Transport' in targets:labels+=['Car','Truck','Bus']
    return list(dict.fromkeys(CLASS_IDS[name] for name in labels))
COLORS={'Car':'#b0ee84','Truck':'#79c2ec','Boat':'#edb674','Airplane':'#bd9ae9','Bus':'#e58aaa','Train':'#7ed5c7','Building':'#65d8d1','Unknown feature':'#f3c76b','Person':'#8daaf4','Agriculture':'#a6c96c','Structure candidate':'#f0cb79','Mapped heritage':'#76cddd','Unclassified wildlife':'#f3c76b',**ANIMAL_COLORS}
SOURCE='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export'

def project(lat,lon):
    return EARTH_RADIUS*math.radians(lon),EARTH_RADIUS*math.log(math.tan(math.pi/4+math.radians(lat)/2))
def unproject(x,y):
    return math.degrees(2*math.atan(math.exp(y/EARTH_RADIUS))-math.pi/2),math.degrees(x/EARTH_RADIUS)
def window_starts(length,size,overlap=.2):
    if length<=size:return [0]
    starts=list(range(0,length-size+1,max(1,int(size*(1-overlap)))))
    if starts[-1]!=length-size:starts.append(length-size)
    return starts

def imagery_plan(config):
    lat,lon=config['latitude'],config['longitude']
    x,y=project(lat,lon)
    # Geodesic cardinal limits include the full requested radius in Web Mercator.
    corners=[geodesic(kilometers=config['radiusKm']).destination((lat,lon),b) for b in (0,90,180,270)]
    north,east,south,west=corners
    half_x=max(abs(project(east.latitude,east.longitude)[0]-x),abs(project(west.latitude,west.longitude)[0]-x))
    half_y=max(abs(project(north.latitude,north.longitude)[1]-y),abs(project(south.latitude,south.longitude)[1]-y))
    # Crossing the antimeridian needs wrapped imagery requests, which this version rejects.
    if abs(east.longitude-lon)>180 or abs(west.longitude-lon)>180:raise ValueError('This area crosses the antimeridian. Move the center or reduce the radius.')
    half=max(half_x,half_y)
    width=min(4096,max(128,math.ceil(2*half/(2*math.pi*EARTH_RADIUS/(256*2**int(config.get('zoom',18)))))))
    return {'bounds3857':[x-half,y-half,x+half,y+half],'width':width,'height':width,'groundResolutionMeters':round(2*config['radiusKm']*1000/width,3),'center':{'latitude':lat,'longitude':lon},'radiusKm':config['radiusKm'],'provider':'Esri World Imagery','attribution':'Esri, Maxar, Earthstar Geographics, and the GIS User Community','sourceType':'context','nativeGsdCm':None,'capturedAt':None,'captureDateRange':None,'analysisPermitted':False,'displayPermitted':False,'captureDate':None,'acquiredAt':None,'historical':True,'requestedZoom':int(config.get('zoom',18)),'detailNote':'Requested pixel spacing does not guarantee native source detail. The provider may resample imagery.'}

def acquire(config,progress):
    if config.get('source')=='aerial':
        image,info=load_baseline(config['_baseline'])
        info['acquiredAt']=datetime.now(timezone.utc).isoformat()
        info['center']={'latitude':config['latitude'],'longitude':config['longitude']}
        info['radiusKm']=config['radiusKm']
        return image,info
    requested_zoom=int(config.get('zoom',18));info=None
    # Some regions have no imagery at the requested fine scale. Probe the export
    # scale first, then reacquire at a supported scale instead of returning blank
    # tiles or silently upsampling the old overview.
    for candidate_zoom in range(requested_zoom,15,-1):
        candidate=imagery_plan({**config,'zoom':candidate_zoom});a,b,c,d=candidate['bounds3857'];resolution=(c-a)/candidate['width'];cx=(a+c)/2;cy=(b+d)/2;half=128*resolution
        progress(stage=f'Checking imagery detail · level {candidate_zoom}',progress=1,imagery=candidate)
        try:
            probe=requests.get(SOURCE,params={'f':'image','bbox':f'{cx-half},{cy-half},{cx+half},{cy+half}','bboxSR':3857,'imageSR':3857,'size':'256,256','format':'jpg'},timeout=(15,30))
            if probe.ok and probe.headers.get('Content-Type','').startswith('image/'):
                info=candidate;info['requestedZoom']=requested_zoom;info['samplingZoom']=candidate_zoom;info['detailLimited']=candidate_zoom<requested_zoom;break
        except requests.RequestException:
            if candidate_zoom==16:raise
    if info is None:raise RuntimeError('The imagery provider has no image available for this location and scale.')
    width=info['width'];height=info['height'];left,bottom,right,top=info['bounds3857'];patches=[(x,y,min(1024,width-x),min(1024,height-y)) for y in range(0,height,1024) for x in range(0,width,1024)]
    mosaic=Image.new('RGB',(width,height))
    def fetch(patch):
        x,y,w,h=patch;params={'f':'image','bbox':','.join(map(str,[left+x/width*(right-left),top-(y+h)/height*(top-bottom),left+(x+w)/width*(right-left),top-y/height*(top-bottom)])),'bboxSR':3857,'imageSR':3857,'size':f'{w},{h}','format':'jpg','transparent':'false'}
        with requests.Session() as session:
            session.mount('https://',HTTPAdapter(max_retries=Retry(total=2,backoff_factor=.5,status_forcelist=[429,500,502,503,504])))
            r=session.get(SOURCE,params=params,timeout=(15,60));r.raise_for_status()
            if not r.headers.get('Content-Type','').startswith('image/'):
                raise RuntimeError('The imagery provider did not return an image. Please try a smaller area.')
            try:
                image=Image.open(io.BytesIO(r.content)).convert('RGB')
            except UnidentifiedImageError as exc:raise RuntimeError('The imagery provider returned unreadable image data.') from exc
            if image.size!=(w,h):raise RuntimeError('The imagery provider returned an unexpected image size.')
            return patch,image
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures=[executor.submit(fetch,p) for p in patches]
        for completed,future in enumerate(as_completed(futures),1):
            (x,y,w,h),image=future.result();mosaic.paste(image,(x,y));progress(stage=f'Acquiring imagery · {completed}/{len(patches)} image sections',progress=2+int(25*completed/len(patches)),imagery=info)
    from datetime import datetime,timezone
    info['acquiredAt']=datetime.now(timezone.utc).isoformat()
    return mosaic,info

class Pipeline:
    def __init__(self,model_dir):
        self.model_dir=Path(model_dir);self.model_dir.mkdir(parents=True,exist_ok=True);self.models={};self.overhead=OverheadLocator(self.model_dir);self.people=PersonDetector(self.model_dir)
        torch.set_num_threads(int(os.environ.get('AVIE_TORCH_THREADS','2')))
    def load_model(self,name):
        if name not in ('yolov8n','yolov8s','yolov8m'):raise ValueError('Unsupported model.')
        if name not in self.models:
            path=self.model_dir/f'{name}.pt'
            if not path.exists():
                response=requests.get(f'https://github.com/ultralytics/assets/releases/download/v8.3.0/{name}.pt',timeout=(15,120));response.raise_for_status();tmp=path.with_suffix('.download');tmp.write_bytes(response.content);tmp.replace(path)
            self.models[name]=YOLO(str(path))
        return self.models[name]
    def load_building_model(self):
        name='buildings-yolov8n'
        if name not in self.models:
            path=self.model_dir/(name+'.pt')
            if not path.exists():
                response=requests.get('https://huggingface.co/keremberke/yolov8n-building-segmentation/resolve/main/best.pt',timeout=(15,120));response.raise_for_status();tmp=path.with_suffix('.download');tmp.write_bytes(response.content);tmp.replace(path)
            self.models[name]=YOLO(str(path))
        return self.models[name]
    def run(self,config,output_dir,progress=lambda **kw:None):
        start=time.monotonic();output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
        analysis_at=datetime.now(timezone.utc).isoformat()
        image,info=acquire(config,progress)
        config={k:v for k,v in config.items() if k!='_baseline'}
        assessment=assess_imagery(info);eligible=assessment['eligible']
        image.save(output_dir/'imagery.jpg',quality=90)
        frame=cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR);size=config['tileSize'];width,height=image.size
        windows=[(x,y) for y in window_starts(height,size) for x in window_starts(width,size)]
        detectors=[]
        vehicle_ids=vehicle_class_ids(config) if eligible else []
        species=animal_species(config) if eligible else [];animal_ids=[ANIMAL_CLASS_IDS[name] for name in species]
        groups=organism_categories(config);use_overhead=eligible and needs_overhead_locator(config);person_ids=[0] if eligible and needs_person_detector(config) else []
        if vehicle_ids or animal_ids or person_ids:detectors.append((self.load_model(config['model']),vehicle_ids+animal_ids+person_ids,'object-model'))
        if eligible and 'Building' in config['classes']:
            progress(stage='Loading satellite building-footprint model',progress=28,tileCount=len(windows),imagery=info)
            detectors.append((self.load_building_model(),[0],'building-model'))
        boxes=[];scores=[];class_ids=[];origins=[];polygons=[];sources=[];reverse_ids={v:k for k,v in {**CLASS_IDS,**ANIMAL_CLASS_IDS}.items()};reverse_ids[100]='Building';reverse_ids[0]='Person'
        total_inferences=max(1,len(windows)*len(detectors));completed=0
        for model,ids,source in detectors:
            for index,(x,y) in enumerate(windows):
                tile=frame[y:y+size,x:x+size]
                result=model.predict(tile,imgsz=size,conf=config['confidence']/100,classes=ids,device='cpu',verbose=False,iou=.45,max_det=300)[0]
                for b,box in enumerate(result.boxes):
                    coords=box.xyxy[0].detach().cpu().tolist();coords=[coords[0]+x,coords[1]+y,coords[2]+x,coords[3]+y]
                    boxes.append(coords);scores.append(float(box.conf[0]));class_ids.append(100 if source=='building-model' else int(box.cls[0]));origins.append(index+1);sources.append('building-model' if source=='building-model' else 'person-model' if int(box.cls[0])==0 else 'animal-model' if int(box.cls[0]) in ANIMAL_CLASS_IDS.values() else 'vehicle-model')
                    polygon=None
                    if result.masks is not None and b<len(result.masks.xy):
                        points=result.masks.xy[b].copy();points[:,0]+=x;points[:,1]+=y
                        if len(points)>64:points=points[::math.ceil(len(points)/64)]
                        polygon=[[float(px),float(py)] for px,py in points]
                    polygons.append(polygon)
                completed+=1
                progress(stage=f"{'Segmenting structures' if source=='building-model' else 'Detecting living-organism candidates' if person_ids else 'Detecting animals & vehicles' if animal_ids and vehicle_ids else 'Detecting animal candidates' if animal_ids else 'Detecting transport'} · {index+1}/{len(windows)} tiles",progress=30+int((24 if person_ids and config.get('useAerialPeople',False) else 39 if use_overhead else 54)*completed/total_inferences),tileCount=len(windows),tilesProcessed=index+1,imagery=info)
        person_points=[];person_metadata={'status':'not_requested' if eligible else 'not_assessed_insufficient_imagery'}
        if person_ids and config.get('useAerialPeople',False):
            try:person_points,person_metadata=self.people.predict(frame,config.get('personConfidence',15)/100,lambda **p:progress(**p,tileCount=len(windows),tilesProcessed=len(windows),imagery=info))
            except Exception:
                import logging
                logging.exception('Aerial human detector failed');person_metadata={'status':'unavailable','reason':'Aerial human model could not run; the general detector remains experimental.'}
        aerial_points=[];aerial_metadata={'status':'not_requested' if eligible else 'not_assessed_insufficient_imagery'}
        if use_overhead:
            try:aerial_points,aerial_metadata=self.overhead.predict(np.asarray(image),max(.2,config['confidence']/100),lambda **p:progress(**p,tileCount=len(windows),tilesProcessed=len(windows),imagery=info))
            except Exception:
                import logging
                logging.exception('Aerial wildlife locator failed')
                aerial_metadata={'status':'unavailable','reason':'The aerial locator could not be loaded or run. No locator findings were inferred.'}
        progress(stage='Deduplicating and geolocating findings',progress=85,tileCount=len(windows),tilesProcessed=len(windows),imagery=info)
        detections=[];notices=['Findings describe the captured image, not current conditions. Image age is unrestricted; acquisition and analysis time are not capture time.','Vehicle classifications use general-purpose COCO weights. Building footprints use a separate satellite-trained segmentation model (keremberke/yolov8n-building-segmentation). Both can miss or misclassify objects.','Unknown features are geometry-based image proposals, not identified structures. They have no classification probability. No mode detects or identifies everything.','Coordinates and dimensions are estimates from image pixels. Requested detail may exceed the native resolution of the source imagery.']
        if not eligible:notices.extend(['High-detail imagery unavailable for this location. People, animals and image features were not assessed.']+assessment['limitations'])
        if use_overhead and aerial_metadata['status']!='available':notices.append('The aerial wildlife locator was unavailable. General model candidates, if any, remain available; the aerial layer was not assessed.')
        if set(groups)&{'Aquatic/Marine Animals','Reptilian Creatures'}:notices.append('Aquatic/marine and reptilian categories are review-only: no specialist classifier is active. Add Unclassified Wildlife to request generic aerial candidate localization. No absence conclusion can be drawn for these categories.')
        if use_overhead and aerial_metadata['status']=='available':notices.append('OWL-C is an aerial-trained animal localizer, not a species classifier. Its heatmap activation is not a probability. Satellite accuracy improvement has not been measured. Model weights: CC BY-NC-SA 4.0, non-commercial research use; see https://zenodo.org/records/20802844 .')
        if species:notices.append('Wildlife mode is experimental: animal classes come from general COCO photographs, not satellite wildlife training. Only the selected supported classes are searched. No animal detections does not establish that wildlife is absent. Birds, small animals, shadows, vegetation, and canopy cover are especially difficult; species suggestions require independent review.')
        if species and info['groundResolutionMeters']>.3:notices.append(f"At {info['groundResolutionMeters']} m/pixel, a hypothetical 4 m-long animal spans only about {4/info['groundResolutionMeters']:.1f} pixels. Image sampling does not establish native source resolution; a smaller scan may still lack enough real detail.")
        if person_ids:notices.append('Living Organisms searches Person and selected supported animal classes using a general-photo model. It does not identify people, confirm organism presence, classify all plants, or provide live tracking. Small people or animals may not be resolvable from this imagery.')
        if info.get('detailLimited'):notices.append(f"The provider declined finer imagery at this location. A fresh image was acquired at supported detail level {info['samplingZoom']}; extra digital zoom cannot recover missing source detail.")
        if info['groundResolutionMeters']>.6:notices.append('The area-wide mosaic is resolution-limited. Use Inspect location or Inspect feature to acquire a smaller, more detailed area.')
        left,bottom,right,top=info['bounds3857']
        def add_detection(box,type,confidence,source,tile,polygon=None,description=None):
            if len(detections)>=1000:
                message='Report limited to 1,000 findings. Use a smaller scan for additional review.'
                if message not in notices:notices.append(message)
                return None
            x1,y1,x2,y2=box;cx=(x1+x2)/2;cy=(y1+y2)/2;lat,lon=unproject(left+cx/width*(right-left),top-cy/height*(top-bottom))
            if geodesic((config['latitude'],config['longitude']),(lat,lon)).km>config['radiusKm']:return
            d={'id':f'DET-{len(detections)+1:04d}','type':type,'confidence':round(confidence*100,2) if confidence is not None else None,'latitude':round(lat,7),'longitude':round(lon,7),'tile':tile,'reviewed':False,'origin':source,'category':'Wildlife' if source=='animal-model' else 'Living Organisms' if source in ('person-model','aerial-person-model','overhead-model') else 'Agriculture' if source=='mapped-agriculture' else 'Structures' if source=='building-model' else 'Vehicles' if source=='vehicle-model' else 'Unclassified','assessment':'Unidentified' if type=='Unknown feature' or source=='mapped-agriculture' else 'Model suggestion','notes':'','bboxPixels':[round(v,2) for v in box],'bboxNormalized':[x1/width,y1/height,x2/width,y2/height],'dimensionsMeters':{'width':round((x2-x1)*info['groundResolutionMeters'],1),'height':round((y2-y1)*info['groundResolutionMeters'],1)},'description':description or ('Satellite model suggests a building or roof footprint. Its purpose is not identified.' if type=='Building' else f'Possible {type.lower()} suggested by a general-purpose animal class. This model is not validated for satellite wildlife identification; the species and presence of an animal are unconfirmed.' if source=='animal-model' else 'Possible person suggested by a general-photo model. Presence is unconfirmed; this is not identity recognition or live tracking.' if source in ('person-model','aerial-person-model') else 'Machine classification; human review required.')}
            if source in ('animal-model','person-model','aerial-person-model','overhead-model'):
                d['organismGroup']='Humans' if source in ('person-model','aerial-person-model') else 'Unclassified Wildlife' if source=='overhead-model' or type=='Bird' else 'Land Mammals'
                if source not in ('person-model','aerial-person-model'):d.update({'wildlifeFlag':'possible','flagBasis':'Single model suggestion; biological presence remains unconfirmed.','flagMeaning':'Review priority, not a calibrated presence probability'})
            if polygon:d['polygonNormalized']=[[px/width,py/height] for px,py in polygon]
            detections.append(d)
            return d
        if boxes:
            keep=batched_nms(torch.tensor(boxes,dtype=torch.float32),torch.tensor(scores),torch.tensor(class_ids),.45).tolist()
            for i in keep[:750]:add_detection(boxes[i],reverse_ids[class_ids[i]],scores[i],sources[i],f'T-{origins[i]:03d}',polygons[i])
            if len(keep)>750:notices.append('Model output limited to 750 highest-confidence findings; narrow the area for full review.')
        for person in person_points:
            if any(d['type']=='Person' and overlap_people(person['box'],d['bboxPixels'])>.25 for d in detections):continue
            d=add_detection(person['box'],'Person',person['score'],'aerial-person-model','HUMAN',description='Possible person from a dedicated VisDrone-trained aerial detector using overlapping 320 px source crops at 960 px model input. Magnification adds no real detail. People/pedestrian source classes are merged; a box may contain a small group. Presence is unconfirmed; this is not a population count, identification, or live tracking.')
            if d is not None:d.update({'sourceClass':person['sourceClass'],'organismGroup':'Humans','assessment':'Possible person','humanCandidate':True})
        archaeology_analysis=None
        if 'Archaeology' in config['classes']:
            progress(stage='Searching image structure and remnant candidates',progress=85,tileCount=len(windows),tilesProcessed=len(windows),imagery=info)
            candidates=propose_archaeology(frame,info['groundResolutionMeters']) if eligible else []
            for candidate in candidates:
                d=add_detection(candidate['box'],'Structure candidate',None,'archaeology-proposal','IMAGE',candidate['polygon'],candidate['description'])
                if d is not None:d.update({'category':'Archaeology','assessment':'Possible structure/remnant','proposalRank':round(candidate['rank'],3),'componentCount':candidate['componentCount'],'isImageDiscovery':True,'archaeologicalAgeEstablished':False})
            progress(stage='Checking known historic map context separately',progress=86,tileCount=len(windows),tilesProcessed=len(windows),imagery=info)
            heritage,heritage_metadata=fetch_heritage(info)
            for feature in heritage:
                d=add_detection(feature['box'],'Mapped heritage',None,'mapped-heritage','MAP',feature['polygon'],feature['description'])
                if d is not None:
                    d.update({k:feature[k] for k in ['label','mapTags','osmElementId','osmElementType','mapUrl']})
                    d.update({'category':'Archaeology','assessment':'Mapped historic feature','isImageDiscovery':False,'dimensionsMeters':None})
            archaeology_analysis={'status':'available' if eligible else 'image_not_assessed_insufficient_imagery','imageDetectionStatus':'completed' if eligible else 'not_assessed','imageMethod':'Multiscale contrast/stone-shadow clusters; not a trained archaeology classifier','imageCandidateCount':sum(d['origin']=='archaeology-proposal' for d in detections),'mappedContext':heritage_metadata,'mappedCount':sum(d['origin']=='mapped-heritage' for d in detections),'ageOrHumanOriginConfirmed':False,'accuracyValidated':False}
            notices.append('Archaeology separates image-only structure/remnant candidates from previously mapped heritage. Neither image geometry nor a map tag proves age or archaeological significance. Natural rocks, trees, paths, and modern features can be false positives; unmapped/buried sites may be missed.')
        if person_ids:
            notices.append('Human search uses a dedicated aerial-trained model on magnified small crops when available. Aerial status: '+person_metadata['status']+'. Scores are model confidence, not confirmed presence or a reliable count. Small objects and imagery resampling remain limiting; reviewed crops can be saved as positive or negative training examples.')
        for point in aerial_points:
            px,py=point['x'],point['y'];match=next((d for d in detections if d['origin']=='animal-model' and d['bboxPixels'][0]-4<=px<=d['bboxPixels'][2]+4 and d['bboxPixels'][1]-4<=py<=d['bboxPixels'][3]+4),None)
            if match:
                match.update({'wildlifeFlag':'probable','flagBasis':'General animal detector and independent aerial locator agree spatially. This increases review priority, not a calibrated probability or confirmed species.','corroboratingModels':[config['model'],'OWL-C'],'localizationScore':round(point['score'],4)})
                continue
            box=[max(0,px-12),max(0,py-12),min(width,px+12),min(height,py+12)]
            d=add_detection(box,'Unclassified wildlife',None,'overhead-model','AERIAL',description='OWL-C aerial animal-localization candidate. Species, animal presence, and biological category are unconfirmed. The box is a fixed review window around a predicted point, not an animal outline.')
            if d is not None:d.update({'dimensionsMeters':None,'reviewWindowOnly':True,'localizationScore':round(point['score'],4),'pointNormalized':[px/width,py/height],'flagBasis':'Aerial animal-localization peak; no independent confirmation.','scoreMeaning':'Localization heatmap activation, not a calibrated probability'})
        agriculture_analysis=None
        if 'Agriculture' in config['classes']:
            fields,agriculture_analysis,agriculture_notice=fetch_agriculture(config,info,lambda **p:progress(**p,tileCount=len(windows),tilesProcessed=len(windows),imagery=info))
            notices.append(agriculture_notice)
            for field in fields:
                d=add_detection(field['box'],'Agriculture',None,'mapped-agriculture','MAP',field['polygon'],field['description'])
                if d is not None:
                    d.update({k:field[k] for k in ['label','mapTags','osmElementId','osmElementType','cropFromMap']})
                    if field.get('holes'):d['holesNormalized']=[[[x/width,y/height] for x,y in ring] for ring in field['holes']]
            agriculture_analysis['includedFindingCount']=sum(d['origin']=='mapped-agriculture' for d in detections)
        if eligible and 'Unknown feature' in config['classes']:

            progress(stage='Proposing unclassified visual features',progress=89,tileCount=len(windows),tilesProcessed=len(windows),imagery=info)
            proposals=propose_features(frame,info['groundResolutionMeters'],[d['bboxPixels'] for d in detections])
            for p in proposals:add_detection(p['box'],'Unknown feature',None,'image-proposal','FEATURE',p['polygon'],p['description'])
            if len(proposals)>=200:notices.append('Visual proposals limited to 200 compact bright features. Dark, diffuse, or low-contrast objects may be missed; mark additional regions manually.')
        annotated=frame.copy()
        for d in detections:
            x1,y1,x2,y2=map(round,d['bboxPixels']);h=COLORS[d['type']].lstrip('#');color=tuple(int(h[i:i+2],16) for i in (4,2,0));cv2.rectangle(annotated,(x1,y1),(x2,y2),color,2)
            if d.get('polygonNormalized'):
                polygon=np.array([[round(px*width),round(py*height)] for px,py in d['polygonNormalized']],dtype=np.int32);cv2.polylines(annotated,[polygon],True,color,2)
            label=f"{d['type']} {d['confidence']:.1f}%" if d['confidence'] is not None else f"{d['type']} (unclassified)"
            cv2.putText(annotated,label,(x1,max(y1-6,15)),cv2.FONT_HERSHEY_SIMPLEX,.45,color,1,cv2.LINE_AA)
        cv2.imwrite(str(output_dir/'annotated.jpg'),annotated,[cv2.IMWRITE_JPEG_QUALITY,90])
        chart_classes=[reverse_ids[i] for i in vehicle_ids]+[c for c in ['Building','Agriculture','Unknown feature'] if c in config['classes']]
        if 'Archaeology' in config['classes']:chart_classes+=['Structure candidate','Mapped heritage']
        if 'organismCategories' in config:
            chart_classes+=([g for g in ['Land Mammals','Humans'] if g in groups]+(['Unclassified Wildlife'] if aerial_metadata['status']=='available' else []))
            counts=[sum((d.get('organismGroup')==c if c in groups or c=='Unclassified Wildlife' else d['type']==c) for d in detections) for c in chart_classes]
        else:
            chart_classes+=(['Person'] if person_ids else [])+species
            counts=[sum(d['type']==c for d in detections) for c in chart_classes]
        fig,axis=plt.subplots(figsize=(max(9,len(chart_classes)*.8),3.5),facecolor='#101619');axis.set_facecolor('#101619');axis.bar(chart_classes,counts,color=[COLORS.get(c,'#e9a7cc') for c in chart_classes]);axis.tick_params(colors='#a9bbc4',labelsize=9);axis.tick_params(axis='x',labelrotation=35 if len(chart_classes)>8 else 0);axis.set_ylabel('Findings',color='#a9bbc4');axis.set_title('AVIE · Context only — image detection not assessed' if not eligible else 'AVIE · Findings (marine/reptile specialist detection unavailable)' if set(groups)&{'Aquatic/Marine Animals','Reptilian Creatures'} else 'AVIE · Findings by category',color='#e3eaed');axis.yaxis.get_major_locator().set_params(integer=True)
        for spine in axis.spines.values():spine.set_color('#344047')
        fig.tight_layout();fig.savefig(output_dir/'confidence.png',dpi=140,facecolor=fig.get_facecolor());plt.close(fig)
        result={'simulated':False,'detections':detections,'imagery':info,'tileCount':len(windows),'durationSeconds':round(time.monotonic()-start,2),'notices':notices,'configuration':config,'analysisVersion':7,'analysisAt':analysis_at,'captureLabel':capture_label(info),'imageryAssessment':assessment,'detectionStatus':'completed' if eligible else 'not_run_insufficient_imagery','findingsContext':'Findings describe the captured image, not current conditions.','humanAnalysis':person_metadata,**({'archaeologyAnalysis':archaeology_analysis} if archaeology_analysis is not None else {}),'organismAnalysis':{'requestedCategories':groups,'aerialLocator':aerial_metadata,'reviewOnlyCategories':[g for g in groups if g in ['Aquatic/Marine Animals','Reptilian Creatures']],'flagPolicy':'Possible = single model candidate; Probable = spatial agreement of independent general and aerial models, or a separately saved human assessment. Neither is a calibrated probability.','accuracyImprovementMeasured':False},**({'wildlifeAnalysis':animal_resolution_context(info)} if species else {}),**({'agricultureAnalysis':agriculture_analysis} if agriculture_analysis is not None else {})}
        (output_dir/'report.json').write_text(json.dumps(result,indent=2));progress(stage='Uploading imagery and report',progress=95,tileCount=len(windows),tilesProcessed=len(windows),imagery=info)
        return result
