import unittest
import importlib
from types import SimpleNamespace
from unittest.mock import patch
from ww_competicao.carregar_desempenho import obter_renderizador


def antigo(st, pd, documentos, admins, usuario):
    pass


def novo(st, pd, documentos, admins, usuario, carregar_manuais=None):
    return carregar_manuais


class Carregamento(unittest.TestCase):
    def test_duas_versoes_antigas_atualizadas_na_ordem(self):
        mensal=SimpleNamespace(renderizar=antigo)
        relatorio=SimpleNamespace(renderizar=antigo)
        ordem=[]
        def atualizar(modulo):
            ordem.append(modulo)
            modulo.renderizar=novo
            return modulo
        with patch.object(importlib, 'import_module',side_effect=[mensal,relatorio]), patch.object(importlib, 'reload',side_effect=atualizar):
            callback=lambda: []
            self.assertIs(obter_renderizador()(None,None,{},[],None,carregar_manuais=callback),callback)
        self.assertEqual(ordem,[mensal,relatorio])

    def test_atual_nao_recarrega(self):
        with patch.object(importlib, 'import_module',return_value=SimpleNamespace(renderizar=novo)), patch.object(importlib, 'reload') as reload:
            self.assertIs(obter_renderizador(),novo)
            reload.assert_not_called()

    def test_arquivos_incompletos_nao_invocam_versao_antiga(self):
        velho=SimpleNamespace(renderizar=antigo)
        with patch.object(importlib, 'import_module',return_value=velho), patch.object(importlib, 'reload',return_value=velho):
            with self.assertRaises(RuntimeError):obter_renderizador()

