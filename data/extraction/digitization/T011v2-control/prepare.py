"""Reproduce T011v2 local source rasters, index sheets and overlays."""
from pathlib import Path
import hashlib
import io
import json
import sys
import fitz
import numpy as np
from PIL import Image, ImageDraw
import yaml

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
sys.path.insert(0,str(OUT))
from geometric_check import PANELS, dump

def main():
    tmp=ROOT/'tmp/T011v2-pages';tmp.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for name,targets in PANELS.items():
        d=yaml.safe_load((ROOT/f'data/extraction/digitization/T011-{name}.digitization.yaml').read_text())
        pdf=ROOT/'data/raw/pdf'/('S105_T011.pdf' if name.startswith('S105') else 'S106.pdf')
        h=hashlib.sha256(pdf.read_bytes()).hexdigest();assert h==d['source_pdf_sha256']
        doc=fitz.open(pdf);page=doc[d['pdf_page']-1]
        iminfo=page.get_images(full=True)[d['source_image_index']]
        rect=page.get_image_rects(iminfo[0])[0]
        page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(tmp/f'{name}-page.png')
        crop=d['crop_native_pixels']
        clip=fitz.Rect(rect.x0+crop[0]/iminfo[2]*rect.width,rect.y0+crop[1]/iminfo[3]*rect.height,
                       rect.x0+crop[2]/iminfo[2]*rect.width,rect.y0+crop[3]/iminfo[3]*rect.height)
        page.get_pixmap(matrix=fitz.Matrix(6,6),clip=clip).save(OUT/f'{name}-render.png')
        im=Image.open(io.BytesIO(doc.extract_image(iminfo[0])['image'])).crop(crop).convert('RGB')
        im.save(OUT/f'{name}-native.png')
        manifest.append({'panel':name,'source':str(pdf.relative_to(ROOT)),'source_sha256':h,
                         'pdf_page_1based':d['pdf_page'],'source_image_index_0based':d['source_image_index'],
                         'image_xref':iminfo[0],'pdf_image_rect_points':list(rect),'crop_native_pixels':crop,
                         'native_png_sha256':hashlib.sha256((OUT/f'{name}-native.png').read_bytes()).hexdigest(),
                         'render_scale':6,'full_page_local_artifact':str((tmp/f'{name}-page.png').relative_to(ROOT)),
                         'attribution':'S105: Materials 2018, 11, 589, Figs 8/9; S106: G. Jajko et al., Microporous and Mesoporous Materials 330 (2022) 111555, Fig4; source excerpts for verification'})
        for si in targets:
            s=d['series'][si];rs=s['pixels'];n=len(rs)
            sheet=Image.new('RGB',(840,((n+7)//8)*120),'white');dr=ImageDraw.Draw(sheet)
            recs={tuple(r['pixel']) for r in s['recoveries']}
            for j,(x,y) in enumerate(rs):
                half=22 if name!='S106-Fig4' else 13
                box=(round(x)-half,round(y)-half,round(x)+half+1,round(y)+half+1)
                a=j%8*105;b=j//8*120
                sheet.paste(im.crop(box).resize((90,90),Image.Resampling.NEAREST),(a,b+25))
                dr.text((a,b+4),f'{j+1}'+(' REC' if (x,y) in recs else ''),fill='black')
            sheet.save(OUT/f'{name}-s{si}-census.png')
            ov=im.copy();od=ImageDraw.Draw(ov)
            for j,(x,y) in enumerate(rs):
                od.ellipse((x-19,y-19,x+19,y+19),outline='#dd7800',width=2)
                od.text((x-10,y+22+(j%2)*12),str(j+1),fill='#bb4400')
            ov.save(OUT/f'{name}-s{si}-overlay.png')
        rs=[r for s in d['series'] for r in s.get('recoveries',[])]
        sheet=Image.new('RGB',(700,((len(rs)+3)//4)*220),'white');dr=ImageDraw.Draw(sheet)
        for j,r in enumerate(rs):
            x,y=r['pixel'];box=(int(x)-23,int(y)-23,int(x)+24,int(y)+24);a=j%4*175;b=j//4*220
            sheet.paste(im.crop(box).resize((141,141),Image.Resampling.NEAREST),(a,b+45))
            dr.text((a,b+4),r['id'].split('-s')[-1],fill='black');dr.text((a,b+20),str((x,y)),fill='black')
        sheet.save(OUT/f'{name}-recoveries.png')
    for name,box in [('S105-Fig8A',(220,1170,470,1380)),('S105-Fig8C',(195,1120,385,1360)),
                     ('S105-Fig9',(295,1190,610,1445)),('S106-Fig4',(185,585,395,680))]:
        im=Image.open(OUT/f'{name}-native.png')
        im.crop(box).resize(((box[2]-box[0])*3,(box[3]-box[1])*3),Image.Resampling.NEAREST).save(OUT/f'{name}-origin-detail.png')
    im=Image.open(OUT/'S106-Fig4-native.png')
    im.crop((182,625,239,676)).resize((684,612),Image.Resampling.NEAREST).save(OUT/'S106-subminimum.png')
    dump(OUT/'source_manifest.json',{'tool':'PyMuPDF','version':fitz.VersionBind,'sources':manifest})

if __name__=='__main__':main()
