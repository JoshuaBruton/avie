"""Mapped agricultural land use, never an image-based crop classifier."""
import math
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
import requests

LAND_USES={'farmland':'farmland','farmyard':'farmyard','vineyard':'vineyard','orchard':'orchard','greenhouse_horticulture':'greenhouse area','allotments':'allotments','meadow':'meadow / grassland'}
ENDPOINTS=('https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter')

def clip_polygon(points,width,height):
    result=points
    for axis,value,greater in ((0,0,True),(0,width,False),(1,0,True),(1,height,False)):
        output=[]
        if not result:break
        previous=result[-1]
        for current in result:
            inside=lambda p:p[axis]>=value if greater else p[axis]<=value
            a,b=inside(previous),inside(current)
            if a!=b:
                denominator=current[axis]-previous[axis]
                t=(value-previous[axis])/denominator if denominator else 0
                output.append([previous[0]+t*(current[0]-previous[0]),previous[1]+t*(current[1]-previous[1])])
            if b:output.append(current)
            previous=current
        result=output
    return result

def mapped_features(elements,info):
    left,bottom,right,top=info['bounds3857'];width,height=info['width'],info['height'];features=[]
    for element in elements:
        tags=element.get('tags',{});landuse=tags.get('landuse');crop=tags.get('crop') or tags.get('produce')
        if landuse not in LAND_USES and not crop:continue
        points=[]
        for p in element.get('geometry',[]):
            lat,lon=p.get('lat'),p.get('lon')
            if not isinstance(lat,(int,float)) or not isinstance(lon,(int,float)) or abs(lat)>=89:continue
            x=6378137*math.radians(lon);y=6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2))
            points.append([(x-left)/(right-left)*width,(top-y)/(top-bottom)*height])
        points=clip_polygon(points,width,height)
        if len(points)<3:continue
        x1,y1=min(p[0] for p in points),min(p[1] for p in points);x2,y2=max(p[0] for p in points),max(p[1] for p in points)
        if x2-x1<2 or y2-y1<2:continue
        kind=LAND_USES.get(landuse,'agricultural land');label='Mapped '+kind+(f' · {crop}' if crop else '')
        holes=[]
        for ring in element.get('holes',[]):
            projected=[]
            for p in ring:
                x=6378137*math.radians(p['lon']);y=6378137*math.log(math.tan(math.pi/4+math.radians(p['lat'])/2))
                projected.append([(x-left)/(right-left)*width,(top-y)/(top-bottom)*height])
            hole=clip_polygon(projected,width,height)
            if len(hole)>=3:holes.append(hole[::max(1,math.ceil(len(hole)/96))])
        source_tags={k:str(tags[k])[:160] for k in ['landuse','crop','produce','trees','name','source','source:date','CLC:year'] if k in tags}
        if len(points)>96:points=points[::math.ceil(len(points)/96)]
        features.append({'box':[x1,y1,x2,y2],'polygon':points,'holes':holes,'label':label,'description':f'OpenStreetMap tags describe {kind}. '+(f'Mapped crop/produce tag: {crop}. ' if crop else 'The crop is not specified. ')+'This is mapped land use, not an image-based crop identification. Map data may be incomplete, outdated, or differ from the imagery date.','mapTags':source_tags,'osmElementId':str(element.get('id','')),'osmElementType':element.get('type','way'),'cropFromMap':str(crop) if crop else None})
    return features

RELATION_CACHE={}

def bounded_xml(url,params=None):
    with requests.get(url,params=params,headers={'User-Agent':'AVIE/1.3 (https://github.com/joshuabruton/avie; geospatial analysis)'},timeout=(8,25),stream=True) as response:
        response.raise_for_status();chunks=[];size=0
        for chunk in response.iter_content(65536):
            size+=len(chunk)
            if size>4*1024*1024:raise ValueError('Map response too large; use a smaller agricultural scan.')
            chunks.append(chunk)
    return ET.fromstring(b''.join(chunks))

def joined_rings(segments):
    remaining=[list(s) for s in segments if len(s)>=2];rings=[]
    while remaining:
        chain=remaining.pop()
        while chain[0]!=chain[-1]:
            index=next((i for i,s in enumerate(remaining) if s[0]==chain[-1] or s[-1]==chain[-1]),None)
            if index is None:break
            segment=remaining.pop(index)
            if segment[-1]==chain[-1]:segment.reverse()
            chain.extend(segment[1:])
        if len(chain)>=4 and chain[0]==chain[-1]:rings.append(chain)
    return rings

