"""Publica o TCLE (v1.0) e revisa Termos de Uso / Politica de Privacidade
para v1.1, refletindo que esta instancia do Bonding e uma DEMONSTRACAO
ACADEMICA (TCC) com um piloto de participantes reais, com pagamento
simulado (sem cobranca real via AbacatePay).

IMPORTANTE: o TCLE abaixo e um MODELO preparado para viabilizar a
implementacao tecnica do fluxo de consentimento de pesquisa. Ele AINDA
PRECISA ser submetido e aprovado por um Comite de Etica em Pesquisa (CEP)
via Plataforma Brasil antes de ser usado com participantes reais — os
campos [ORIENTADOR A DEFINIR], [CAAE A DEFINIR] e [CONTATO DO CEP A DEFINIR]
sao placeholders que devem ser preenchidos assim que essas informacoes
existirem.

Como em 0020_seed_legal_documents.py, o conteudo fica literal neste arquivo
de proposito (retrato congelado da v1.1/v1.0) — mudancas futuras devem
publicar uma NOVA versao via bonding.services.legal.publish_document_version(),
nunca editar este arquivo depois de aplicado."""

import hashlib

from django.db import migrations

TCLE_CONTENT = """TERMO DE CONSENTIMENTO LIVRE E ESCLARECIDO (TCLE)

AVISO: este e um MODELO de TCLE preparado para viabilizar a implementacao
tecnica do fluxo de consentimento de pesquisa do aplicativo Bonding. Ele
ainda precisa ser submetido e aprovado por um Comite de Etica em Pesquisa
(CEP), via Plataforma Brasil, antes de ser utilizado com participantes reais.

Versao 1.0 — vigente a partir da data de publicacao indicada no aplicativo.

Titulo do estudo: Bonding — desenvolvimento e avaliacao piloto de um
aplicativo de relacionamento (titulo sujeito a ajuste conforme definido
com o orientador).

Pesquisador responsavel: Luis Carlos Macedo Moreira
Orientador(a): [ORIENTADOR A DEFINIR]
Instituicao de ensino: Centro Universitario UNDB (UNDB)
Comite de Etica em Pesquisa (CEP) responsavel: [CONTATO DO CEP A DEFINIR]
Numero do CAAE: [CAAE A DEFINIR]

1. CONVITE E APRESENTACAO

Voce esta sendo convidado(a) a participar, como voluntario(a), de uma
pesquisa de Trabalho de Conclusao de Curso (TCC) desenvolvida por Luis
Carlos Macedo Moreira, sob orientacao a ser definida, no Centro
Universitario UNDB. Antes de decidir se deseja participar, leia com
atencao as informacoes abaixo.

2. OBJETIVO DA PESQUISA

O estudo tem como objetivo desenvolver e avaliar, em carater piloto, um
aplicativo de relacionamento ("Bonding"), incluindo funcionalidades de
criacao de perfil, descoberta e curtidas, troca de mensagens, verificacao
de identidade por reconhecimento facial, sugestao de locais de encontro
por geolocalizacao, e assinatura de planos premium (neste piloto, de forma
simulada, sem cobranca real).

3. JUSTIFICATIVA

A pesquisa se justifica pela necessidade de avaliar, com um grupo reduzido
e controlado de usuarios reais (ate 20 participantes), o funcionamento e a
usabilidade do prototipo desenvolvido, gerando dados e metricas que serao
utilizados na elaboracao do TCC.

4. PROCEDIMENTOS

Caso concorde em participar, voce sera convidado(a) a: criar uma conta no
aplicativo (nome, idade, e-mail e senha); preencher um perfil (biografia,
fotos, genero, orientacao sexual, interesses); opcionalmente, realizar a
verificacao de identidade por selfie (comparacao facial automatizada);
utilizar as funcionalidades de descoberta, curtidas, matches e mensagens
com outros participantes do piloto; e, opcionalmente, testar a ativacao de
um plano premium (simulada, sem cobranca real, neste piloto). O periodo de
uso e as tarefas especificas serao combinados previamente com o
pesquisador responsavel.

5. RISCOS E DESCONFORTOS

A participacao envolve o compartilhamento de dados pessoais e, em alguns
casos, dados pessoais sensiveis (genero, orientacao sexual, imagem
biometrica facial para verificacao de identidade, localizacao geografica
precisa quando solicitada). Como o grupo de participantes e pequeno e
conhecido entre si (ate 20 pessoas), existe risco de reidentificacao
mesmo apos anonimizacao no relatorio final do TCC — esse risco sera
mitigado por meio de codificacao (pseudonimos/codigos) dos participantes
nos dados analisados e apresentados. Ha tambem riscos tecnicos inerentes a
um prototipo academico (instabilidades, bugs), e o desconforto psicologico
eventual de interagir com outras pessoas em um contexto de relacionamento.
Voce podera se recusar a responder qualquer pergunta ou realizar qualquer
etapa que lhe cause desconforto, sem qualquer prejuizo.

6. BENEFICIOS

Nao ha beneficio financeiro direto. Os beneficios sao indiretos: contribuir
para uma pesquisa academica, e o acesso experimental a um prototipo
funcional de aplicativo de relacionamento durante o periodo do piloto.

7. USO DE SERVICOS DE TERCEIROS / INTELIGENCIA ARTIFICIAL

Para o funcionamento das funcionalidades descritas, dados sao processados
por servicos de terceiros: sua selfie e fotos de perfil podem ser enviadas
a Amazon Web Services (Rekognition) para comparacao facial automatizada, na
verificacao de identidade; o texto de suas conversas pode ser processado
pela API do Google (Gemini) para classificacao automatizada de estagio de
conversa, funcionalidade que pode ser desativada nas configuracoes; e
coordenadas geograficas podem ser enviadas ao Google Maps e/ou
OpenStreetMap para sugestao de locais de encontro, apenas quando voce
solicitar essa funcionalidade e consentir especificamente com o uso de
geolocalizacao precisa.

8. SIGILO E CONFIDENCIALIDADE

Suas respostas e dados de uso serao tratados com confidencialidade. No
relatorio final do TCC, os resultados serao apresentados de forma
agregada e/ou codificada (sem uso do seu nome real ou de identificadores
diretos), exceto quando a divulgacao de informacoes especificas for
previamente autorizada por voce por escrito.

9. ARMAZENAMENTO E DESCARTE DOS DADOS

Os dados coletados durante o piloto ficarao armazenados de forma segura
(banco de dados com controle de acesso e, para o registro de consentimento,
um mecanismo de log imutavel com verificacao criptografica de integridade)
durante o periodo do piloto e da elaboracao/defesa do TCC. Apos a conclusao
e defesa do trabalho, os dados pessoais identificaveis (fotos, selfies,
mensagens, dados de perfil) serao anonimizados ou excluidos, salvo os
registros minimos exigidos para fins de comprovacao academica/etica, que
poderao ser retidos pelo prazo exigido pelas normas da instituicao/CEP.

10. PARTICIPACAO VOLUNTARIA E DIREITO DE RETIRADA

Sua participacao e totalmente voluntaria. Voce podera se recusar a
participar ou desistir a qualquer momento, sem necessidade de justificativa
e sem qualquer prejuizo, penalidade ou constrangimento, bastando informar o
pesquisador responsavel ou excluir sua conta diretamente pelo aplicativo
(Configuracoes > Privacidade e conta).

11. RESSARCIMENTO E INDENIZACAO

Nao estao previstos gastos pessoais para voce em decorrenca da
participacao nesta pesquisa. Caso, excepcionalmente, algum dano
comprovadamente decorrente da pesquisa venha a ocorrer, voce tem direito a
indenizacao, conforme legislacao vigente.

12. CONTATO

Em caso de duvidas sobre a pesquisa, voce pode contatar o pesquisador
responsavel, Luis Carlos Macedo Moreira, pelos canais informados no
aplicativo. Em caso de duvidas sobre seus direitos como participante da
pesquisa, ou para relatar alguma situacao ocorrida durante o estudo, voce
pode contatar o Comite de Etica em Pesquisa (CEP) responsavel:
[CONTATO DO CEP A DEFINIR].

13. CONSENTIMENTO

Declaro que li e/ou ouvi as explicacoes contidas neste termo, que fui
informado(a) dos objetivos, procedimentos, riscos e beneficios da
pesquisa, que tive a oportunidade de esclarecer minhas duvidas, e que
concordo, de forma livre e esclarecida, em participar voluntariamente
deste estudo, podendo retirar meu consentimento a qualquer momento sem
qualquer prejuizo. Este aceite fica registrado eletronicamente, com data,
hora e demais metadados, em log de consentimento com verificacao de
integridade, e uma via deste termo permanece disponivel a qualquer momento
dentro do proprio aplicativo."""

