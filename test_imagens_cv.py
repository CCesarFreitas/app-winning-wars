import base64
import io
import unittest
from PIL import Image
from ww_competicao.imagens_cv import imagem_cv


class ImagensCV(unittest.TestCase):
    def test_todos_cvs_embutidos_validos(self):
        for cv in range(9,19):
            with self.subTest(cv=cv):
                uri=imagem_cv(cv)
                self.assertTrue(uri.startswith('data:image/webp;base64,'))
                im=Image.open(io.BytesIO(base64.b64decode(uri.split(',',1)[1])))
                im.load()
                self.assertGreaterEqual(min(im.size),90)
                self.assertEqual(im.format,'WEBP')

    def test_cvs_invalidos(self):
        for cv in (True,8,19,'18'):
            with self.assertRaises(ValueError):imagem_cv(cv)
