import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { SourceTextModule } from "node:vm";
import { test } from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../src/playerPeriod.ts", import.meta.url), "utf8");
const module = new SourceTextModule(ts.transpileModule(source, { compilerOptions: {
  target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
} }).outputText);
await module.link(() => { throw new Error("Import inesperado"); });
await module.evaluate();
const { playerForPeriod } = module.namespace;
const player = { tag: "#AAA", nome: "Jogador", temporada: "2026-11", total: 90, jogos: 10, posicao: 1 };
const audit = { player_tag: "#AAA", temporada: "2026-10", registros: [{ temporada: "2026-10" }], resumo: {
  total: 13, jogos: 5, guerra: 2, raides: 6, eventos: 0, posicao: null, origem: "fotografia_fechamento",
} };

test("Tela e PNG recebem totais do mês selecionado, sem posição atual", () => {
  const result = playerForPeriod(player, audit);
  assert.equal(result.temporada, "2026-10");
  assert.equal(result.total, 13);
  assert.equal(result.jogos, 5);
  assert.equal(result.posicao, null);
  assert.equal(player.total, 90);
});
test("Ausência de total histórico não reutiliza o atual", () => {
  const result = playerForPeriod(player, { ...audit, resumo: { ...audit.resumo, total: null, jogos: null } });
  assert.equal(result.total, null);
  assert.equal(result.jogos, null);
});
test("Bloqueia mistura de meses e resposta atrasada de outro jogador", () => {
  assert.throws(() => playerForPeriod(player, { ...audit, registros: [{ temporada: "2026-09" }] }));
  assert.throws(() => playerForPeriod(player, { ...audit, player_tag: "#BBB" }));
  assert.throws(() => playerForPeriod(player, { ...audit, resumo: undefined }));
});
