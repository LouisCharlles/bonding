AVISO: este é um MODELO/RASCUNHO de Projeto (Protocolo) de Pesquisa, preparado para apoiar a submissão à Plataforma Brasil / Comitê de Ética em Pesquisa (CEP). Os campos entre colchetes `[...]` são placeholders a preencher — em especial o referencial teórico, as referências bibliográficas e o cronograma, que dependem de decisões que só você e seu(sua) orientador(a) podem tomar. Este documento não substitui a orientação do seu curso quanto ao formato/modelo específico exigido pela instituição ou pelo CEP.

---

# PROJETO DE PESQUISA

## Bonding — desenvolvimento e avaliação piloto de um aplicativo de relacionamento

*(título sujeito a ajuste conforme definido com o orientador)*

---

## 1. IDENTIFICAÇÃO

- **Pesquisador responsável:** Luis Carlos Macêdo Moreira
- **Orientador(a):** [ORIENTADOR A DEFINIR]
- **Instituição de ensino:** Centro Universitário UNDB (UNDB)
- **Curso:** [CURSO A DEFINIR]
- **Natureza do trabalho:** Trabalho de Conclusão de Curso (TCC)
- **Área do conhecimento:** Ciência da Computação / Engenharia de Software *(ajustar conforme o curso)*

## 2. RESUMO

Este projeto tem como objetivo o desenvolvimento e a avaliação piloto de um aplicativo de relacionamento ("Bonding"), com funcionalidades de criação de perfil, descoberta e curtidas, formação de conexões mútuas ("matches"), troca de mensagens, verificação de identidade por reconhecimento facial, sugestão de locais de encontro por geolocalização, e um sistema de assinaturas premium (simulado, sem cobrança real, nesta fase de piloto). A avaliação será conduzida com um grupo de até 20 (vinte) participantes voluntários, maiores de 18 anos, que utilizarão o aplicativo por um período determinado, gerando dados de uso que serão analisados para fins do Trabalho de Conclusão de Curso.

## 3. INTRODUÇÃO E JUSTIFICATIVA

[A preencher pelo pesquisador/orientador: contextualizar o problema de pesquisa — por exemplo, o cenário de aplicativos de relacionamento, lacunas identificadas na literatura ou no mercado, motivação técnica/acadêmica para o desenvolvimento do Bonding, e a relevância de uma avaliação piloto com usuários reais para validar as funcionalidades desenvolvidas.]

A justificativa para o uso de participantes reais (em vez de apenas dados simulados) se apoia na necessidade de avaliar, em condições próximas às de uso real, aspectos como usabilidade, funcionamento das funcionalidades de descoberta e correspondência ("matching"), verificação de identidade, e a percepção dos usuários quanto à experiência oferecida — aspectos que dificilmente seriam capturados de forma representativa apenas com dados sintéticos/mock.

## 4. REFERENCIAL TEÓRICO

[A preencher: revisão da literatura sobre aplicativos de relacionamento, arquiteturas de software relevantes (ex.: aplicações web/mobile em tempo real, uso de inteligência artificial para reconhecimento facial e processamento de linguagem natural), trabalhos correlatos, e fundamentação sobre os aspectos éticos e legais de pesquisa envolvendo dados pessoais sensíveis (LGPD, Resoluções CNS 466/2012 e 510/2016).]

## 5. OBJETIVOS

### 5.1. Objetivo geral

Desenvolver e avaliar, em caráter piloto, um protótipo funcional de aplicativo de relacionamento, examinando seu funcionamento e a experiência de uso a partir da interação de participantes reais com suas principais funcionalidades.

### 5.2. Objetivos específicos

- Descrever a arquitetura técnica e as funcionalidades implementadas no aplicativo Bonding;
- Implementar um mecanismo de consentimento informado, específico para dados sensíveis, com registro auditável e íntegro das manifestações de consentimento dos participantes;
- Conduzir um piloto de uso com até 20 participantes voluntários por um período determinado;
- Coletar e analisar métricas de uso do aplicativo (ex.: interações, matches, uso de funcionalidades) geradas durante o piloto;
- [A preencher: demais objetivos específicos relevantes ao recorte do seu TCC — por exemplo, avaliar usabilidade, avaliar desempenho técnico, avaliar a eficácia da verificação de identidade, etc.]

## 6. METODOLOGIA

### 6.1. Tipo de estudo

Pesquisa aplicada, de natureza exploratória, com abordagem [QUALITATIVA / QUANTITATIVA / MISTA — A DEFINIR], envolvendo o desenvolvimento de um artefato de software (o aplicativo Bonding) e sua avaliação por meio de um estudo piloto com usuários reais.

### 6.2. População e amostra

