import {test} from 'node:test';
import assert from 'node:assert/strict';
import {assessImagery,captureLabel,nativeZoomLimit,normalizeBaseline,baselineCovers} from '../public/imagery-policy.js';
const good={sourceType:'aerial',provider:'Historical survey',nativeGsdCm:3,groundResolutionMeters:.03,licenseReference:'Test contract',analysisPermitted:true,displayPermitted:true};
test('native capture resolution and delivered spacing are independent requirements; age is unrestricted',()=>{
 assert.equal(assessImagery({...good,captureDate:'1999-01-01'}).eligible,true);
 for(const nativeGsdCm of [null,0,-1,5.1,12.5,NaN,Infinity,true,'3'])assert.equal(assessImagery({...good,nativeGsdCm}).eligible,false);
 assert.equal(assessImagery({...good,nativeGsdCm:5}).eligible,true);
 assert.equal(assessImagery({...good,groundResolutionMeters:.125}).eligible,false);
 for(const patch of [{sourceType:'context'},{licenseReference:null},{analysisPermitted:false},{displayPermitted:false}])assert.equal(assessImagery({...good,...patch}).eligible,false);
});
test('capture precision is preserved, unknown timestamps are not replaced',()=>{
 assert.equal(captureLabel({acquiredAt:'2026-11-13T01:00:00Z'}),'Capture date/time unavailable');
 assert.equal(captureLabel({captureDate:'2001-06-01'}),'2001-06-01 (capture time unavailable)');
 assert.equal(captureLabel({capturedAt:'2001-06-01T10:15:00Z'}),'2001-06-01T10:15:00Z');
 assert.equal(captureLabel({capturedAt:'2001-06-01T10:15:00'}),'Capture date/time unavailable');
 assert.equal(captureLabel({captureDate:'2001-02-31'}),'Capture date/time unavailable');
 assert.equal(captureLabel({captureDateRange:{start:'2001-01-01',end:'2001-12-31'}}),'2001-01-01 to 2001-12-31 (exact capture date/time unavailable)');
});
test('zoom cannot enlarge original image pixels including small images',()=>{
 for(const [w,h,vw,vh] of [[4096,4096,800,600],[200,100,800,600],[800,2000,400,300]]){
  const fit=Math.min(1,vw/w,vh/h);assert.ok(fit*nativeZoomLimit(w,h,vw,vh)<=1.000001);
 }
});
test('provider export metadata determines sampling; full scan radius must fit',()=>{
 const info=normalizeBaseline({source:'Survey',source_type:'aerial',native_gsd_cm:3,license_reference:'Contract',analysis_permitted:true,display_permitted:true,width:4096,height:4096,bounds3857:[-102.4,-102.4,102.4,102.4]});
 assert.equal(assessImagery(info).eligible,true);assert.equal(baselineCovers(info,{latitude:0,longitude:0,radiusKm:.05}),true);assert.equal(baselineCovers(info,{latitude:0,longitude:0,radiusKm:.5}),false);
 assert.throws(()=>normalizeBaseline({bounds3857:[0,0,0,0]}));
});
