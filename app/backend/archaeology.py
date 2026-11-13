"""Image-only structure candidates and independently sourced mapped heritage context."""
import math
from datetime import datetime,timezone
import cv2,numpy as np
import requests
import xml.etree.ElementTree as ET
from agriculture import bounded_xml,clip_polygon
from features import overlap

HISTORIC={'archaeological_site','ruins','monument','castle','citywalls','tomb','boundary_stone','fort','yes'}
def propose_archaeology(frame,spacing,limit=60):
    """Multiscale clusters of contrasting stone/shadow texture; no age classifier."""
    height,width=frame.shape[:2];scale=min(1,1400/max(width,height));small=cv2.resize(frame,None,fx=scale,fy=scale) if scale<1 else frame
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY);b,g,r=cv2.split(small.astype(np.float32));green=(g-(r+b)/2)/(g+1)
    local=cv2.GaussianBlur(gray.astype(np.float32),(0,0),max(2,1.3/spacing*scale));contrast=np.abs(gray-local)
    seeds=((contrast>9)&((green<.13)|(gray<local-13))).astype(np.uint8)*255
    seeds=cv2.morphologyEx(seeds,cv2.MORPH_OPEN,np.ones((2,2),np.uint8));items=[]
    for ground_gap in (1.5,3.,6.):
        k=max(3,min(61,round(ground_gap/spacing*scale)));k+=1-k%2
        mask=cv2.morphologyEx(seeds,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(k,k)))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x,y,w,h=cv2.boundingRect(contour);gw=w/scale*spacing;gh=h/scale*spacing
            if not(7<=gw<=180 and 7<=gh<=180) or max(w,h)/min(w,h)>5:continue
            area=cv2.contourArea(contour)
            if area/(w*h)<.20:continue
            density=float(np.count_nonzero(seeds[y:y+h,x:x+w]))/(w*h)
            if density<.035:continue
            # Require multiple contrast components: a single tree/stone is not a site cluster.
            components=cv2.connectedComponentsWithStats(seeds[y:y+h,x:x+w],8)[2][1:]
            count=sum(2<=q[4]<=max(20,w*h*.2) for q in components)
            if count<5:continue
            polygon=cv2.approxPolyDP(cv2.convexHull(contour),max(1,.01*cv2.arcLength(contour,True)),True).reshape(-1,2)/scale
            box=[x/scale,y/scale,(x+w)/scale,(y+h)/scale];rank=math.sqrt(area)*min(density,.35)*math.log1p(count)
            items.append({'box':box,'polygon':polygon.tolist()[:64],'rank':rank,'componentCount':int(count),'description':'Image-only cluster of contrasting stone-like edges and shadows, grouped at multiple ground scales. Possible structure/remnant for review; age, human origin, and archaeological significance are NOT established. Trees, natural rocks, paths, and modern features can produce similar geometry.'})
    kept=[]
    for p in sorted(items,key=lambda p:p['rank'],reverse=True):
        if any(overlap(p['box'],q['box'])>.35 for q in kept):continue
        kept.append(p)
        if len(kept)>=limit:break
    return kept

def mapped_heritage(root,info):
    left,bottom,right,top=info['bounds3857'];width,height=info['width'],info['height'];nodes={n.get('id'):(float(n.get('lat')),float(n.get('lon'))) for n in root.findall('node')};out=[]
    def pixel(lat,lon):
        x=6378137*math.radians(lon);y=6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2));return[(x-left)/(right-left)*width,(top-y)/(top-bottom)*height]
    for e in list(root.findall('node'))+list(root.findall('way')):
        tags={t.get('k'):t.get('v') for t in e.findall('tag')}
        if tags.get('historic') not in HISTORIC and tags.get('ruins')!='yes' and tags.get('site_type') not in {'megalith','stone_circle','tumulus','settlement','fortification'}:continue
        points=[pixel(*nodes[n.get('ref')]) for n in e.findall('nd') if n.get('ref') in nodes] if e.tag=='way' else [pixel(*nodes[e.get('id')])]
        if not points:continue
        if len(points)==1:
            x,y=points[0]
            if not(0<=x<=width and 0<=y<=height):continue
            pad=max(6,3/info['groundResolutionMeters']);box=[max(0,x-pad),max(0,y-pad),min(width,x+pad),min(height,y+pad)];polygon=None
        else:
            points=clip_polygon(points,width,height)
            if len(points)<3:continue
            box=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)];polygon=points[::max(1,math.ceil(len(points)/96))]
        if box[2]-box[0]<1 or box[3]-box[1]<1:continue
        out.append({'box':box,'polygon':polygon,'label':tags.get('name') or 'Mapped historic feature','mapTags':{k:v for k,v in tags.items() if k in ['name','historic','site_type','archaeological_site','ruins','heritage','start_date','wikidata']},'osmElementId':e.get('id'),'osmElementType':e.tag,'mapUrl':f'https://www.openstreetmap.org/{e.tag}/{e.get("id")}','description':'Previously mapped historic feature from OpenStreetMap, not an image-model discovery. Map identity, boundaries, and dates require independent verification.'})
    return out[:100]

def fetch_heritage(info):
    left,bottom,right,top=info['bounds3857'];inverse=lambda x,y:((2*math.atan(math.exp(y/6378137))-math.pi/2)*180/math.pi,x/6378137*180/math.pi)
    south,west=inverse(left,bottom);north,east=inverse(right,top)
    meta={'source':'OpenStreetMap','attribution':'© OpenStreetMap contributors, ODbL','retrievedAt':datetime.now(timezone.utc).isoformat(),'isImageDiscovery':False,'coverageComplete':False}
    # Keep OSM map requests bounded; larger surveys still run image candidates.
    if (north-south)*(east-west)>.01:return [],{**meta,'status':'not_assessed','reason':'Map context limited to smaller areas; use a close-up.'}
    try:
        root=bounded_xml('https://www.openstreetmap.org/api/0.6/map',{'bbox':f'{west},{south},{east},{north}'})
        return mapped_heritage(root,info),{**meta,'status':'available'}
    except (requests.RequestException,ValueError,ET.ParseError):
        return [],{**meta,'status':'unavailable','reason':'Historic map context unavailable; this is not evidence of absence.'}
