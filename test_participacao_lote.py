import copy
import unittest
import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from datetime import datetime
from ww_competicao.participacao_lote import preparar_lote, conferir_lote
from ww_competicao.participacao_competicao import PC_CABECALHO, pc_estado, pc_ler_eventos
from ww_competicao.participacao_competicao import pc_validar_admin

class ParticipacaoLote(unittest.TestCase):
    def setUp(self):
        self.data = '2026-10-01T12:00:00-03:00'
        self.linhas = [PC_CABECALHO,
            ['a', '#222', 'Nome ♤', 'TRUE', 'admin', 'Importado', self.data, 'CADASTRO'],
            ['b', '#PPP', 'Outro', 'TRUE', 'admin', 'Importado', self.data, 'CADASTRO']]
        self.admins = [['Usuario','Nivel'],['admin','Co-líder']]
        self.selecao = {'#222':'a','#PPP':'b'}
    def preparar(self, **kwargs):
        args = dict(linhas=self.linhas, admins=self.admins, usuario='admin', selecoes=self.selecao,
            habilitada=False, motivo='Contas secundárias', lote_id='085cbba2-27c5-48e1-b77d-b9702b982f9e', data=self.data)
        args.update(kwargs)
        return preparar_lote(**args)
    def test_lote_auditavel_sem_mudar_fontes(self):
        antes=copy.deepcopy(self.linhas)
        novas=self.preparar()
        self.assertEqual(antes,self.linhas)
        self.assertEqual(len(novas),2)
        self.assertEqual(novas[0][2],'Nome ♤')
        self.assertEqual(len({r[0] for r in novas}),2)
        self.assertTrue(all(r[3]=='FALSE' and r[7]=='ADMIN' for r in novas))
        self.assertTrue(conferir_lote(self.linhas+novas,novas))
    def test_admin_revogado_bloqueia(self):
        with self.assertRaises(PermissionError): self.preparar(admins=[['Usuario','Nivel'],['admin','Membro']])
    def test_uma_conta_alterada_bloqueia_lote_inteiro(self):
        self.linhas.append(['c','#PPP','Outro','FALSE','admin','Mudou',self.data,'ADMIN'])
        with self.assertRaises(ValueError): self.preparar()
    def test_resposta_perdida_conferida_sem_reenvio(self):
        novas=self.preparar(); self.linhas+=novas
        self.assertTrue(conferir_lote(self.linhas,novas))
        with self.assertRaises(ValueError): self.preparar()
    def test_confirmacao_parcial_nao_aceita(self):
        novas=self.preparar()
        self.assertFalse(conferir_lote(self.linhas+novas[:1],novas))
    def test_dados_divergentes_bloqueados(self):
        novas=self.preparar(); alteradas=copy.deepcopy(novas); alteradas[0][3]='TRUE'
        with self.assertRaises(ValueError): conferir_lote(self.linhas+alteradas,novas)
    def test_vazio_motivo_curto_e_conta_desconhecida(self):
        for op in ({'selecoes':{}},{'motivo':'a'},{'selecoes':{'#GGG':'x'}}):
            with self.assertRaises(ValueError): self.preparar(**op)
    def test_habilitar_preserva_historico(self):
        novas=self.preparar(); self.linhas+=novas
        mais=self.preparar(selecoes={r[1]:r[0] for r in novas}, habilitada=True,
            lote_id='616e53fc-6e0b-42b4-b03a-0d60ddf3dd29')
        self.assertTrue(all(c['Habilitada']=='TRUE' for c in pc_estado(pc_ler_eventos(self.linhas+mais)).values()))
        self.assertEqual(len(self.linhas+mais),7)

    def painel(self):
        st=MagicMock(); st.session_state={'admin_logado':'admin'}
        st.button.return_value=False
        st.text_input.side_effect=lambda label,**kw: 'Contas secundárias' if label=='Motivo da alteração' else ''
        st.radio.return_value='Bloquear participação'
        st.checkbox.return_value=False
        st.multiselect.return_value=['#222','#PPP']
        st.selectbox.return_value='#222'
        st.form_submit_button.return_value=True
        class Rerun(Exception): pass
        st.rerun.side_effect=Rerun
        aba=MagicMock(); aba.get_all_values.side_effect=lambda **kw: copy.deepcopy(self.linhas)
        aba.append_rows.side_effect=lambda rows,**kw: self.linhas.extend(rows)
        admins=MagicMock(); admins.get_all_values.return_value=self.admins
        tree=ast.parse(Path('app.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='renderizar_permissoes_competicao')
        env=dict(st=st, pd=SimpleNamespace(DataFrame=lambda x:x),json=json,
            pc_validar_admin=pc_validar_admin,pc_estado=pc_estado,pc_ler_eventos=pc_ler_eventos,
            PC_ABA='ParticipacaoCompeticao',planilha_competicao=SimpleNamespace(id='oficial'),
            ww_admins_exibicao=lambda _:self.admins,ww_aba_painel=lambda *_:aba,
            ww_controle_exibicao=lambda _:copy.deepcopy(self.linhas),nome_conta=lambda tag,n:n,
            ww_limpar_painel=MagicMock(),sheet_admins=admins,
            agora_winning_wars=lambda:datetime.fromisoformat(self.data))
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'painel','exec'),env)
        return st,aba,env['renderizar_permissoes_competicao'],Rerun

    def test_painel_revisao_sem_escrita_e_confirmacao_unica(self):
        st,aba,render,Rerun=self.painel()
        with self.assertRaises(Rerun): render()
        aba.append_rows.assert_not_called()
        self.assertEqual(len(st.session_state['ww_participacao_lote_proposta']['selecoes']),2)
        st.button.side_effect=lambda label,**kw: label=='Confirmar e salvar lote'
        with self.assertRaises(Rerun): render()
        aba.append_rows.assert_called_once()
        self.assertNotIn('ww_participacao_envio_pendente',st.session_state)

    def test_painel_recupera_resposta_perdida_sem_repetir(self):
        st,aba,render,Rerun=self.painel()
        with self.assertRaises(Rerun): render()
        st.button.side_effect=lambda label,**kw: label=='Confirmar e salvar lote'
        def perder(rows,**kw):
            self.linhas.extend(rows)
            raise TimeoutError()
        aba.append_rows.side_effect=perder
        with self.assertRaises(Rerun): render()
        self.assertIn('ww_participacao_envio_pendente',st.session_state)
        with self.assertRaises(Rerun): render()
        aba.append_rows.assert_called_once()
        self.assertNotIn('ww_participacao_envio_pendente',st.session_state)

if __name__=='__main__': unittest.main()
