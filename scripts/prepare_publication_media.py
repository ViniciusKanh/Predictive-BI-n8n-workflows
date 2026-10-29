"""Reproduz a seleção editorial da gravação demonstrativa do autor.

Requer OpenCV e Pillow. Preserva os originais e remove barras do navegador.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import cv2
from PIL import Image


def main():
    parser=argparse.ArgumentParser(description='Prepara a galeria revisada do Predictive BI: prints, GIFs e logo original.')
    parser.add_argument('--video',type=Path,required=True)
    parser.add_argument('--logo',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    video=args.video.resolve(strict=True)
    logo=args.logo.resolve(strict=True)
    output=root/'docs/media';output.mkdir(parents=True,exist_ok=True)
    branding=root/'frontend/public/branding';branding.mkdir(parents=True,exist_ok=True)
    shutil.copy2(logo,branding/'predictive-bi.png')
    capture=cv2.VideoCapture(str(video));assert capture.isOpened()
    fps=capture.get(cv2.CAP_PROP_FPS)
    manifest={'source':'2026-10-29 14-50-45.mp4','source_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
              'duration_seconds':capture.get(cv2.CAP_PROP_FRAME_COUNT)/fps,'source_fps':fps,
              'crop':{'x':0,'y':80,'width':1270,'height':608},
              'privacy':'Barras do navegador, favoritos e área externa ao aplicativo removidos. Os gráficos não foram retocados.',
              'logo_sha256':hashlib.sha256(logo.read_bytes()).hexdigest(),'screenshots':[],'clips':[]}
    frames=[('n8n-complete',10,'Canvas do fluxo completo no n8n'),('n8n-backend',38,'Backend de leitura com Webhook, validação e resposta'),
            ('overview',44,'Overview: indicadores e trajetória de receita'),('sales',56,'Sales Analytics com recorte comercial'),
            ('forecast',62,'Receita prevista e comparação com baseline'),('churn',76,'Probabilidades de churn e explicabilidade'),
            ('segmentation',84,'Segmentação RFM e perfis'),('analyst',103,'Analista com evidências e modo identificado'),
            ('models',108,'Comparação dos modelos e backtesting'),('quality',110,'Qualidade e reconciliação'),
            ('pipelines',114,'Monitoramento e histórico de execuções')]
    def read(second):
        capture.set(cv2.CAP_PROP_POS_MSEC,second*1000)
        ok,frame=capture.read();assert ok,second
        return cv2.cvtColor(frame[80:688,:1270],cv2.COLOR_BGR2RGB)
    for name,second,caption in frames:
        image=Image.fromarray(read(second))
        file=output/(name+'.jpg');image.save(file,quality=88,optimize=True)
        manifest['screenshots'].append({'file':file.name,'second':second,'caption':caption})
    clips=[('workflow-tour',10,18,'Percurso no canvas n8n'),('dashboard-tour',40,56,'Overview, filtros e exploração comercial'),
           ('forecast-tour',58,64,'Inspeção da previsão de receita'),('analyst-tour',91,101,'Analista e evidências estruturadas')]
    for name,start,end,caption in clips:
        images=[]
        for frame_index in range(int((end-start)*3)):
            image=Image.fromarray(read(start+frame_index/3))
            image.thumbnail((720,360))
            images.append(image)
        file=output/(name+'.gif')
        palette=images[0].quantize(colors=64,method=Image.Quantize.MEDIANCUT)
        images=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in images]
        images[0].save(file,save_all=True,append_images=images[1:],duration=333,loop=0,optimize=True,disposal=1)
        manifest['clips'].append({'file':file.name,'start':start,'end':end,'fps':3,'audio':False,'caption':caption})
    capture.release()
    (output/'media-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'screenshots':len(frames),'clips':len(clips),'files':[{ 'file':f.name,'bytes':f.stat().st_size} for f in output.iterdir()]},ensure_ascii=False))


if __name__ == "__main__":
    main()
