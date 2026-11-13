"""Outbound-only authenticated queue worker. No public inbound port is needed."""
from __future__ import annotations
import argparse,json,os,sys,time,threading,tempfile,logging
from pathlib import Path
import requests

class JobEnded(Exception):pass
class SiteClient:
    def __init__(self,config):
        self.url=config['url'].rstrip('/');self.headers={'OAI-Sites-Authorization':'Bearer '+config['serviceToken'],'x-avie-worker-token':config['workerToken']}
    def call(self,path,payload=None,lease=None,data=None,method='POST'):
        headers=dict(self.headers);headers['x-avie-analysis-version']='7'
        if lease:headers['x-avie-lease']=lease
        if data is not None:headers['content-type']='application/octet-stream'
        last=None
        for attempt in range(3):
            try:
                response=requests.request(method,self.url+path,headers=headers,json=payload if data is None else None,data=data,timeout=(15,90))
                if response.status_code==409:raise JobEnded('Scan cancelled or lease expired.')
                if response.status_code in (429,500,502,503,504) and attempt<2:time.sleep(attempt+1);continue
                if not response.ok:raise RuntimeError(f'API request failed ({response.status_code}) on {path.split("/")[2]}.')
                return response.json()
            except requests.RequestException as exc:
                last=exc
                if attempt==2:raise RuntimeError('The AVIE site is unreachable.') from exc
                time.sleep(attempt+1)
        raise RuntimeError('The AVIE site is unreachable.') from last

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stdin-config',action='store_true');parser.add_argument('--once',action='store_true');args=parser.parse_args()
    if args.stdin_config:
        if sys.stdin.isatty():
            import termios
            attrs=termios.tcgetattr(sys.stdin);attrs[3]&=~termios.ECHO;termios.tcsetattr(sys.stdin,termios.TCSANOW,attrs)
        print('Ready for worker configuration',flush=True);config=json.loads(sys.stdin.readline())
    else:config={'url':os.environ['AVIE_SITE_URL'],'serviceToken':os.environ['AVIE_SITE_SERVICE_TOKEN'],'workerToken':os.environ['AVIE_WORKER_TOKEN']}
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    client=SiteClient(config);stop=threading.Event()
    def heartbeat():
        while not stop.is_set():
            try:client.call('/api/worker/heartbeat',{'model':'YOLOv8n/s/m','engine':'PyTorch + aerial humans + structure candidates + OWL-C + mapped context','analysisVersion':7})
            except Exception as e:logging.warning('Heartbeat: %s',e)
            stop.wait(12)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    from pipeline import Pipeline
    engine=Pipeline(os.environ.get('AVIE_MODEL_DIR',str(Path(__file__).resolve().parent.parent/'.runtime/models')))
    logging.info('Python vision worker started')
    try:
        while True:
            try:
                job=client.call('/api/worker/next').get('scan')
                if not job:
                    if args.once:break
                    stop.wait(3);continue
                logging.info('Starting scan %s',job['id']);lease=job['workerLease'];prefix='/api/worker/scans/'+job['id'];last_progress=[0]
                def progress(**p):
                    # Limit object-store writes while keeping cancellation responsive.
                    if time.monotonic()-last_progress[0]<1 and p.get('progress',0)<95:return
                    client.call(prefix+'/progress',p,lease=lease);last_progress[0]=time.monotonic()
                try:
                    with tempfile.TemporaryDirectory(prefix='avie-scan-') as folder:
                        settings=dict(job['configuration'])
                        if settings.get('source')=='aerial':
                            settings['_baseline']=client.call('/api/baselines/'+settings['baselineId'],method='GET')['baseline']
                        result=engine.run(settings,folder,progress)
                        for name in ['imagery.jpg','annotated.jpg','confidence.png','report.json']:
                            client.call(prefix+'/assets/'+name,lease=lease,data=(Path(folder)/name).read_bytes())
                        client.call(prefix+'/complete',result,lease=lease)
                    logging.info('Completed scan %s: %d detections',job['id'],len(result['detections']))
                except JobEnded:logging.info('Scan %s cancelled',job['id'])
                except Exception:
                    logging.exception('Scan failed')
                    try:client.call(prefix+'/fail',{'error':'Imagery acquisition or model inference failed. Please retry with a smaller radius. The worker logs contain technical details.'},lease=lease)
                    except JobEnded:pass
                if args.once:break
            except KeyboardInterrupt:break
            except Exception as e:logging.warning('Queue connection: %s',e);stop.wait(5)
    finally:stop.set()

if __name__=='__main__':main()
