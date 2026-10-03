# 5LTEP-L1 · Instância Recife (experimento de controle)

[![Tests](https://github.com/lsp3cesarschool/5ltep-layer1-recife/actions/workflows/tests.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer1-recife/actions/workflows/tests.yml) [![Camada 1](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Flsp3cesarschool%2F5ltep-layer1-recife%2Fmain%2Fdocs%2Fdata%2Fstatus.pt.json)](https://github.com/lsp3cesarschool/5ltep-layer1-recife/actions/workflows/layer1.yml) [![Licença: MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-blue.svg)](LICENSE)

[English](README.md) · **Português**

**A Camada 1 (contratos estruturais) do 5L-TEP aplicada ao portal de dados abertos da Prefeitura do
Recife: uma segunda instância de [5ltep-layer1](https://github.com/lsp3cesarschool/5ltep-layer1),
montada pelo autor como caso de controle do estudo do IBAMA, num portal municipal.**

| Recurso | O que você encontra |
|---|---|
| 📊 **Painel** | [lsp3cesarschool.github.io/5ltep-layer1-recife](https://lsp3cesarschool.github.io/5ltep-layer1-recife/?lang=pt): maturidade, achados de documentação, todos os conjuntos e arquivos |
| 🔀 **Deriva de esquema** | [![issues de deriva](https://img.shields.io/github/issues/lsp3cesarschool/5ltep-layer1-recife/layer1?label=issues%20de%20deriva&color=0366d6)](https://github.com/lsp3cesarschool/5ltep-layer1-recife/issues?q=is%3Aissue+label%3Alayer1) |
| 🧑‍⚖️ **Esquemas sugeridos** | [pull requests](https://github.com/lsp3cesarschool/5ltep-layer1-recife/pulls?q=is%3Apr+schemas+suggested) com esquemas extraídos de dicionários em PDF, aguardando uma pessoa |
| 🏛️ **Instância principal** | [5ltep-layer1](https://github.com/lsp3cesarschool/5ltep-layer1): IBAMA, e a documentação completa |
| 🔁 **Outro controle** | [5ltep-layer1-aneel](https://github.com/lsp3cesarschool/5ltep-layer1-aneel): o portal da ANEEL |

> **Situação: demonstração de pesquisa.** Este repositório não é operado, afiliado nem endossado pela
> Prefeitura do Recife nem pela EMPREL; ele só lê os dados abertos da cidade. Mostra que a ferramenta
> pode ser reutilizada em outro portal. Não pressupõe que a Prefeitura vá revisar seus resultados ou
> adotá-la. Os esquemas sugeridos e as issues de deriva demonstram o fluxo; o autor não atua como revisor deles.

## Caso de uso em um parágrafo

A Prefeitura do Recife publica seus dados abertos num portal CKAN, muitos conjuntos com dicionário de
dados em mais de um formato. Suponha que alguém que reutiliza esses dados queira saber, antes de
confiar num arquivo, o que ele deveria conter e se contém. Esta instância lê todos os dicionários que o
portal publica, liga cada um aos arquivos que descreve e verifica cada CSV publicado contra o seu
esquema, semana após semana.

## Por que um experimento de controle

A ferramenta da Camada 1 foi construída sobre o portal do IBAMA, um órgão federal. O Recife é um
município, com outra equipe, outros hábitos e outro modelo de documentação. Este repositório roda **o
mesmo código**, seguindo os passos de *Rodando a sua própria instância* do README principal: só
`portal.json` (a URL do portal) e os textos deste README mudaram. Onde a documentação do Recife difere
da do IBAMA, a diferença aparece nos resultados, não no código.

## Como o Recife documenta seus dados

Conforme observado ao montar esta instância (01/10/2026); o painel tem os números atuais.

- Muitos conjuntos têm um **dicionário JSON** que segue um modelo (`metadados.campos` com código, tipo,
  tamanho e valores permitidos) e que **nomeia os recursos que descreve** pelos identificadores: a
  ligação entre dicionário e arquivo é declarada pelo publicador, em vez de adivinhada. Os mesmos
  dicionários muitas vezes também são publicados em PDF, e alguns em XLSX.
- Alguns dicionários JSON estão malformados, e pelo menos um nomeia um conjunto que não é o seu: os
  dois casos são contados nos achados de documentação.
- A maioria dos CSV está carregada no **DataStore** com tipos reais (números, datas e horas), o que os
  coloca no nível 3. Esses tipos podem ter sido inferidos pelo carregador do portal, e não declarados
  pelo publicador, por isso a validação prefere o dicionário quando existe um.

## O que mudou em relação à instância principal

| Arquivo | Mudança |
|---|---|
| `portal.json` | `portal_url` = `https://dados.recife.pe.gov.br` |
| `README.md`, `LEIAME.md`, `CITATION.cff` | este texto e a citação deste repositório |

Todo o resto é o código de `5ltep-layer1` no commit `8bddff6`
([8bddff6b86a1ca9b60c2e6cd7a23a3e9d7fbe0b3](https://github.com/lsp3cesarschool/5ltep-layer1/commit/8bddff6b86a1ca9b60c2e6cd7a23a3e9d7fbe0b3)).

## Rodando, e adaptando de novo

O workflow *5L-TEP Layer 1 Structural Contracts* roda toda segunda-feira e pode ser iniciado à mão
(*Actions → Run workflow*). Localmente:

```bash
pip install -r requirements.txt
python main.py run --minutes 10
```

Para apontá-lo para mais um portal CKAN, troque `portal_url` em `portal.json`; veja o README principal.

## Reprodutibilidade

Cada resultado registra o SHA-256 do arquivo validado, a impressão digital do esquema, os parâmetros
do método e, nas extrações de PDF, o modelo, seu digest e a versão do prompt. O código é o commit de
origem acima; os esquemas e resultados são commitados pelo workflow.

## Limitações

Valem as limitações da instância principal, inclusive os [limites de tamanho e de tempo](https://github.com/lsp3cesarschool/5ltep-layer1/blob/main/LEIAME.md#limites-de-tamanho-e-de-tempo) (o que o GitHub e o sistema aceitam). Específico do Recife: o portal não atende downloads
parciais, então cada arquivo é lido desde o início; a primeira execução do portal inteiro leva vários
lotes encadeados.

## Documentação e referências

A documentação completa (escala de maturidade, leitores, validação, etapas do PDF, deriva, achados,
segurança, configuração e referências) está no [repositório principal](https://github.com/lsp3cesarschool/5ltep-layer1/blob/main/LEIAME.md).

## Licença

MIT para o código ([LICENSE](LICENSE)). Os dados da cidade são publicados sob a Open Database License
(ODbL); este repositório guarda só esquemas e resultados agregados derivados deles.