TERMS_OF_USE_V1_1_CONTENT = """TERMOS DE USO — BONDING

AVISO: este documento e um rascunho preparado para fins de implementacao
tecnica do aplicativo Bonding e ainda nao foi revisado por advogado. Nao deve
ser publicado em producao comercial sem revisao juridica formal, preenchimento
dos dados societarios reais e adequacao ao modelo de negocio final.

AVISO — VERSAO DE DEMONSTRACAO ACADEMICA: esta instancia do Bonding e um
prototipo operado exclusivamente para fins de pesquisa academica (Trabalho de
Conclusao de Curso, Centro Universitario UNDB), com um numero limitado de
participantes voluntarios. Nao ha relacao de consumo real: os planos
"premium" mencionados abaixo sao ativados de forma SIMULADA, sem qualquer
cobranca financeira efetiva. As condicoes descritas neste documento refletem
o funcionamento do aplicativo como se fosse um produto comercial, para fins
de demonstracao e avaliacao academica.

Versao 1.1 — vigente a partir da data de publicacao indicada no aplicativo.

1. QUEM SOMOS

O Bonding e um aplicativo de relacionamento, nesta instancia operado como
prototipo academico por Luis Carlos Macedo Moreira, no ambito de um TCC do
Centro Universitario UNDB ("Bonding", "nos"). Estes Termos de Uso regulam o
acesso e uso do aplicativo e dos servicos associados (o "Servico") por
qualquer pessoa que crie uma conta ("voce", "usuario").

2. ACEITACAO DOS TERMOS

Ao criar uma conta no Bonding, voce declara que leu, compreendeu e concorda
integralmente com estes Termos de Uso, com a Politica de Privacidade e, por
se tratar de um piloto de pesquisa, com o Termo de Consentimento Livre e
Esclarecido (TCLE), que integram este documento por referencia. Caso nao
concorde com qualquer disposicao, voce nao devera se cadastrar ou utilizar o
Servico.

3. ELEGIBILIDADE

3.1. O Servico e destinado exclusivamente a pessoas com 18 (dezoito) anos ou
mais. Ao se cadastrar, voce declara e garante que possui a idade minima
exigida e plena capacidade civil para celebrar este contrato.

3.2. Voce declara que as informacoes fornecidas no cadastro e no perfil sao
verdadeiras, precisas e atualizadas, e se compromete a mante-las assim.

3.3. Nesta instancia de demonstracao academica, o acesso e restrito aos
participantes convidados para o piloto de pesquisa.

4. CADASTRO E CONTA

4.1. Voce e responsavel por manter a confidencialidade de sua senha e por
todas as atividades realizadas em sua conta.

4.2. Notifique-nos imediatamente sobre qualquer uso nao autorizado de sua
conta.

4.3. O cadastro completo do perfil pode exigir a verificacao de identidade
por reconhecimento facial, conforme detalhado na Politica de Privacidade e no
TCLE, mediante consentimento especifico e destacado, coletado separadamente
antes do envio de qualquer imagem para esse fim.

5. DESCRICAO DO SERVICO

O Bonding permite que usuarios criem um perfil, descubram e curtam outros
perfis, formem conexoes mutuas ("matches"), troquem mensagens de texto,
imagem e video, participem de chamadas de video, publiquem "stories"
temporarios, e acessem funcionalidades adicionais mediante planos de
assinatura premium (simulados, nesta instancia) ou moeda virtual interna
(lacos/ribbons, coracoes/hearts e rewinds), cujas regras de conversao e uso
estao descritas dentro do proprio aplicativo.

6. REGRAS DE CONDUTA

Ao usar o Bonding, voce concorda em NAO:

- Assediar, ameacar, constranger ou praticar discurso de odio contra outros
  usuarios, inclusive com base em raca, etnia, religiao, orientacao sexual,
  identidade de genero, deficiencia ou nacionalidade;
- Publicar conteudo ilegal, pornografia infantil, violencia extrema, ou
  qualquer material que viole direitos de terceiros;
- Se passar por outra pessoa, criar perfis falsos ou fornecer informacoes
  falsas sobre idade, identidade ou intencoes;
- Usar o Servico para fins comerciais nao autorizados, spam, ou coleta nao
  autorizada de dados de outros usuarios (scraping);
- Tentar contornar mecanismos de seguranca, engenharia reversa, ou acessar
  areas restritas do sistema;
- Solicitar ou oferecer valores financeiros, servicos sexuais mediante
  pagamento, ou qualquer atividade ilegal por meio da plataforma.

O descumprimento destas regras pode resultar em advertencia, suspensao ou
encerramento definitivo da conta, sem prejuizo de outras medidas cabiveis.

7. CONTEUDO GERADO PELO USUARIO

7.1. Voce mantem a titularidade sobre fotos, textos e demais conteudos que
publicar, mas concede ao Bonding uma licenca nao exclusiva, mundial e
gratuita para hospedar, exibir e processar esse conteudo estritamente para
operar e disponibilizar o Servico a voce e aos usuarios com quem interage,
incluindo a analise academica prevista no TCLE.

7.2. Voce e o unico responsavel pelo conteudo que publica e declara possuir
todos os direitos necessarios sobre ele.

8. MODERACAO, DENUNCIAS E BLOQUEIO

8.1. O Bonding disponibiliza ferramentas para denunciar ("Report") e
bloquear ("Block") outros usuarios. Denuncias sao analisadas e podem
resultar em medidas contra a conta denunciada.

8.2. Reservamo-nos o direito de remover conteudo ou suspender contas que
violem estes Termos, a nosso criterio razoavel, mediante notificacao quando
possivel.

9. SEGURANCA EM ENCONTROS PESSOAIS

O Bonding e uma plataforma de intermediacao de conexoes e NAO realiza
verificacao de antecedentes criminais dos usuarios, nem garante a veracidade
integral das informacoes fornecidas por terceiros. Encontros pessoais
decorrentes do uso do Servico ocorrem por conta e risco exclusivo dos
usuarios envolvidos. Recomendamos fortemente: informar terceiros de
confianca sobre encontros marcados, escolher locais publicos para primeiros
encontros, e nunca compartilhar dados financeiros com outros usuarios.

10. PLANOS PREMIUM NESTA INSTANCIA DE DEMONSTRACAO (SEM COBRANCA REAL)

10.1. Nesta instancia de demonstracao academica, a ativacao de planos
"premium" e feita de forma SIMULADA: ao solicitar um plano, ele e ativado
imediatamente em sua conta, sem qualquer cobranca financeira real, sem envio
de dados de pagamento a operadoras ou gateways, e sem gerar qualquer
obrigacao financeira para voce.

10.2. Em uma eventual instancia comercial futura do Bonding (fora do escopo
deste piloto academico), a contratacao de planos pagos seria processada por
um parceiro de pagamentos, e se aplicariam as regras usuais de protecao ao
consumidor, incluindo o direito de arrependimento em ate 7 (sete) dias
corridos previsto no art. 49 do Codigo de Defesa do Consumidor. Essas regras
NAO se aplicam a este piloto, por nao haver relacao de consumo real.

10.3. Moedas virtuais internas (lacos, coracoes, rewinds) nao possuem valor
monetario de resgate e nao sao conversiveis em dinheiro, servindo
exclusivamente para uso dentro do Servico.

11. SUSPENSAO E ENCERRAMENTO

11.1. Voce pode encerrar sua conta a qualquer momento pelas configuracoes do
aplicativo, observados os efeitos descritos na Politica de Privacidade e no
TCLE quanto ao tratamento dos dados apos o encerramento.

11.2. Podemos suspender ou encerrar sua conta em caso de violacao destes
Termos, exigencia legal/etica, ou risco a seguranca de outros usuarios.

12. LIMITACAO DE RESPONSABILIDADE

Na maxima extensao permitida pela legislacao aplicavel, o Bonding nao se
responsabiliza por danos indiretos, condutas de terceiros, ou pela precisao
das informacoes fornecidas por outros usuarios, sem prejuizo das
responsabilidades que a lei brasileira atribui de forma inafastavel.

13. ALTERACOES DESTES TERMOS

Podemos atualizar estes Termos periodicamente. Alteracoes materiais serao
comunicadas dentro do aplicativo e exigirao novo aceite explicito antes da
continuidade do uso do Servico, por meio do mecanismo de consentimento
versionado do aplicativo.

14. LEGISLACAO APLICAVEL E FORO

Estes Termos sao regidos pelas leis da Republica Federativa do Brasil. Para
fins academicos, aplicam-se subsidiariamente as normas eticas de pesquisa
com seres humanos (Resolucoes CNS 466/2012 e 510/2016) e as diretrizes do
Comite de Etica em Pesquisa responsavel pelo estudo.

15. CONTATO

Duvidas sobre estes Termos podem ser encaminhadas ao pesquisador responsavel,
Luis Carlos Macedo Moreira, pelos canais informados no aplicativo."""

