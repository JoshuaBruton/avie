"""Unclassified visual proposals. Scores rank proposals, never identify their meaning."""
import math
import cv2
import numpy as np

def overlap(a,b):
    x1,y1=max(a[0],b[0]),max(a[1],b[1]);x2,y2=min(a[2],b[2]),min(a[3],b[3]);intersection=max(0,x2-x1)*max(0,y2-y1)
    return intersection/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)

def propose_features(frame,meters_per_pixel,existing=(),limit=200):
    height,width=frame.shape[:2];scale=min(1,2048/max(width,height));small=cv2.resize(frame,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale<1 else frame
    hsv=cv2.cvtColor(small,cv2.COLOR_BGR2HSV);value=hsv[:,:,2];threshold=max(160,min(225,float(np.percentile(value,90))))
    mask=((value>=threshold)&(hsv[:,:,1]<100)).astype(np.uint8)*255
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);items=[]
    for contour in contours:
        area=cv2.contourArea(contour);x,y,w,h=cv2.boundingRect(contour);ground_width=w/scale*meters_per_pixel;ground_height=h/scale*meters_per_pixel
        if not (3<=ground_width<=250 and 3<=ground_height<=250 and 12<=area/(scale*scale)*meters_per_pixel**2<=30000):continue
        if max(w,h)/max(1,min(w,h))>6 or area/(w*h)<.35:continue
        perimeter=cv2.arcLength(contour,True);circularity=4*math.pi*area/max(perimeter**2,1);hull=cv2.convexHull(contour);solidity=area/max(cv2.contourArea(hull),1)
        if solidity<.7:continue
        box=[x/scale,y/scale,(x+w)/scale,(y+h)/scale]
        if any(overlap(box,b)>.2 for b in existing):continue
        polygon=cv2.approxPolyDP(contour,.015*perimeter,True).reshape(-1,2)/scale
        shape='Rounded bright feature' if circularity>.68 else 'Compact bright feature'
        items.append({'box':box,'polygon':polygon.tolist()[:64],'description':shape+' selected by image geometry; its identity and whether it is man-made are unknown.','rank':area*solidity})
    items.sort(key=lambda p:p['rank'],reverse=True);kept=[]
    for item in items:
        if any(overlap(item['box'],p['box'])>.35 for p in kept):continue
        kept.append(item)
        if len(kept)>=limit:break
    return kept
