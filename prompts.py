import json

# Novo gabarito exemplo para referência
GABARITO_EXEMPLO = [
    {"entidade": "ACÓRDÃO", "tipo": "Título"},
    {"entidade": "Agravo de Instrumento nº 2116753-11.2020.8.26.0000", "tipo": "Nome_Recurso"},
    {"entidade": "Comarca de São Paulo", "tipo": "Origem"},
    {"entidade": "Banco do Brasil S/A", "tipo": "Recorrido"},
    {"entidade": "João da Silva", "tipo": "Recorrente"},
    {"entidade": "Ministro Paulo de Tarso Sanseverino", "tipo": "Nome_Desembargador/Ministro"},
    {"entidade": "Deram provimento ao recurso", "tipo": "Resultado_Acórdão"},
    {"entidade": "7 de julho de 2023", "tipo": "Data"},
    {"entidade": "Cézar Zalaf", "tipo": "Nome_Relator"},
    {"entidade": "VOTO Nº 5219", "tipo": "Voto"},
    {"entidade": "17ª Câmara de Direito Privado", "tipo": "Orgao_Julgador"},
    {"entidade": "EXPURGOS INFLACIONÁRIOS", "tipo": "Tema_Keyword"},
    {"entidade": "JUROS REMUNERATÓRIOS", "tipo": "Tema_Keyword"},
    {"entidade": "Extinta a obrigação principal, não mais se justifica a subsistência dos juros remuneratórios", "tipo": "Tema_Complemento"},
    {"entidade": "Recurso Especial repetitivo (REsp nº 1.134.186/RS)", "tipo": "Tema_Recurso"},
]
# ====================== PROMPTS ======================

PROMPT_ZERO_SHOT = """
Você é um especialista em Direito e Processamento de Linguagem Natural. Sua tarefa é identificar entidades jurídicas em textos de acórdãos, mas **somente** entre as seguintes categorias:

(Título, Nome_Recurso, Origem, Recorrido, Recorrente, Nome_Desembargador/Ministro, Resultado_Acórdão, Data, Nome_Relator, Voto, Orgao_Julgador, Tema_Keyword, Tema_Complemento, Tema_Recurso)

Regras importantes:
- Extraia apenas entidades que se encaixem nessas categorias.
- A saída deve ser em formato JSON, lista de objetos com:
  - "entidade": valor encontrado no texto
  - "tipo": uma das categorias listadas acima
- Não invente entidades que não aparecem no texto.

Texto:
{{text}}
"""

PROMPT_ONE_SHOT = """
Você é um especialista em Direito e Processamento de Linguagem Natural. Sua tarefa é identificar entidades jurídicas em textos de acórdãos, apenas das seguintes categorias:

(Título, Nome_Recurso, Origem, Recorrido, Recorrente, Nome_Desembargador/Ministro, Resultado_Acórdão, Data, Nome_Relator, Voto, Orgao_Julgador, Tema_Keyword, Tema_Complemento, Tema_Recurso)

### Exemplo:
Texto:
"ACÓRDÃO. Agravo de Instrumento nº 2116753-11.2020.8.26.0000, Comarca de São Paulo. Apelante: João da Silva. Apelado: Banco do Brasil S/A. Relator: Cézar Zalaf. Julgado em 7 de julho de 2023. VOTO Nº 5219. A 17ª Câmara de Direito Privado decidiu: Deram provimento ao recurso. Tema relacionado: EXPURGOS INFLACIONÁRIOS - JUROS REMUNERATÓRIOS. Complemento: Extinta a obrigação principal, não mais se justifica a subsistência dos juros remuneratórios. Recurso Especial repetitivo (REsp nº 1.134.186/RS)."

Saída:
[
  {{"entidade": "ACÓRDÃO", "tipo": "Título"}},
  {{"entidade": "Agravo de Instrumento nº 2116753-11.2020.8.26.0000", "tipo": "Nome_Recurso"}},
  {{"entidade": "Comarca de São Paulo", "tipo": "Origem"}},
  {{"entidade": "João da Silva", "tipo": "Recorrente"}},
  {{"entidade": "Banco do Brasil S/A", "tipo": "Recorrido"}},
  {{"entidade": "Cézar Zalaf", "tipo": "Nome_Relator"}},
  {{"entidade": "7 de julho de 2023", "tipo": "Data"}},
  {{"entidade": "VOTO Nº 5219", "tipo": "Voto"}},
  {{"entidade": "17ª Câmara de Direito Privado", "tipo": "Orgao_Julgador"}},
  {{"entidade": "Deram provimento ao recurso", "tipo": "Resultado_Acórdão"}},
  {{"entidade": "EXPURGOS INFLACIONÁRIOS - JUROS REMUNERATÓRIOS", "tipo": "Tema_Keyword"}},
  {{"entidade": "Extinta a obrigação principal, não mais se justifica a subsistência dos juros remuneratórios", "tipo": "Tema_Complemento"}},
  {{"entidade": "Recurso Especial repetitivo (REsp nº 1.134.186/RS)", "tipo": "Tema_Recurso"}}
]

Agora extraia as entidades do texto abaixo no mesmo formato JSON.

Contexto:
{{contexto}}

Texto:
{{text}}
"""

