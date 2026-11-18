import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";
import { SourceTextModule } from "node:vm";
import { test } from "node:test";
import ts from "typescript";

async function assets(base = "/") {
  const source = await readFile(new URL("../src/assets.ts", import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext,
  } });
  const module = new SourceTextModule(outputText, {
    initializeImportMeta(meta) { meta.env = { BASE_URL: base }; },
  });
  await module.link(() => { throw new Error("Import inesperado"); });
  await module.evaluate();
  return module.namespace;
}

test("CV9 a CV19 possuem imagem local e seletor em ordem decrescente", async () => {
  const { LAYOUT_TOWN_HALLS, townHallUrl, hasTownHallImage } = await assets();
  assert.deepEqual([...LAYOUT_TOWN_HALLS], [19,18,17,16,15,14,13,12,11,10,9]);
  for (const cv of LAYOUT_TOWN_HALLS) {
    assert.equal(hasTownHallImage(cv), true);
    await access(new URL(`../public${townHallUrl(cv)}`, import.meta.url));
  }
});

test("CV ausente, inválido ou futuro usa alternativa embutida", async () => {
  const { townHallUrl, hasTownHallImage, TOWN_HALL_FALLBACK } = await assets();
  for (const cv of [undefined, null, 0, 8, 20, -1, 19.5, NaN, Infinity, true, "19"]) {
    assert.equal(hasTownHallImage(cv), false);
    assert.equal(townHallUrl(cv), TOWN_HALL_FALLBACK);
  }
  assert.ok(TOWN_HALL_FALLBACK.startsWith("data:image/svg+xml,"));
});

test("Imagens respeitam o caminho base de publicação", async () => {
  const { townHallUrl } = await assets("/previa/");
  assert.equal(townHallUrl(19), "/previa/assets/centros-vila/cv19.svg");
  assert.equal(townHallUrl(18), "/previa/assets/centros-vila/cv18.webp");
});

test("Arte CV19 tem dimensões e PNG embutido, sem requisição externa", async () => {
  const svg = await readFile(new URL("../public/assets/centros-vila/cv19.svg", import.meta.url), "utf8");
  assert.match(svg, /width="250" height="234" viewBox="0 0 250 234"/);
  const png = svg.match(/xlink:href="data:image\/png;base64,([^"]+)"/);
  assert.ok(png);
  assert.equal(Buffer.from(png[1], "base64").subarray(1, 4).toString(), "PNG");
  assert.doesNotMatch(svg, /(?:href|src)="https?:/);
});
