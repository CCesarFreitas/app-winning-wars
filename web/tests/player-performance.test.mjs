import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { SourceTextModule } from "node:vm";
import { test } from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/playerPerformance.ts", import.meta.url), "utf8");
const module = new SourceTextModule(ts.transpileModule(source, { compilerOptions: {
  target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
} }).outputText);
await module.link(() => { throw new Error("Import inesperado"); });
await module.evaluate();

const { battlePerformance, leagueRounds } = module.namespace;
const record = (id, tipo, rodada, stars) => ({identificador:id,tipo,rodada,jogador:{limite_ataques:tipo==='liga'?1:2,pontos_competicao:3,ataques:stars.map(estrelas=>({estrelas}))}});
test('Liga não mistura guerra e reserva não vira falta', () => {
 const records=[record('l1','liga',1,[3]),record('l2','liga',2,[1]),record('l4','liga',4,[]),record('g','guerra',null,[3,3])];
 const s=battlePerformance(records,'liga');
 assert.equal(s.activities.length,3); assert.equal(s.attacks.length,2);
 assert.equal(s.noAttack,1); assert.equal(s.missing,1);
 assert.equal(s.tripleRate,50); assert.equal(s.average,2);
 assert.deepEqual(Array.from(s.distribution),[0,1,0,1]);
 const rounds=leagueRounds(records,[1,2,3,4]);
 assert.equal(rounds[2].label,'Não escalado');
 assert.equal(rounds[3].label,'Não atacou');
 assert.equal(rounds[4].label,'Sem registro');
});
test('Guerras contam dois ataques, sem misturar liga nem versões repetidas', () => {
 const r=record('g','guerra',null,[2]);
 const s=battlePerformance([r,r,record('l','liga',1,[3])],'guerra');
 assert.equal(s.activities.length,1); assert.equal(s.missing,1); assert.equal(s.noAttack,0);
 assert.equal(s.average,2); assert.equal(s.tripleRate,0);
});
test('Sem ataques não inventa taxa e dados incompletos não são faltas', () => {
 assert.equal(battlePerformance([],'liga').tripleRate,null);
 const r=record('l','liga',1,[]); delete r.jogador.ataques;
 const s=battlePerformance([r],'liga'); assert.equal(s.noAttack,0); assert.equal(s.missing,null);
 assert.equal(leagueRounds([r],[1])[0].label,'Ataque indisponível');
});
