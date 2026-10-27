"""Ficha de feedback: somente resultados conhecidos, sem presumir ausências."""
import io
from .desempenho_mensal import linhas, NOMES, CORES, PLOT_LOCK


def indicadores(conta, tipo):
    regs=[r for r in conta['registros'] if r['tipo']==tipo]
    rows=linhas([conta],tipo)
    if not rows:return None
    r=dict(rows[0]);completas=zeradas=conhecidas=0
    for reg in regs:
        j=reg['jogador']
        n=j.get('quantidade_ataques') if tipo=='raide' else len(j['ataques'])
        limite=j.get('limite_ataques')
        if type(n) is int and n>=0:
            zeradas+=int(n==0)
            if type(limite) is int and limite>0 and n<=limite:
                conhecidas+=1;completas+=int(n==limite)
    r.update(completas=completas,zeradas=zeradas,conhecidas=conhecidas)
    return r


def exportar(conta,mes,stamp,jogos=None,jogos_estado='pendente',total_raides=None):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.font_manager import findfont
    from matplotlib.ft2font import FT2Font
    with PLOT_LOCK:
        cmap=FT2Font(findfont('DejaVu Sans')).get_charmap()
        nome=''.join(c for c in conta['nome'] if ord(c) in cmap)[:60]
        fig=Figure(figsize=(12,15),dpi=250,facecolor='#edf2f7');FigureCanvasAgg(fig)
        def texto(x,y,t,size=12,weight='normal'):
            fig.text(x,y,t,fontsize=size,color='#23394d',weight=weight,parse_math=False)
        texto(.06,.958,'WINNING WARS  |  FEEDBACK INDIVIDUAL',13,'bold')
        texto(.06,.923,nome,23,'bold')
        texto(.06,.896,conta['tag']+'  •  Mês '+mes+'  •  Atividades encerradas',12)
        for i,tipo in enumerate(NOMES):
            top=.855-i*.205
            ax=fig.add_axes([.045,top-.185,.91,.19]);ax.set_facecolor('white')
            ax.set_xticks([]);ax.set_yticks([])
            for spine in ax.spines.values():spine.set_visible(False)
            texto(.065,top-.017,NOMES[tipo].upper(),15,'bold')
            r=indicadores(conta,tipo)
            if not r:
                texto(.065,top-.065,'Sem participação registrada neste mês.',15)
                texto(.065,top-.103,'Ausência no histórico não comprova inatividade.',11)
                continue
            unidade='raides' if tipo=='raide' else ('rodadas' if tipo=='liga' else 'guerras')
            texto(.065,top-.052,f"{unidade.capitalize()} com registro: {r['atividades']}  •  Ataques feitos: {r['ataques']}",17,'bold')
            faltas=str(r['faltas']) if r['faltas'] is not None else 'não informado'
            texto(.065,top-.078,f"Ataques completos: {r['completas']}/{r['conhecidas']} atividades  |  Sem atacar: {r['zeradas']}  |  Ataques não usados: {faltas}",10)
            bar=fig.add_axes([.065,top-.118,.57,.018]);bar.set_xlim(0,100);bar.set_ylim(-.5,.5);bar.axis('off')
            if tipo!='raide':
                if r['ataques'] and r['completos']:
                    left=0
                    for n in (3,2,1,0):
                        v=100*r['estrelas'][n]/r['ataques'];bar.barh(0,v,left=left,color=CORES[n]);left+=v
                    texto(.665,top-.115,f"{r['taxa3']:.1f}% de 3 estrelas",15,'bold')
                else:texto(.065,top-.115,'Sem taxa confiável de estrelas',12)
                for pos,n in enumerate((3,2,1,0)):
                    x=.065+pos*.215
                    texto(x,top-.145,f"{n} estrelas: {r['estrelas'][n]}",12)
                    fig.text(x-.012,top-.145,'●',color=CORES[n],fontsize=10)
                texto(.065,top-.169,'Atenção: completar os ataques disponíveis.' if r['faltas'] else 'Avaliar qualidade dos ataques considerando os CVs dos alvos.',10)
            else:
                if r['uso'] is not None:
                    bar.barh(0,100,color='#e0e7ef');bar.barh(0,r['uso'],color='#168775')
                    texto(.665,top-.115,f"{r['uso']:.1f}% dos ataques",15,'bold')
                saque=f"{r['saque_medio']:,.0f}" if r['saque_medio'] is not None else 'não informado'
                texto(.065,top-.145,'Saque médio por ataque: '+saque,12)
                cobertura=f"Registro em {r['atividades']}/{total_raides} raides do clã no histórico do mês." if total_raides is not None else 'Não é possível confirmar presença em todos os raides do mês.'
                texto(.065,top-.169,cobertura,10)
        texto(.065,.212,'JOGOS DO CLÃ',15,'bold')
        if jogos is not None:
            texto(.065,.177,f"{jogos['jogo']:,} pontos no jogo   •   {jogos['competicao']} pontos na competição",18,'bold')
            texto(.065,.148,'Último lançamento auditado: '+jogos['data'],10)
        else:
            texto(.065,.177,'Consulta indisponível' if jogos_estado=='erro' else 'Aguardando lançamento confirmado',17,'bold')
            texto(.065,.148,'Sem resultado confirmado não significa zero pontos.',11)
        texto(.065,.105,'CONTEXTO PARA O FEEDBACK',11,'bold')
        texto(.065,.082,'Ausências no histórico não comprovam faltas: considerar entrada no clã e escalação.',10)
        texto(.065,.065,'Ataques completos usam limites conhecidos. Estrelas são desempenho, não pontos da competição.',9)
        texto(.065,.048,'Poucos ataques e diferenças de CV exigem contexto. Raides não têm estrelas individuais neste relatório.',9)
        texto(.065,.025,'Atualização do histórico: '+stamp,9)
        out=io.BytesIO();fig.savefig(out,format='png',dpi=250);fig.clear()
        return out.getvalue()