PRIVACY_POLICY_V1_1_CONTENT = """POLITICA DE PRIVACIDADE — BONDING

AVISO: este documento e um rascunho preparado para fins de implementacao
tecnica do aplicativo Bonding e ainda nao foi revisado por advogado
especializado em protecao de dados. Nao deve ser publicado em producao
comercial sem revisao juridica formal e preenchimento dos dados reais da
empresa e do Encarregado de Dados (DPO).

AVISO — VERSAO DE DEMONSTRACAO ACADEMICA: esta instancia do Bonding e um
prototipo operado exclusivamente para fins de pesquisa academica (TCC,
Centro Universitario UNDB), com um numero limitado de participantes
voluntarios. Consulte tambem o Termo de Consentimento Livre e Esclarecido
(TCLE) disponivel no aplicativo, que trata especificamente do uso dos seus
dados no contexto da pesquisa.

Versao 1.1 — vigente a partir da data de publicacao indicada no aplicativo.

1. INTRODUCAO E RESPONSAVEL PELO TRATAMENTO

Esta Politica de Privacidade descreve como os dados pessoais coletados por
esta instancia academica do Bonding sao tratados. O responsavel pelo
tratamento, nesta fase de piloto de pesquisa, e o pesquisador responsavel,
Luis Carlos Macedo Moreira, sob orientacao a ser definida, vinculado ao
Centro Universitario UNDB.

2. ENCARREGADO DE DADOS / PONTO DE CONTATO

Nesta instancia academica, o ponto de contato para duvidas sobre tratamento
de dados pessoais e o proprio pesquisador responsavel, ate que um Encarregado
de Dados formal seja eventualmente designado (relevante caso o Bonding venha
a se tornar um produto comercial fora do escopo deste TCC).

3. DADOS QUE COLETAMOS

3.1. Dados de cadastro: nome, e-mail, senha (armazenada de forma criptografada
por hash unidirecional), idade.

3.2. Dados de perfil: biografia, ocupacao, formacao/educacao, curso,
intencao de relacionamento, preferencias de descoberta (faixa etaria,
distancia maxima), interesses selecionados, e os seguintes DADOS PESSOAIS
SENSIVEIS nos termos do art. 5o, II da LGPD: genero e orientacao sexual,
fornecidos voluntariamente por voce e tratados com base no consentimento
especifico e destacado exigido pelo art. 11 da LGPD.

3.3. Fotos de perfil e midia (imagens e videos) que voce publica ou envia em
conversas.

3.4. Dados de verificacao de identidade / biometria facial: caso voce opte
por verificar sua identidade, coletamos uma selfie e a comparamos com as
fotos do seu perfil por meio de um provedor de reconhecimento facial (Amazon
Web Services — Rekognition). Trata-se de DADO PESSOAL SENSIVEL (dado
biometrico, art. 5o, II da LGPD), tratado somente mediante consentimento
especifico e destacado, coletado antes do envio de qualquer imagem para essa
finalidade.

3.5. Dados de localizacao: cidade e estado informados no perfil, e — quando
voce solicita sugestoes de locais para encontros e concede o consentimento
especifico correspondente — dados de geolocalizacao precisa (latitude,
longitude e precisao em metros) obtidos do seu dispositivo no momento da
solicitacao.

3.6. Conteudo de mensagens trocadas com outros usuarios (texto, imagens,
videos), incluindo processamento automatizado do conteudo textual por
inteligencia artificial (Google Gemini) para sugerir estagio da conversa e
sugestoes de encontro — funcionalidade que voce pode desativar nas
configuracoes do aplicativo.

3.7. Dados de pagamento — NAO SE APLICAM NESTA INSTANCIA: ao contrario de uma
instancia comercial do Bonding, nesta demonstracao academica a ativacao de
planos premium e SIMULADA. Nenhum CPF, dado de cartao ou dado financeiro real
e coletado, processado ou enviado a qualquer gateway de pagamento. Mantemos
apenas o registro de qual plano foi simulado/ativado em sua conta.

3.8. Dados de dispositivo e tecnicos: endereco IP, identificador do
navegador/dispositivo (user-agent), token de notificacao push, registros de
data e hora de acesso.

3.9. Dados de uso e comportamento: curtidas, matches, bloqueios, denuncias,
saldo e historico de moeda virtual interna, musica selecionada via busca
publica no catalogo do Spotify (nao acessamos sua conta pessoal do Spotify).

4. BASES LEGAIS PARA O TRATAMENTO

Mesmo em pesquisas de finalidade exclusivamente academica, a LGPD determina,
no art. 4o, IV, "b", que os arts. 7o e 11o continuam se aplicando
integralmente. Assim, tratamos seus dados pessoais com fundamento em:

- Consentimento (art. 7o, I): esta e a base legal principal para sua
  participacao neste piloto de pesquisa, formalizada por meio do TCLE e do
  aceite destes Termos e desta Politica;
- Cumprimento de obrigacao legal ou regulatoria (art. 7o, II), quando
  aplicavel a exigencias academicas/eticas de guarda de registros da
  pesquisa.

Para os DADOS PESSOAIS SENSIVEIS descritos nos itens 3.2 (genero/orientacao
sexual) e 3.4 (biometria facial), a base legal exclusiva e o CONSENTIMENTO
ESPECIFICO E DESTACADO (art. 11, I da LGPD), coletado separadamente do
aceite geral destes Termos, podendo ser revogado a qualquer momento — a
revogacao pode limitar ou impedir o uso de funcionalidades que dependam
desses dados (ex.: selo de verificacao).

5. FINALIDADES DO TRATAMENTO

Usamos seus dados para: viabilizar cadastro e autenticacao; exibir seu
perfil a outros participantes do piloto conforme suas configuracoes de
privacidade; processar curtidas e formar matches; entregar e armazenar
mensagens; processar verificacao de identidade quando solicitada; sugerir
locais de encontro proximos quando voce solicitar e consentir; simular a
ativacao de planos premium; enviar notificacoes relevantes; prevenir fraude
e abuso; e gerar as metricas e analises que serao utilizadas no relatorio
do TCC (de forma anonimizada/codificada).

6. COMPARTILHAMENTO DE DADOS COM TERCEIROS

Compartilhamos dados pessoais estritamente na medida necessaria com os
seguintes operadores/parceiros:

- Amazon Web Services (Rekognition): recebe a imagem da selfie e das fotos
  de perfil para realizar a comparacao facial durante a verificacao de
  identidade. Pode envolver processamento em servidores localizados fora do
  Brasil (transferencia internacional de dados, art. 33 da LGPD).
- Google (Maps Platform e Gemini): recebe coordenadas geograficas agregadas
  para sugerir locais de encontro, e conteudo textual de conversas para
  classificacao automatizada de estagio de relacionamento. Pode envolver
  processamento em servidores localizados fora do Brasil.
- OpenStreetMap / Nominatim: recebe coordenadas geograficas para busca de
  pontos de interesse proximos, sem autenticacao ou vinculo direto a sua
  identidade.
- Spotify: recebemos apenas resultados publicos de busca no catalogo de
  musicas; nenhum dado da sua conta pessoal do Spotify e acessado.
- Infraestrutura de hospedagem e banco de dados (Render e Supabase): armazenam
  a aplicacao, o banco de dados e os arquivos de midia.

Nao vendemos dados pessoais a terceiros. Nesta instancia academica, nenhum
dado de pagamento e compartilhado com gateways financeiros (ver item 3.7).

7. RETENCAO DE DADOS

Adotamos o principio da minimizacao (art. 6o, VII da LGPD). Os dados
coletados durante o piloto sao mantidos pelo periodo do estudo e da
elaboracao/defesa do TCC; apos a conclusao, dados pessoais identificaveis
sao anonimizados ou excluidos, conforme detalhado no TCLE, ressalvados
registros minimos exigidos por normas academicas/eticas aplicaveis.

8. SEUS DIREITOS COMO TITULAR DE DADOS

Nos termos do art. 18 da LGPD, voce tem direito a, mediante requisicao:
confirmar a existencia de tratamento de seus dados; acessar seus dados
pessoais; corrigir dados incompletos, inexatos ou desatualizados; solicitar
anonimizacao, bloqueio ou eliminacao de dados desnecessarios ou excessivos;
solicitar a portabilidade dos seus dados; solicitar a eliminacao dos dados
tratados com base no seu consentimento; obter informacoes sobre as entidades
com as quais compartilhamos seus dados; e revogar o consentimento a qualquer
momento, sem prejuizo da legalidade do tratamento realizado antes da
revogacao. Voce pode exercer esses direitos diretamente pelo aplicativo
(Configuracoes > Privacidade e conta, para desativacao/exclusao de conta) ou
contatando o pesquisador responsavel.

9. SEGURANCA DA INFORMACAO

Adotamos medidas tecnicas e organizacionais para proteger seus dados,
incluindo: criptografia de determinados campos sensiveis em repouso;
comunicacao criptografada (HTTPS/TLS) entre aplicativo e servidores; controle
de acesso baseado em autenticacao; e um mecanismo de log de consentimento
imutavel (cadeia de hashes assinada criptograficamente) que impede a
alteracao ou exclusao dos registros de aceite destes Termos, desta Politica e
do TCLE.

10. COOKIES E ARMAZENAMENTO LOCAL

O aplicativo utiliza armazenamento local do navegador (localStorage) para
guardar preferencias funcionais (idioma, filtros de descoberta, saldo de
moeda virtual, personalizacao visual) exclusivamente no seu proprio
dispositivo, sem finalidade de rastreamento publicitario ou compartilhamento
com terceiros.

11. MENORES DE IDADE

O Servico e destinado exclusivamente a pessoas com 18 anos ou mais.

12. ALTERACOES DESTA POLITICA

Podemos atualizar esta Politica periodicamente. Alteracoes materiais serao
comunicadas dentro do aplicativo e exigirao novo aceite explicito antes da
continuidade do uso do Servico.

13. CONTATO E AUTORIDADE NACIONAL DE PROTECAO DE DADOS

Duvidas, solicitacoes ou reclamacoes sobre o tratamento dos seus dados
pessoais podem ser enviadas ao pesquisador responsavel, Luis Carlos Macedo
Moreira, ou ao Comite de Etica em Pesquisa responsavel (ver TCLE). Voce
tambem pode apresentar reclamacao a Autoridade Nacional de Protecao de Dados
(ANPD) — www.gov.br/anpd."""


