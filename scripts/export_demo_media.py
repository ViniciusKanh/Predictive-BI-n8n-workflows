"""Extrai prints e cortes silenciosos; copia o logo original sem redesenho.

OpenCV é opcional, necessário apenas para preparar a mídia da documentação.
"""

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path)
    parser.add_argument('--logo', type=Path)
    parser.add_argument('--frames', default='10,30,60')
    parser.add_argument('--clips', default='', help='Intervalos início:fim em segundos, separados por vírgula.')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/media')
    args = parser.parse_args()
    if not args.video and not args.logo:
        parser.error('Informe --video e/ou --logo.')
    args.output.mkdir(parents=True, exist_ok=True)
    result = {'frames': [], 'clips': [], 'logo': None}
    if args.logo:
        if args.logo.suffix.lower() != '.png':
            parser.error('Use o PNG original do logo; não há conversão da imagem.')
        origin = args.logo.resolve(strict=True)
        branding = ROOT / 'frontend/public/branding'
        branding.mkdir(parents=True, exist_ok=True)
        for destination in (branding / 'predictive-bi.png', args.output / 'predictive-bi-logo.png'):
            if destination.resolve() != origin:
                shutil.copy2(origin, destination)
        result['logo'] = 'Cópia exata do PNG fornecido pelo autor.'
    if args.video:
        import cv2
        capture = cv2.VideoCapture(str(args.video.resolve(strict=True)))
        if not capture.isOpened():
            raise RuntimeError('Não foi possível abrir o vídeo.')
        fps = capture.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            raise ValueError('Taxa de quadros inválida.')
        duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps
        result.update(duration_seconds=duration, source_fps=fps)
        try:
            for index, second in enumerate(map(float, args.frames.split(',')), 1):
                if not 0 <= second < duration:
                    raise ValueError(f'Instante fora do vídeo: {second}s; duração {duration:.1f}s.')
                capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError('Falha ao ler quadro.')
                destination = args.output / f'capture-{index:02d}.jpg'
                if not cv2.imwrite(str(destination), frame, [cv2.IMWRITE_JPEG_QUALITY, 90]):
                    raise RuntimeError('Falha ao salvar print.')
                result['frames'].append({'file': destination.name, 'second': second})
            for index, interval in enumerate(filter(None, args.clips.split(',')), 1):
                start, end = map(float, interval.split(':'))
                if not 0 <= start < end <= duration:
                    raise ValueError('Intervalo de corte inválido.')
                capture.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError('Falha ao ler início do corte.')
                height, width = frame.shape[:2]
                destination = args.output / f'demo-{index:02d}.mp4'
                writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
                if not writer.isOpened():
                    raise RuntimeError('Codec MP4 indisponível.')
                try:
                    for offset in range(int((end - start) * fps)):
                        if offset:
                            ok, frame = capture.read()
                        if not ok:
                            raise RuntimeError('Vídeo terminou antes do intervalo solicitado.')
                        writer.write(frame)
                finally:
                    writer.release()
                result['clips'].append({'file': destination.name, 'start': start, 'end': end, 'audio': False})
        finally:
            capture.release()
    (args.output / 'media-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
