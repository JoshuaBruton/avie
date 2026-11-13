// Capture age is intentionally not an eligibility criterion.
export const imageryRequirement = {maxNativeGsdCm:5, preferredNativeGsdCm:[2,3], freshnessRequired:false};
const validDate=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s).toISOString().slice(0,10)===s;
export function captureLabel(info={}) {
 if(typeof info.capturedAt==='string'&&/^\d{4}-\d{2}-\d{2}T.+(?:Z|[+-]\d{2}:\d{2})$/.test(info.capturedAt)&&Number.isFinite(Date.parse(info.capturedAt)))return info.capturedAt;
 if(validDate(info.captureDate))return `${info.captureDate} (capture time unavailable)`;
 const r=info.captureDateRange;if(r&&validDate(r.start)&&validDate(r.end)&&r.start<=r.end)return `${r.start} to ${r.end} (exact capture date/time unavailable)`;
 return 'Capture date/time unavailable';
}
export function assessImagery(info={}) {
 const n=info.nativeGsdCm, sampling=info.groundResolutionMeters;
 const valid=typeof n==='number'&&Number.isFinite(n)&&n>0&&n<=5;
 const limitations=[];
 if(!valid)limitations.push('Native capture resolution must be verified at 5 cm/pixel or better.');
 if(info.sourceType!=='aerial')limitations.push('A verified aerial baseline is required for detailed detection.');
 if(!info.provider)limitations.push('Imagery source is unverified.');
 if(!info.licenseReference)limitations.push('Imagery licence reference is missing.');
 if(info.analysisPermitted!==true)limitations.push('Permission for AI analysis is unverified.');
 if(info.displayPermitted!==true)limitations.push('Permission for app display is unverified.');
 if(typeof sampling!=='number'||!Number.isFinite(sampling)||sampling<=0||sampling>.050001)limitations.push('Delivered image pixel spacing must be 5 cm or better.');
 return {eligible:!limitations.length,status:limitations.length?'unavailable':'eligible',preferredResolution:valid&&n<=3,limitations,requirement:imageryRequirement};
}
export function imageryReportFields(info={},analysisAt=null) {
 return {captureLabel:captureLabel(info),analysisAt,imageryAssessment:assessImagery(info),findingsContext:'Findings describe the captured image, not current conditions.'};
}
export function normalizeBaseline(m={}) {
 const b=m.bounds3857,w=m.width,h=m.height;
 if(!Array.isArray(b)||b.length!==4||b.some(v=>typeof v!=='number'||!Number.isFinite(v)||Math.abs(v)>20037509)||b[0]>=b[2]||b[1]>=b[3])throw Error('Supply valid EPSG:3857 bounds [west, south, east, north].');
 if(!Number.isInteger(w)||!Number.isInteger(h)||w<1||h<1||w>4096||h>4096)throw Error('Baseline dimensions must be 1–4096 native pixels per side.');
 for(const v of [m.source,m.license_reference])if(typeof v!=='string'||!v.trim()||v.length>500)throw Error('Supply the imagery source and licence reference (up to 500 characters).');
 const cy=(b[1]+b[3])/2,lat=(2*Math.atan(Math.exp(cy/6378137))-Math.PI/2)*180/Math.PI,lon=(b[0]+b[2])/2/6378137*180/Math.PI;
 const gsd=Math.max((b[2]-b[0])/w,(b[3]-b[1])/h)*Math.cos(lat*Math.PI/180);
 return {sourceType:m.source_type,provider:m.source.trim(),nativeGsdCm:m.native_gsd_cm??null,licenseReference:m.license_reference.trim(),analysisPermitted:m.analysis_permitted===true,displayPermitted:m.display_permitted===true,capturedAt:typeof m.captured_at==='string'?m.captured_at.slice(0,100):null,captureDate:typeof m.capture_date==='string'?m.capture_date.slice(0,20):null,captureDateRange:m.capture_date_range&&typeof m.capture_date_range.start==='string'&&typeof m.capture_date_range.end==='string'?{start:m.capture_date_range.start.slice(0,20),end:m.capture_date_range.end.slice(0,20)}:null,width:w,height:h,bounds3857:b,groundResolutionMeters:gsd,center:{latitude:lat,longitude:lon},historical:true,attribution:m.source.trim()};
}
export function baselineCovers(info,c) {
 const r=6378137,x=r*c.longitude*Math.PI/180,y=r*Math.log(Math.tan(Math.PI/4+c.latitude*Math.PI/360)),half=c.radiusKm*1000/Math.cos(c.latitude*Math.PI/180)*1.02;
 const [west,south,east,north]=info.bounds3857;return x-half>=west&&x+half<=east&&y-half>=south&&y+half<=north;
}
export function nativeZoomLimit(width,height,viewportWidth,viewportHeight) {
 const fit=Math.min(1,viewportWidth/width,viewportHeight/height);return Math.max(1,1/fit);
}
export function imageDimensions(bytes) {
 const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
 if(bytes.length>=24&&[137,80,78,71,13,10,26,10].every((v,i)=>bytes[i]===v)&&String.fromCharCode(...bytes.slice(12,16))==='IHDR')return {width:view.getUint32(16),height:view.getUint32(20)};
 if(bytes.length>=4&&bytes[0]===255&&bytes[1]===216){
  let i=2;while(i+4<bytes.length){if(bytes[i++]!==255)break;const marker=bytes[i++];if(marker===217||marker===218)break;const length=view.getUint16(i);if(length<2||i+length>bytes.length)break;if([192,193,194,195,197,198,199,201,202,203,205,206,207].includes(marker)&&length>=7)return {height:view.getUint16(i+3),width:view.getUint16(i+5)};i+=length;}
 }
 throw Error('The uploaded file is not a supported JPEG or PNG.');
}