def publish_pilot_documents(apps, schema_editor):
    # Ver nota em 0020_seed_legal_documents.py sobre por que o content_hash
    # e calculado manualmente aqui (o model "historico" do apps.get_model()
    # nao inclui o save() customizado de bonding/models/legal.py).
    LegalDocumentVersion = apps.get_model("bonding", "LegalDocumentVersion")
    from django.utils import timezone

    now = timezone.now()

    # TCLE e um documento novo (nunca existiu antes) — so cria se ainda nao existir.
    LegalDocumentVersion.objects.get_or_create(
        document_type="research_consent",
        version_label="1.0",
        defaults={
            "content": TCLE_CONTENT,
            "content_hash": hashlib.sha256(TCLE_CONTENT.encode("utf-8")).hexdigest(),
            "is_current": True,
            "effective_date": now.date(),
            "published_at": now,
        },
    )

    # Termos de Uso e Politica de Privacidade: a v1.0 (criada em
    # 0020_seed_legal_documents.py) deixa de ser a vigente, e uma v1.1
    # revisada (modo demonstracao academica) passa a ser a corrente.
    for document_type, version_label, content in (
        ("terms_of_use", "1.1", TERMS_OF_USE_V1_1_CONTENT),
        ("privacy_policy", "1.1", PRIVACY_POLICY_V1_1_CONTENT),
    ):
        existing = LegalDocumentVersion.objects.filter(
            document_type=document_type, version_label=version_label
        ).first()
        if existing:
            continue
        LegalDocumentVersion.objects.filter(
            document_type=document_type, is_current=True
        ).update(is_current=False)
        LegalDocumentVersion.objects.create(
            document_type=document_type,
            version_label=version_label,
            content=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            is_current=True,
            effective_date=now.date(),
            published_at=now,
        )


def unpublish_pilot_documents(apps, schema_editor):
    LegalDocumentVersion = apps.get_model("bonding", "LegalDocumentVersion")

    LegalDocumentVersion.objects.filter(
        document_type="research_consent", version_label="1.0"
    ).delete()

    for document_type in ("terms_of_use", "privacy_policy"):
        LegalDocumentVersion.objects.filter(
            document_type=document_type, version_label="1.1"
        ).delete()
        LegalDocumentVersion.objects.filter(
            document_type=document_type, version_label="1.0"
        ).update(is_current=True)


class Migration(migrations.Migration):

    dependencies = [
        ("bonding", "0023_research_consent_choices"),
    ]

    operations = [
        migrations.RunPython(publish_pilot_documents, reverse_code=unpublish_pilot_documents),
    ]
