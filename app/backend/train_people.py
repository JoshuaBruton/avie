"""Build/train a custom human candidate from the GUI's reviewed-crop export.
No model is automatically activated. Validate on independent sites before promotion.
"""
import argparse,json,math,random,zipfile
from pathlib import Path

def prepare(archive,output):
    from PIL import Image
    import io
    with zipfile.ZipFile(archive) as z:
        if z.getinfo('manifest.json').file_size>4*1024*1024:raise ValueError('Manifest too large.')
        manifest=json.loads(z.read('manifest.json'));examples=[e for e in manifest.get('examples',[]) if e.get('reviewed') is True and e.get('label') in ('human','not-human')]
        if manifest.get('format')!='avie-reviewed-examples-v1':raise ValueError('Unsupported export format.')
        if sum(e['label']=='human' for e in examples)<20 or sum(e['label']=='not-human' for e in examples)<20:raise ValueError('Collect at least 20 reviewed human and 20 negative crops; this is a minimum guard, not proof of sufficient data.')
        # Link nearby crops OR shared scan ancestry before splitting, including cell boundaries.
        from geopy.distance import geodesic
        parents=list(range(len(examples)))
        def find(i):
            while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
            return i
        for i,e in enumerate(examples):
            for j in range(i):
                q=examples[j]
                if e['rootScanId']==q['rootScanId'] or geodesic((e['latitude'],e['longitude']),(q['latitude'],q['longitude'])).meters<=1000:parents[find(i)]=find(j)
        groups={}
        for i,e in enumerate(examples):groups.setdefault(find(i),[]).append(e)
        if len(groups)<3:raise ValueError('Need at least 3 geographically separated site groups. Repeated Stonehenge crops are not an independent validation set.')
        keys=sorted(groups);random.Random(42).shuffle(keys);heldout=set(keys[:max(1,round(len(keys)*.25))]);assignments={}
        for key,records in groups.items():
            split='val' if key in heldout else 'train'
            for e in records:
                old=assignments.setdefault(e['rootScanId'],split)
                if old!=split:raise ValueError('Scan lineage crosses splits; regroup this survey.')
        if any(not any(e['label']=='human' for k in keys if ('val' if k in heldout else 'train')==split for e in groups[k]) for split in ('train','val')):raise ValueError('Both geographic splits need reviewed positive humans; collect more sites.')
        written=[]
        for key,records in groups.items():
            split='val' if key in heldout else 'train'
            for e in records:
                name=e['imageFile']
                if not name.startswith('crops/') or '..' in name or not name.endswith('.jpg') or z.getinfo(name).file_size>300000:raise ValueError('Unsafe or oversized crop.')
                image=Image.open(io.BytesIO(z.read(name)));image.load()
                if image.width>512 or image.height>512:raise ValueError('Native crops must be at most 512 px per side.')
                stem=Path(name).stem
                if not all(c.isalnum() or c=='-' for c in stem):raise ValueError('Invalid crop name.')
                for folder in ('images','labels'):(output/folder/split).mkdir(parents=True,exist_ok=True)
                image.convert('RGB').save(output/'images'/split/(stem+'.jpg'),quality=95)
                label=''
                if e['label']=='human':
                    x1,y1,x2,y2=e['bboxCropNormalized']
                    if not (0<=x1<x2<=1 and 0<=y1<y2<=1):raise ValueError('Invalid positive crop box.')
                    label=f'0 {(x1+x2)/2:.6f} {(y1+y2)/2:.6f} {x2-x1:.6f} {y2-y1:.6f}\n'
                (output/'labels'/split/(stem+'.txt')).write_text(label);written.append({'id':e['id'],'split':split,'rootScanId':e['rootScanId'],'siteGroup':key,'label':e['label']})
        (output/'dataset.yaml').write_text('path: '+json.dumps(str(output.resolve()))+'\ntrain: images/train\nval: images/val\nnames:\n  0: person\n')
        (output/'split-provenance.json').write_text(json.dumps({'seed':42,'grouping':'Connected groups within 1 km OR shared scan lineage; audit site boundaries before validation','examples':written,'imageryRightsVerifiedByUser':True,'activation':'Not activated; independent-site validation and false-positive review required'},indent=2))
    return output/'dataset.yaml'

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--rights-confirmed',action='store_true',help='Confirm you have checked permission to train on these imagery crops.');p.add_argument('--train',action='store_true');p.add_argument('--epochs',type=int,default=50);p.add_argument('--device',default='cpu');a=p.parse_args()
    if not a.rights_confirmed:p.error('Check the source imagery training/reuse terms, then supply --rights-confirmed.')
    if a.output.exists() and any(a.output.iterdir()):p.error('Choose an empty output directory to preserve prior training artifacts.')
    a.output.mkdir(parents=True,exist_ok=True);dataset=prepare(a.archive,a.output);print('Prepared',dataset)
    if a.train:
        from ultralytics import YOLO
        model=YOLO('yolov8s.pt');model.train(data=str(dataset),epochs=a.epochs,imgsz=640,batch=8,device=a.device,project=str(a.output/'training'),name='human-candidate',seed=42)
        print('Candidate weights created. Not activated in AVIE. Validate independent-site precision/recall and false positives before deployment.')
if __name__=='__main__':main()