def map_elements(root,relation_fetch=None):
    nodes={n.get('id'):{'lat':float(n.get('lat')),'lon':float(n.get('lon'))} for n in root.findall('node')};ways={w.get('id'):[n.get('ref') for n in w.findall('nd')] for w in root.findall('way')};elements=[]
    for way in root.findall('way'):
        tags={t.get('k'):t.get('v') for t in way.findall('tag')}
        if tags.get('landuse') not in LAND_USES and 'crop' not in tags:continue
        refs=ways[way.get('id')]
        if len(refs)<4 or refs[0]!=refs[-1] or not all(ref in nodes for ref in refs):continue
        elements.append({'id':way.get('id'),'type':'way','tags':tags,'geometry':[nodes[ref] for ref in refs]})
    for relation in root.findall('relation'):
        tags={t.get('k'):t.get('v') for t in relation.findall('tag')}
        if tags.get('landuse') not in LAND_USES and 'crop' not in tags:continue
        rel_nodes,rel_ways=nodes,ways
        members=[m for m in relation.findall('member') if m.get('type')=='way']
        if relation_fetch and any(m.get('ref') not in ways for m in members):
            try:
                full=relation_fetch(relation.get('id'))
                rel_nodes={n.get('id'):{'lat':float(n.get('lat')),'lon':float(n.get('lon'))} for n in full.findall('node')};rel_ways={w.get('id'):[n.get('ref') for n in w.findall('nd')] for w in full.findall('way')}
            except (requests.RequestException,ValueError,ET.ParseError):continue
        outer=joined_rings([rel_ways[m.get('ref')] for m in members if m.get('role') in ('outer','') and m.get('ref') in rel_ways]);inner=joined_rings([rel_ways[m.get('ref')] for m in members if m.get('role')=='inner' and m.get('ref') in rel_ways])
        holes=[[rel_nodes[ref] for ref in refs] for refs in inner if all(ref in rel_nodes for ref in refs)]
        for refs in outer:
            if all(ref in rel_nodes for ref in refs):elements.append({'id':relation.get('id'),'type':'relation','tags':tags,'geometry':[rel_nodes[ref] for ref in refs],'holes':holes})
    return elements[:250]

def read_map_api(info):
    left,bottom,right,top=info['bounds3857'];r=6378137
    inverse=lambda x,y:((2*math.atan(math.exp(y/r))-math.pi/2)*180/math.pi,x/r*180/math.pi)
    south,west=inverse(left,bottom);north,east=inverse(right,top)
    root=bounded_xml('https://www.openstreetmap.org/api/0.6/map',{'bbox':f'{west},{south},{east},{north}'})
    fetched=[0]
    def relation_fetch(id):
        if id in RELATION_CACHE:return RELATION_CACHE[id]
        if fetched[0]>=4:raise ValueError('Relation expansion limit reached.')
        fetched[0]+=1;full=bounded_xml('https://www.openstreetmap.org/api/0.6/relation/'+id+'/full')
        if len(RELATION_CACHE)>=16:RELATION_CACHE.pop(next(iter(RELATION_CACHE)))
        RELATION_CACHE[id]=full;return full
    return map_elements(root,relation_fetch)

def fetch_agriculture(config,info,progress):
    lat,lon,radius=config['latitude'],config['longitude'],config['radiusKm']*1000
    query=f'[out:json][timeout:12];(way(around:{radius},{lat},{lon})["landuse"~"^(farmland|farmyard|vineyard|orchard|greenhouse_horticulture|allotments|meadow)$"];way(around:{radius},{lat},{lon})["crop"];);out tags geom 250;'
    metadata={'source':'OpenStreetMap via Overpass','retrievedAt':datetime.now(timezone.utc).isoformat(),'imageCropClassification':False,'nativeCropVerification':False,'coverageComplete':False,'attribution':'© OpenStreetMap contributors, ODbL','licenseUrl':'https://www.openstreetmap.org/copyright'}
    if config['radiusKm']<=5:
        progress(stage='Looking up mapped agricultural land use',progress=87)
        try:
            elements=read_map_api(info);features=mapped_features(elements,info)
            return features,{**metadata,'source':'OpenStreetMap API','status':'available','mappedFeatureCount':len(features),'resultLimitReached':len(elements)>=250},'Agriculture uses OpenStreetMap field boundaries and crop tags where available, not crop predictions from imagery. © OpenStreetMap contributors. Coverage is incomplete; an unmapped field can still be agricultural.'
        except (requests.RequestException,ValueError,ET.ParseError):pass
    for index,endpoint in enumerate(ENDPOINTS):
        progress(stage=f'Looking up mapped agricultural land use · source {index+1}',progress=87)
        try:
            response=requests.get(endpoint,params={'data':query},headers={'User-Agent':'AVIE/1.3 (https://github.com/joshuabruton/avie; geospatial analysis)'},timeout=(8,22));response.raise_for_status();payload=response.json()
            if payload.get('remark'):continue
            elements=payload.get('elements')
            if not isinstance(elements,list):continue
            features=mapped_features(elements,info)
            return features,{**metadata,'status':'available','mappedFeatureCount':len(features),'resultLimitReached':len(elements)>=250},'Agriculture uses OpenStreetMap field boundaries and crop tags where available, not crop predictions from imagery. Coverage is incomplete; an unmapped field can still be agricultural.'
        except (requests.RequestException,ValueError):continue
    return [],{**metadata,'status':'unavailable','mappedFeatureCount':None},'The agricultural map-data service was unavailable for this scan. Agriculture was not assessed; this is not evidence that no fields are present.'