A amostra será composta por até **20 (vinte) participantes voluntários**, recrutados por conveniência entre pessoas maiores de 18 anos de idade [A preencher: critério de recrutamento — por exemplo, colegas de curso, conhecidos do pesquisador, convite público na instituição, etc.].

### 6.3. Critérios de inclusão

- Pessoas com 18 (dezoito) anos de idade ou mais;
- Concordância livre e esclarecida em participar, mediante assinatura/aceite do Termo de Consentimento Livre e Esclarecido (TCLE);
- Possuir dispositivo (computador ou smartphone) com acesso à internet e navegador compatível.

### 6.4. Critérios de exclusão

- Pessoas menores de 18 anos;
- Pessoas que não concordarem com os termos do TCLE;
- Participantes que manifestarem, a qualquer momento, o desejo de se retirar da pesquisa (a partir desse momento, excluídos da análise).

### 6.5. Procedimentos da pesquisa

Após a assinatura do TCLE, cada participante:

1. Criará uma conta no aplicativo Bonding (nome, idade, e-mail e senha);
2. Preencherá um perfil de usuário (biografia, fotos, gênero, orientação sexual, interesses), mediante consentimento específico e destacado para o tratamento desses dados sensíveis;
3. Poderá, de forma opcional e mediante consentimento específico, realizar a verificação de identidade por meio de selfie, comparada automaticamente às fotos do perfil (reconhecimento facial via Amazon Web Services — Rekognition);
4. Utilizará as funcionalidades de descoberta de outros perfis, curtidas, formação de matches e troca de mensagens com os demais participantes do piloto;
5. Poderá, de forma opcional, testar a ativação de um plano premium, simulada nesta instância (sem cobrança financeira real);
6. Poderá, a qualquer momento, encerrar sua participação, desativando ou excluindo sua conta diretamente pelo aplicativo.

O período de uso será de [PERÍODO A DEFINIR — ex.: 2 a 4 semanas], acompanhado pelo pesquisador responsável.

### 6.6. Instrumentos e técnicas de coleta de dados

- **Dados de uso do próprio aplicativo**: registros de interações (curtidas, matches, mensagens trocadas, uso de funcionalidades), coletados automaticamente pela plataforma durante o período do piloto;
- **Registro de consentimento**: cada manifestação de consentimento (TCLE, Termos de Uso, Política de Privacidade, e consentimentos específicos para dados sensíveis) fica registrada de forma auditável, com data, hora, IP e um mecanismo de verificação criptográfica de integridade (cadeia de hashes assinada), garantindo que os registros não possam ser alterados após sua criação;
- [A preencher, se aplicável: instrumentos adicionais, como questionário de satisfação/usabilidade pós-uso, entrevista, formulário de feedback, etc.]

### 6.7. Plano de análise dos dados

Os dados coletados serão organizados e analisados de forma agregada, sem identificação individual dos participantes nos resultados apresentados. [A preencher: técnicas de análise a serem empregadas — por exemplo, estatística descritiva das métricas de uso, análise de conteúdo, etc.] Também serão utilizadas métricas simuladas (mock), claramente identificadas como tal no relatório final, para ilustrar cenários de uso em maior escala que não seriam representativos com uma amostra de apenas 20 participantes.

## 7. RISCOS E BENEFÍCIOS

### 7.1. Riscos

A participação envolve o compartilhamento de dados pessoais e, em alguns casos, dados pessoais sensíveis (gênero, orientação sexual, imagem biométrica facial, localização geográfica precisa quando solicitada). Como o grupo de participantes é pequeno e conhecido entre si (até 20 pessoas), existe risco de reidentificação mesmo após anonimização no relatório final. Há também riscos técnicos inerentes a um protótipo acadêmico (instabilidades, eventuais falhas) e o desconforto eventual de interagir com outras pessoas em um contexto de relacionamento.

### 7.2. Medidas de minimização de riscos

- Coleta de consentimento específico e destacado para cada categoria de dado sensível, antes de sua coleta;
- Codificação/pseudonimização dos participantes na análise e na apresentação dos resultados;
- Restrição de acesso aos dados brutos ao pesquisador responsável (e orientador(a), quando aplicável), conforme o Termo de Confidencialidade firmado;
- Armazenamento seguro dos dados, com criptografia de campos sensíveis em repouso, comunicação criptografada (HTTPS/TLS), e controle de acesso por autenticação;
- Direito assegurado de recusa a qualquer etapa e de retirada da pesquisa a qualquer momento, sem qualquer prejuízo;
- Possibilidade de desativação (congelamento) ou exclusão da conta a qualquer momento, diretamente pelo aplicativo.

### 7.3. Benefícios

