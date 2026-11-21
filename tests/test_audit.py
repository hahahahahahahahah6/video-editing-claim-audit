import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from video_editing_claim_audit.audit import audit, evidence
from video_editing_claim_audit.phrases import VIDEOEDITING, NOVIDEOEDITING, GENERIC_NAMES

class AuditTests(unittest.TestCase):
    def test_phrases(self):
        self.assertEqual((len(VIDEOEDITING), len(NOVIDEOEDITING), len(GENERIC_NAMES)), (50, 24, 24))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); doc = root / 'README.md'; src = root / 'app.py'
            for phrase in VIDEOEDITING:
                with self.subTest(phrase=phrase):
                    doc.write_text(phrase); src.unlink(missing_ok=True)
                    self.assertEqual(audit(root)['verdict'], 'FAIL')
                    src.write_text('x.edit_video()'); self.assertEqual(audit(root)['verdict'], 'PASS')
            for phrase in NOVIDEOEDITING:
                with self.subTest(phrase=phrase):
                    doc.write_text(phrase); src.unlink(missing_ok=True)
                    self.assertEqual(audit(root)['verdict'], 'PASS')
                    src.write_text('x.edit_video()'); r = audit(root)
                    self.assertEqual(len(r['findings']), 1); self.assertEqual(r['findings'][0]['rule'], 'documented-no-video-editing-claim-false')

    def test_routes(self):
        methods = 'subclipped with_section_cut_out with_speed_scaled cropped resized with_audio with_effects_on_subclip'.split()
        sources = ['import moviepy as m; clip=m.VideoFileClip(); clip.%s()' % n for n in methods]
        sources += ['from moviepy import VideoFileClip as V; V(); x.subclipped()', 'from moviepy import concatenate_videoclips as c; c()', 'import moviepy as m; m.concatenate_videoclips()', 'from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips as c; c()']
        sources += ['import ffmpeg as f; f.input(); x.filter("trim"); f.output()', 'from ffmpeg import input as i, concat as c, run as r; i(); c(); r()', 'import ffmpeg; ffmpeg.input(); x.filter(filter_name="CROP"); stream.run()']
        sources += ['import cv2; cv2.VideoCapture("A.MP4"); x.read(); cv2.VideoWriter()', 'from cv2 import VideoCapture as C, VideoWriter as W; C("x.avi"); x.read(); W()']
        sources += ['import imageio; imageio.get_reader(); imageio.get_writer()', 'import imageio.v2 as i; i.get_reader(); i.get_writer()', 'from imageio.v2 import get_reader as r, get_writer as w; r(); w()']
        sources += ['x.%s()' % n for n in GENERIC_NAMES] + ['from lib import %s as f; f()' % n for n in GENERIC_NAMES]
        for source in sources:
            with self.subTest(source=source): self.assertTrue(evidence(source))

    def test_non_routes(self):
        sources = ['import '+n for n in ('moviepy','ffmpeg','cv2','imageio','pydub','PIL')]
        sources += ['import moviepy; moviepy.VideoFileClip()', 'x.subclipped()', 'concatenate_videoclips()', 'import ffmpeg; ffmpeg.input()', 'x.filter("trim")', 'import ffmpeg; ffmpeg.concat()', 'import ffmpeg; ffmpeg.output()', 'x.run()', 'import ffmpeg; ffmpeg.input(); ffmpeg.output()', 'import ffmpeg; ffmpeg.input(); x.filter("hflip"); x.run()']
        sources += ['import cv2; cv2.VideoCapture(0); x.read(); cv2.VideoWriter()', 'import cv2; cv2.VideoCapture(path); x.read(); cv2.VideoWriter()', 'import cv2; cv2.VideoCapture("x.png"); x.read(); cv2.VideoWriter()', 'import cv2; cv2.VideoCapture("x.mp4"); x.read()', 'import cv2; cv2.VideoWriter()', 'import imageio; imageio.get_reader()', 'import imageio; imageio.get_writer()', 'from imageio.v2 import get_reader; get_reader()']
        sources += ['edit_video()', 'def edit_video(): pass\nx.edit_video()', 'import moviepy\nwith obj as moviepy: pass\nmoviepy.VideoFileClip(); x.subclipped()', 'import moviepy; moviepy.VideoFileClip', '"edit video"', 'invalid syntax !!!', 'from PIL import Image; Image.open().resize()', 'import subprocess; subprocess.run(["ffmpeg"])']
        for source in sources:
            with self.subTest(source=source): self.assertFalse(evidence(source))

    def test_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); doc=root/'README.md'; doc.write_text("doesn't edit video")
            self.assertEqual(audit(root)['verdict'], 'PASS')
            (root/'app.py').write_text('x.edit_video()'); self.assertEqual(len(audit(root)['findings']),1)
            (root/'app.py').unlink(); doc.write_text('edit video'); self.assertEqual(audit(root)['findings'][0]['severity'],'HIGH')
            (root/'tests').mkdir(); (root/'tests/test_x.py').write_text('x.edit_video()')
            self.assertEqual(audit(root)['findings'][0]['severity'],'MEDIUM'); self.assertEqual(audit(root)['verdict'],'PASS'); self.assertEqual(audit(root,fail_on='medium')['verdict'],'FAIL')
            doc.write_text('```\nedit video\n```'); self.assertEqual(audit(root)['verdict'],'PASS')
            doc.write_text('`edit video`'); self.assertEqual(audit(root,fail_on='medium')['verdict'],'FAIL')

    def test_split_ignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'README.md').write_text('edit video'); (root/'a.py').write_text('import moviepy; moviepy.VideoFileClip()'); (root/'b.py').write_text('x.subclipped()')
            self.assertEqual(audit(root)['verdict'],'FAIL')
            (root/'b.py').write_text('x.edit_video()'); (root/'link.py').symlink_to(root/'b.py')
            self.assertEqual(audit(root,ignore=['b.py'])['verdict'],'FAIL')

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'README.md').write_text('edit video')
            cmd=[sys.executable,'-m','video_editing_claim_audit']
            p=subprocess.run(cmd+['audit',tmp,'--json'],capture_output=True,text=True); self.assertEqual(p.returncode,2); self.assertEqual(set(json.loads(p.stdout)),{'verdict','findings'})
            self.assertEqual(subprocess.run(cmd+['audit',tmp,'--ignore','README.md'],capture_output=True).returncode,0)
            self.assertEqual(subprocess.run(cmd+['audit',tmp+'/missing'],capture_output=True).returncode,1)
            self.assertEqual(subprocess.run(cmd+['--version'],capture_output=True,text=True).stdout.strip(),'0.1.0')
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(audit(root)['verdict'],'PASS')
        self.assertEqual(subprocess.run([sys.executable,'-m','video_editing_claim_audit','audit',str(root)],capture_output=True).returncode,0)

if __name__ == '__main__': unittest.main()