PROMPT_FEW_SHOT = """
Você é um especialista em Direito e Processamento de Linguagem Natural. Sua tarefa é identificar entidades jurídicas em textos de acórdãos, **somente** entre as seguintes categorias:

(Título, Nome_Recurso, Origem, Recorrido, Recorrente, Nome_Desembargador/Ministro, Resultado_Acórdão, Data, Nome_Relator, Voto, Orgao_Julgador, Tema_Keyword, Tema_Complemento, Tema_Recurso)

### Exemplo 1:
Texto:
"ACÓRDÃO. Apelação nº 1001234-55.2021.8.26.0100, Comarca de Guarulhos. Apelante: Maria Oliveira. Apelado: Itaú Unibanco S/A. Relator: José Pereira. Julgado em 15 de agosto de 2022. VOTO Nº 33. A 5ª Câmara de Direito Privado decidiu: Negaram provimento ao recurso. Tema relacionado: AÇÃO REVISIONAL - JUROS ABUSIVOS. Complemento: Juros limitados à taxa média de mercado. Recurso Especial repetitivo (REsp nº 1.061.530/RS)."

Saída:
[
  {{"entidade": "ACÓRDÃO", "tipo": "Título"}},
  {{"entidade": "Apelação nº 1001234-55.2021.8.26.0100", "tipo": "Nome_Recurso"}},
  {{"entidade": "Comarca de Guarulhos", "tipo": "Origem"}},
  {{"entidade": "Maria Oliveira", "tipo": "Recorrente"}},
  {{"entidade": "Itaú Unibanco S/A", "tipo": "Recorrido"}},
  {{"entidade": "José Pereira", "tipo": "Nome_Relator"}},
  {{"entidade": "15 de agosto de 2022", "tipo": "Data"}},
  {{"entidade": "VOTO Nº 33", "tipo": "Voto"}},
  {{"entidade": "5ª Câmara de Direito Privado", "tipo": "Orgao_Julgador"}},
  {{"entidade": "Negaram provimento ao recurso", "tipo": "Resultado_Acórdão"}},
  {{"entidade": "AÇÃO REVISIONAL - JUROS ABUSIVOS", "tipo": "Tema_Keyword"}},
  {{"entidade": "Juros limitados à taxa média de mercado", "tipo": "Tema_Complemento"}},
  {{"entidade": "Recurso Especial repetitivo (REsp nº 1.061.530/RS)", "tipo": "Tema_Recurso"}}
]

### Exemplo 2:
Texto:
"ACÓRDÃO. Agravo Interno nº 2004321-88.2020.8.26.0000, Comarca de Campinas. Agravante: João Souza. Agravado: Fazenda Pública do Estado de São Paulo. Relator: Ana Maria Lopes. Julgado em 10 de setembro de 2021. VOTO Nº 87. A 12ª Câmara de Direito Público decidiu: Deram provimento ao recurso. Tema relacionado: RESPONSABILIDADE CIVIL DO ESTADO - DANOS MORAIS. Complemento: Indenização fixada em 50 salários mínimos. Recurso Especial repetitivo (REsp nº 1.251.993/PR)."

Saída:
[
  {{"entidade": "ACÓRDÃO", "tipo": "Título"}},
  {{"entidade": "Agravo Interno nº 2004321-88.2020.8.26.0000", "tipo": "Nome_Recurso"}},
  {{"entidade": "Comarca de Campinas", "tipo": "Origem"}},
  {{"entidade": "João Souza", "tipo": "Recorrente"}},
  {{"entidade": "Fazenda Pública do Estado de São Paulo", "tipo": "Recorrido"}},
  {{"entidade": "Ana Maria Lopes", "tipo": "Nome_Relator"}},
  {{"entidade": "10 de setembro de 2021", "tipo": "Data"}},
  {{"entidade": "VOTO Nº 87", "tipo": "Voto"}},
  {{"entidade": "12ª Câmara de Direito Público", "tipo": "Orgao_Julgador"}},
  {{"entidade": "Deram provimento ao recurso", "tipo": "Resultado_Acórdão"}},
  {{"entidade": "RESPONSABILIDADE CIVIL DO ESTADO - DANOS MORAIS", "tipo": "Tema_Keyword"}},
  {{"entidade": "Indenização fixada em 50 salários mínimos", "tipo": "Tema_Complemento"}},
  {{"entidade": "Recurso Especial repetitivo (REsp nº 1.251.993/PR)", "tipo": "Tema_Recurso"}}
]

Agora extraia TODAS as entidades jurídicas do texto abaixo no mesmo formato JSON.

Contexto:
{{ASSIM, O SOBRESTAMENTO
DETERMINADO PELO PRETÓRIO EXCELSO NÃO
ALCANÇA AS DEMANDAS QUE SE ENCONTRAM NA
FASE DE EXECUÇÃO, EM ATENÇÃO AO PRINCÍPIO
CONSTITUCIONAL DA COISA JULGADA, TAL COMO
OCORRE NO CASO.

NO QUE DIZ RESPEITO À PRESCRIÇÃO
DAS EXECUÇÕES, PRECEITUA A SÚMULA Nº 150 DO
SUPREMO TRIBUNAL FEDERAL:

“PRESCREVE A EXECUÇÃO NO MESMO PRAZO DE
PRESCRIÇÃO DA AÇÃO”.

CONSOANTE INFORMATIVO Nº 0484
DO SUPERIOR TRIBUNAL DE JUSTIÇA:

“QUANDO SE TRATAR DE EXECUÇÃO INDIVIDUAL
DE SENTENÇA PROFERIDA EM AÇÃO COLETIVA, COMO NO CASO, O
BENEFICIÁRIO SE INSERE EM MICROSSISIEMA DIVERSO E COM
REGRAS PERTINENTES, SENDO NECESSÁRIA A OBSERVÂNCIA DO
PRAZO PRÓPRIO DAS AÇÕES COLETIVAS, QUE É QUINQUENAL,
CONFORME JÁ FIRMADO NO RECURSO ESPECIAL Nº 1.070.896.
SC, DJ 4/8/2010, APLICANDOSE A SÚMULA Nº 150SIF. O
BENEFICIÁRIO DE AÇÃO COLETIVA TERIA CINCO ANOS PARA O
AJUIZAMENTO DA EXECUÇÃO INDIVIDUAL, CONTADOS A PARTIR DO
TRÂNSITO EM JULGADO DE SENTENÇA COLETIVA , E O PRAZO DE
20 ANOS PARA O AJUIZAMENTO DE AÇÃO DE CONHECIMENTO
INDIVIDUAL, CONTADOS DOS RESPECTIVOS PAGAMENTOS A
MENOR DAS CORREÇÕES MONETÁRIAS EM RAZÃO DOS PLANOS
ECONÔMICOS”. (GRIFAMOS)

REFERIDO ENTENDIMENTO RESTOU

8 STF. EMBARGOS DE DECLARAÇÃO NO RECURSO EXTRAORDINÁRIO Nº 626.307. MN. REL DIAS
TOFFOLI. J.11.03.2011.

Agravo Interno Cível nº 2116753-11.2020.8.26.0000/50000 -Voto nº 16
| Pe PODER JUDICIÁRIO
mm TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO

SEDIMENTADO PELA SUPRACITADA CORTE COM O
JULGAMENTO | DO RECURSO ESPECIAL Nº
1.273.643/PR, EM SEDE DE RECURSO
REPETITIVO, CONSOANTE SE DEPREENDE DA
SEGUINTE EMENTA:

“DIREITO PROCESSUAL CIVIL. AÇÃO CIVIL
PÚBLICA PRESCRIÇÃO  QUINQUENAL DA EXECUÇÃO
INDIVIDUAL. PRESCRIÇÃO  VINTENÁRIA DO PROCESSO
DE CONHECIMENTO TRANSITADA EM JULGADO.
INAPLICABILIDADE: AO PROCESSO DE EXECUÇÃO.
RECURSO ESPECIAL REPETITIVO. ART. 548C DO CÓDIGO
DE PROCESSO  CIVI. PROVIMENTO DO RECURSO
ESPECIAL REPRESENTATIVO DE CONTROVÉRSIA TESE
CONSOLIDADA.

1.- PARA OS EFEITOS DO ART. 543€C DO CÓDIGO
DE PROCESSO CIVIL, FOI FIXADA A SEGUINTE TESE: 'NO ÂMBITO
DO DIREITO PRIVADO, É DE CINCO ANOS O PRAZO
PRESCRICIONAL PARA AJUIZAMENTO DA EXECUÇÃO INDIVIDUAL
EM PEDIDO DE CUMPRIMENTO DE SENIENÇA PROFERIDA EM AÇÃO

CIVLPÚBLICA! ”.º (GRIFAMOS)

A DESPEITO DE A R. SENTENÇA
PROFERIDA NA DEMANDA COLETIVA TER
TRANSITADO EM JULGADO AOS 27 DE OUTUBRO DE
2009, É CERTO QUE O PRAZO PRESCRICIONAL
RESTOU INTERROMPIDO AOS 26 DE SETEMBRO DE
2014, ATRAVÉS DO AJUIZAMENTO DA AÇÃO DE
PROTESTO Nº 2014.01.1.148561-3, PELO
MINISTÉRIO PúBLICO DO DISTRITO FEDERAL E
TERRITÓRIOS.

COMO SE SABE, COMPETE AO
MINISTÉRIO PÚBLICO A PROTEÇÃO DOS
INTERESSES INDIVIDUAIS INDISPONÍVEIS, DIFUSOS E
COLETIVOS, NOS PRECISOS MOLDES DA ALÍNEA
“Cc”, DO INCISO YVlIl, DO ARTIGO 6º DA LEI

º STJ. REsp. Nº 1.273.643/PR. 22 SEÇÃO. MIN. REL SIDNEI BENET. JJ. 27.02.2018.
Agravo Interno Cível nº 2116753-11.2020.8.26.0000/50000 -Voto nº 17

| Pe PODER JUDICIÁRIO
mm TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO

COMPLEMENTAR Nº 75/1998.

ADEMAIS, O ARTIGO 82 DO CÓDIGO DE
DEFESA DO CONSUMIDOR CONSIDERA O
MINISTÉRIO PÚBLICO LEGITIMADO CONCORRENTE
PARA A DEFESA COLETIVA DOS INTERESSES E
DIREITOS DOS CONSUMIDORES, SENDO QUE O
SUBSEQUENTE ARTIGO 83 ESTABELECE:

“ART. 83. PARA A DEFESA DOS DIRENOS E
INTERESSES PROTEGIDOS POR ESTE CÓDIGO SÃO ADMISSÍVEIS
TODAS AS ESPÉCIES DE AÇÕES CAPAZES DE PROPICIAR SUA

ADEQUADA E EFETIVA TUTELA ”. (GRIFAMOS)

DESSA FORMA, O PARQUET POSSUI
LEGITIMIDADE PARA O AJUIZAMENTO DA MEDIDA
CAUTELAR DE PROTESTO INTERRUPTIVO DO PRAZO
PRESCRICIONAL, QUE, ALIÁS, VISA A GARANTIA DOS
DIREITOS DOS DIVERSOS POUPADORES LESADOS
PELA CONDUTA DO BANCO DO BRASIL S/A }}

Texto:
{{text}}
"""