Não há benefício financeiro direto aos participantes. Os benefícios são indiretos: contribuição para uma pesquisa acadêmica e acesso experimental a um protótipo funcional de aplicativo de relacionamento durante o período do piloto.

## 8. ASPECTOS ÉTICOS

### 8.1. Processo de consentimento

Todos os participantes assinarão/aceitarão eletronicamente o Termo de Consentimento Livre e Esclarecido (TCLE), previamente à sua participação, sendo informados sobre os objetivos, procedimentos, riscos e benefícios da pesquisa, e sobre seu direito de recusa e retirada a qualquer momento, sem qualquer prejuízo.

### 8.2. Confidencialidade e proteção de dados

O tratamento dos dados pessoais observará a Lei Geral de Proteção de Dados (Lei nº 13.709/2018 — LGPD). Ainda que se trate de pesquisa de finalidade exclusivamente acadêmica (art. 4º, IV, "b" da LGPD), os arts. 7º e 11º da Lei continuam integralmente aplicáveis, de modo que o consentimento específico e destacado é a base legal adotada para o tratamento de dados sensíveis. O pesquisador responsável e o(a) orientador(a) firmam Termo de Confidencialidade específico, comprometendo-se a não divulgar a identidade dos participantes e a utilizar os dados exclusivamente para os fins desta pesquisa.

### 8.3. Dados sensíveis

Os dados sensíveis tratados nesta pesquisa (orientação sexual, gênero, biometria facial) são coletados apenas mediante consentimento específico, destacado do consentimento geral, e podem ser revogados a qualquer momento pelo participante, com efeitos sobre as funcionalidades que deles dependam.

### 8.4. Direito de desistência

A participação é voluntária e o participante pode se retirar da pesquisa a qualquer momento, sem necessidade de justificativa e sem qualquer prejuízo, bastando informar o pesquisador responsável ou excluir sua conta diretamente pelo aplicativo.

## 9. GERENCIAMENTO, ARMAZENAMENTO E DESCARTE DE DADOS

### 9.1. Infraestrutura técnica

O aplicativo é hospedado em ambiente de nuvem (Render, para os serviços de aplicação e processamento; Supabase, para banco de dados e armazenamento de arquivos), com comunicação criptografada (HTTPS/TLS) entre o aplicativo e os servidores.

### 9.2. Segurança da informação

São adotadas as seguintes medidas técnicas: criptografia de campos sensíveis em repouso; controle de acesso baseado em autenticação; e um mecanismo de log de consentimento imutável (cadeia de hashes assinada criptograficamente, com verificação de integridade), que impede a alteração ou exclusão dos registros de consentimento após sua criação.

### 9.3. Retenção e descarte

Os dados coletados serão mantidos pelo período do piloto e da elaboração/defesa do TCC. Após a conclusão e defesa do trabalho, os dados pessoais identificáveis (fotos, selfies, mensagens, dados de perfil) serão anonimizados ou excluídos, ressalvados os registros mínimos exigidos por normas acadêmicas/éticas aplicáveis. Os registros de consentimento são preservados de forma permanente, por constituírem prova do cumprimento das obrigações éticas e legais da pesquisa.

## 10. CRONOGRAMA

| Etapa | Período *(a definir)* |
|---|---|
| Submissão do projeto ao CEP | [DATA] |
| Aprovação do CEP | [DATA] |
| Recrutamento dos participantes | [DATA] |
| Coleta de dados (uso piloto do aplicativo) | [DATA] |
| Análise dos dados | [DATA] |
| Redação do TCC | [DATA] |
| Defesa do TCC | [DATA] |

## 11. ORÇAMENTO

Este projeto não prevê custos financeiros para os participantes. Os custos de infraestrutura (hospedagem, serviços de terceiros) são de responsabilidade do pesquisador responsável. [A preencher, se exigido pelo modelo da instituição: estimativa de custos de hospedagem/serviços de terceiros, ainda que simbólica.]

## 12. RESULTADOS ESPERADOS

Espera-se, ao final deste estudo, apresentar um relatório de TCC descrevendo o desenvolvimento técnico do aplicativo Bonding e os resultados da avaliação piloto conduzida com os participantes, incluindo métricas de uso reais (do piloto) e simuladas (mock, para ilustrar cenários de maior escala), de forma agregada e anonimizada, contribuindo para o campo de [A preencher, conforme o recorte do TCC].

## 13. REFERÊNCIAS

[A preencher pelo pesquisador/orientador, conforme as normas de citação adotadas pela instituição — inclua a legislação de referência: BRASIL. Lei nº 13.709, de 14 de agosto de 2018 (Lei Geral de Proteção de Dados Pessoais); Conselho Nacional de Saúde. Resolução CNS nº 466/2012; Resolução CNS nº 510/2016.]
