"""Seed da versao 1.0 dos Termos de Uso e da Politica de Privacidade.

IMPORTANTE: o conteudo abaixo e um RASCUNHO gerado para viabilizar a
implementacao tecnica do fluxo de consentimento. NAO CONSTITUI ACONSELHAMENTO
JURIDICO e precisa ser revisado por advogado especializado em protecao de
dados (LGPD) antes de qualquer publicacao em producao. Campos entre colchetes
(ex.: [RAZAO SOCIAL]) sao placeholders que devem ser preenchidos com os dados
reais da empresa antes da revisao juridica.

O conteudo e mantido literal nesta migration (e nao importado de um modulo
Python separado) de proposito: uma migration de dados deve ser um retrato
congelado e auto-contido do estado que ela cria — alteracoes de texto depois
da publicacao da v1.0 devem ser feitas publicando uma NOVA versao via
bonding.services.legal.publish_document_version(), nunca editando este
arquivo ou o registro ja criado (o proprio ConsentRecord que referencia esta
versao depende do hash do conteudo permanecer estavel)."""

import hashlib

from django.db import migrations

TERMS_OF_USE_CONTENT = """TERMOS DE USO — BONDING

AVISO: este documento e um rascunho preparado para fins de implementacao
tecnica do aplicativo Bonding e ainda nao foi revisado por advogado. Nao deve
ser publicado em producao sem revisao juridica formal, preenchimento dos
dados societarios reais e adequacao ao modelo de negocio final.

Versao 1.0 — vigente a partir da data de publicacao indicada no aplicativo.

1. QUEM SOMOS

O Bonding e um aplicativo de relacionamento operado por [RAZAO SOCIAL DA
EMPRESA], inscrita no CNPJ sob o no [CNPJ], com sede em [ENDERECO COMPLETO]
("Bonding", "nos"). Estes Termos de Uso regulam o acesso e uso do aplicativo
e dos servicos associados (o "Servico") por qualquer pessoa que crie uma
conta ("voce", "usuario").

2. ACEITACAO DOS TERMOS

Ao criar uma conta no Bonding, voce declara que leu, compreendeu e concorda
integralmente com estes Termos de Uso e com a Politica de Privacidade, que
integra este documento por referencia. Caso nao concorde com qualquer
disposicao, voce nao devera se cadastrar ou utilizar o Servico.

3. ELEGIBILIDADE

3.1. O Servico e destinado exclusivamente a pessoas com 18 (dezoito) anos ou
mais. Ao se cadastrar, voce declara e garante que possui a idade minima
exigida e plena capacidade civil para celebrar este contrato.

3.2. Voce declara que as informacoes fornecidas no cadastro e no perfil sao
verdadeiras, precisas e atualizadas, e se compromete a mante-las assim.

3.3. E vedado o cadastro de pessoas anteriormente banidas do Servico, bem
como a criacao de mais de uma conta por pessoa sem autorizacao expressa.

4. CADASTRO E CONTA

4.1. Voce e responsavel por manter a confidencialidade de sua senha e por
todas as atividades realizadas em sua conta.

4.2. Notifique-nos imediatamente sobre qualquer uso nao autorizado de sua
conta.

4.3. O cadastro completo do perfil pode exigir a verificacao de identidade
por reconhecimento facial, conforme detalhado na Politica de Privacidade e
mediante consentimento especifico e destacado, coletado separadamente antes
do envio de qualquer imagem para esse fim.

5. DESCRICAO DO SERVICO

O Bonding permite que usuarios criem um perfil, descubram e curtam outros
perfis, formem conexoes mutuas ("matches"), troquem mensagens de texto,
imagem e video, participem de chamadas de video, publiquem "stories"
temporarios, e acessem funcionalidades adicionais mediante planos de
assinatura premium ou moeda virtual interna (lacos/ribbons, coracoes/hearts e
rewinds), cujas regras de conversao e uso estao descritas dentro do proprio
aplicativo.

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
operar e disponibilizar o Servico a voce e aos usuarios com quem interage.

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

10. ASSINATURAS, PAGAMENTOS E REEMBOLSO

10.1. Determinadas funcionalidades exigem a contratacao de planos de
assinatura paga, processados atraves de parceiro de pagamentos (PIX e
cartao). Precos, periodicidade e formas de pagamento sao informados no
aplicativo antes da confirmacao da compra.

10.2. Nos termos do artigo 49 do Codigo de Defesa do Consumidor, voce tem
direito de arrependimento em ate 7 (sete) dias corridos a contar da
contratacao, desde que a funcionalidade paga ainda nao tenha sido
efetivamente utilizada, mediante solicitacao pelos canais de atendimento
informados no aplicativo.

10.3. Moedas virtuais internas (lacos, coracoes, rewinds) nao possuem valor
monetario de resgate e nao sao conversiveis em dinheiro, servindo
exclusivamente para uso dentro do Servico.

11. SUSPENSAO E ENCERRAMENTO

11.1. Voce pode encerrar sua conta a qualquer momento pelas configuracoes do
aplicativo, observados os efeitos descritos na Politica de Privacidade quanto
ao tratamento dos dados apos o encerramento.

11.2. Podemos suspender ou encerrar sua conta em caso de violacao destes
Termos, exigencia legal, ou risco a seguranca de outros usuarios.

12. LIMITACAO DE RESPONSABILIDADE

Na maxima extensao permitida pela legislacao aplicavel, o Bonding nao se
responsabiliza por danos indiretos, condutas de terceiros, ou pela precisao
das informacoes fornecidas por outros usuarios, sem prejuizo das
responsabilidades que a lei brasileira atribui de forma inafastavel ao
fornecedor de servicos.

13. ALTERACOES DESTES TERMOS

Podemos atualizar estes Termos periodicamente. Alteracoes materiais serao
comunicadas dentro do aplicativo e exigirao novo aceite explicito antes da
continuidade do uso do Servico, por meio do mecanismo de consentimento
versionado do aplicativo.

14. LEGISLACAO APLICAVEL E FORO

Estes Termos sao regidos pelas leis da Republica Federativa do Brasil. Fica
eleito o foro da comarca de [CIDADE/UF] para dirimir quaisquer controversias,
com renuncia a qualquer outro, por mais privilegiado que seja, resguardado o
foro do consumidor quando aplicavel.

15. CONTATO

Duvidas sobre estes Termos podem ser encaminhadas para [E-MAIL DE CONTATO/
SAC]."""

PRIVACY_POLICY_CONTENT = """POLITICA DE PRIVACIDADE — BONDING

AVISO: este documento e um rascunho preparado para fins de implementacao
tecnica do aplicativo Bonding e ainda nao foi revisado por advogado
especializado em protecao de dados. Nao deve ser publicado em producao sem
revisao juridica formal e preenchimento dos dados reais da empresa e do
Encarregado de Dados (DPO).

Versao 1.0 — vigente a partir da data de publicacao indicada no aplicativo.

1. INTRODUCAO E CONTROLADOR

Esta Politica de Privacidade descreve como [RAZAO SOCIAL DA EMPRESA], CNPJ
[CNPJ] ("Bonding", "nos"), na qualidade de controladora de dados pessoais nos
termos da Lei no 13.709/2018 (Lei Geral de Protecao de Dados — LGPD), coleta,
usa, compartilha e protege os dados pessoais dos usuarios do aplicativo
Bonding.

2. ENCARREGADO DE DADOS (DPO)

Nos termos do art. 41 da LGPD, o Bonding [AINDA NAO POSSUI / POSSUI]
Encarregado de Dados formalmente designado. Contato do Encarregado:
[NOME DO ENCARREGADO — E-MAIL DE CONTATO]. Ate a designacao formal, duvidas
sobre tratamento de dados pessoais podem ser encaminhadas para
[E-MAIL DE CONTATO/SAC].

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
finalidade. A imagem da selfie e retida pelo prazo indicado na secao 7 abaixo
e entao excluida fisicamente do armazenamento; o resultado da analise
(pontuacao de similaridade e status aprovado/rejeitado) e retido de forma
criptografada.

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

3.7. Dados de pagamento: ao contratar um plano premium, seu CPF e enviado
diretamente ao nosso parceiro de processamento de pagamentos (AbacatePay)
para fins de emissao de cobranca (boleto/PIX/cartao). O Bonding NAO armazena
seu CPF ou dados de cartao em seus proprios sistemas — esses dados transitam
apenas para o processamento da cobranca. Mantemos, isso sim, o historico do
status da sua assinatura (ativa, expirada, etc.).

3.8. Dados de dispositivo e tecnicos: endereco IP, identificador do
navegador/dispositivo (user-agent), token de notificacao push, registros de
data e hora de acesso.

3.9. Dados de uso e comportamento: curtidas, matches, bloqueios, denuncias,
saldo e historico de moeda virtual interna, musica selecionada via busca
publica no catalogo do Spotify (nao acessamos sua conta pessoal do Spotify).

4. BASES LEGAIS PARA O TRATAMENTO

Tratamos seus dados pessoais com fundamento em uma ou mais das seguintes
bases legais previstas no art. 7o da LGPD, conforme a finalidade especifica:

- Execucao de contrato (art. 7o, V): dados necessarios para viabilizar as
  funcionalidades essenciais do Servico (cadastro, matches, mensagens,
  assinatura de planos);
- Consentimento (art. 7o, I): funcionalidades opcionais, como sugestoes de
  local baseadas em geolocalizacao precisa;
- Cumprimento de obrigacao legal ou regulatoria (art. 7o, II): guarda de
  registros fiscais e de pagamento pelo prazo exigido em lei;
- Legitimo interesse (art. 7o, IX): prevencao a fraude e seguranca da
  plataforma, sempre precedido de teste de balanceamento e sem prejuizo dos
  seus direitos e liberdades fundamentais.

Para os DADOS PESSOAIS SENSIVEIS descritos nos itens 3.2 (genero/orientacao
sexual) e 3.4 (biometria facial), a base legal exclusiva e o CONSENTIMENTO
ESPECIFICO E DESTACADO (art. 11, I da LGPD), coletado separadamente do aceite
geral destes Termos, podendo ser revogado a qualquer momento — a revogacao
pode limitar ou impedir o uso de funcionalidades que dependam desses dados
(ex.: selo de verificacao).

5. FINALIDADES DO TRATAMENTO

Usamos seus dados para: viabilizar cadastro e autenticacao; exibir seu
perfil a outros usuarios conforme suas configuracoes de privacidade;
processar curtidas e formar matches; entregar e armazenar mensagens;
processar verificacao de identidade quando solicitada; sugerir locais de
encontro proximos quando voce solicitar e consentir; processar pagamentos de
planos premium; enviar notificacoes relevantes; prevenir fraude, abuso e
violacoes destes Termos; cumprir obrigacoes legais e regulatorias; e — quando
aplicavel e com base no seu consentimento — aprimorar recomendacoes dentro
do Servico.

6. COMPARTILHAMENTO DE DADOS COM TERCEIROS

Compartilhamos dados pessoais estritamente na medida necessaria com os
seguintes operadores/parceiros, todos vinculados por obrigacoes contratuais
de confidencialidade e seguranca:

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
- AbacatePay: recebe nome, e-mail e CPF para processar cobrancas de planos
  premium.
- Spotify: recebemos apenas resultados publicos de busca no catalogo de
  musicas; nenhum dado da sua conta pessoal do Spotify e acessado.

Nao vendemos dados pessoais a terceiros. Podemos divulgar dados quando
exigido por lei, ordem judicial ou para proteger direitos, seguranca e
propriedade do Bonding, de seus usuarios ou de terceiros.

7. RETENCAO DE DADOS

Adotamos o principio da minimizacao (art. 6o, VII da LGPD) e propomos os
seguintes prazos de retencao, sujeitos a revisao formal quando uma politica
de retencao definitiva for aprovada pela empresa:

- Dados de cadastro e perfil: mantidos enquanto a conta estiver ativa; apos
  exclusao da conta, dados identificaveis sao anonimizados, exceto registros
  com obrigacao legal de guarda (ex.: dados de assinatura/pagamento, por ate
  5 anos, prazo fiscal/civil aplicavel);
- Selfie de verificacao de identidade: proposta de exclusao fisica da imagem
  em ate 90 (noventa) dias apos a conclusao da verificacao, mantendo-se
  apenas o resultado (aprovado/rejeitado) de forma criptografada;
- Pings de geolocalizacao precisa: proposta de exclusao apos 30 (trinta)
  dias;
- Mensagens: mantidas enquanto a conversa/conta estiver ativa, podendo ser
  excluidas antecipadamente por voce dentro do aplicativo;
- Log de consentimento (aceites de termos e de dados sensiveis): mantido de
  forma permanente e imutavel, mesmo apos a exclusao da conta, pois constitui
  prova do cumprimento de obrigacoes legais e do exercicio de direitos pelo
  titular.

8. SEUS DIREITOS COMO TITULAR DE DADOS

Nos termos do art. 18 da LGPD, voce tem direito a, mediante requisicao:

- Confirmar a existencia de tratamento de seus dados;
- Acessar seus dados pessoais;
- Corrigir dados incompletos, inexatos ou desatualizados;
- Solicitar anonimizacao, bloqueio ou eliminacao de dados desnecessarios,
  excessivos ou tratados em desconformidade com a LGPD;
- Solicitar a portabilidade dos seus dados a outro fornecedor de servico;
- Solicitar a eliminacao dos dados tratados com base no seu consentimento;
- Obter informacoes sobre as entidades com as quais compartilhamos seus
  dados;
- Ser informado sobre a possibilidade de nao fornecer consentimento e sobre
  as consequencias da negativa;
- Revogar o consentimento a qualquer momento, sem prejuizo da legalidade do
  tratamento realizado antes da revogacao.

Voce pode exercer esses direitos pelos canais de atendimento indicados no
aplicativo ou diretamente com o Encarregado de Dados (secao 2). Funcoes de
autoatendimento para exclusao de conta e exportacao de dados estao previstas
no roteiro de evolucao do aplicativo.

9. SEGURANCA DA INFORMACAO

Adotamos medidas tecnicas e organizacionais para proteger seus dados,
incluindo: criptografia de determinados campos sensiveis em repouso;
comunicacao criptografada (HTTPS/TLS) entre aplicativo e servidores; controle
de acesso baseado em autenticacao; e um mecanismo de log de consentimento
imutavel (cadeia de hashes assinada criptograficamente) que impede a
alteracao ou exclusao dos registros de aceite destes Termos e desta
Politica, garantindo a integridade e a nao-repudiabilidade das evidencias de
consentimento.

10. COOKIES E ARMAZENAMENTO LOCAL

O aplicativo utiliza armazenamento local do navegador (localStorage) para
guardar preferencias funcionais (idioma, filtros de descoberta, saldo de
moeda virtual, personalizacao visual) exclusivamente no seu proprio
dispositivo, sem finalidade de rastreamento publicitario ou compartilhamento
com terceiros. Nao utilizamos cookies ou pixels de rastreamento de terceiros
para fins de publicidade comportamental.

11. MENORES DE IDADE

O Servico e destinado exclusivamente a pessoas com 18 anos ou mais. Nao
coletamos intencionalmente dados de menores de idade. Caso identifiquemos
uma conta de pessoa menor de idade, ela sera encerrada e os dados
correspondentes serao excluidos, ressalvadas obrigacoes legais de guarda.

12. ALTERACOES DESTA POLITICA

Podemos atualizar esta Politica periodicamente. Alteracoes materiais serao
comunicadas dentro do aplicativo e exigirao novo aceite explicito antes da
continuidade do uso do Servico.

13. CONTATO E AUTORIDADE NACIONAL DE PROTECAO DE DADOS

Duvidas, solicitacoes ou reclamacoes sobre o tratamento dos seus dados
pessoais podem ser enviadas para [E-MAIL DE CONTATO/SAC] ou para o
Encarregado de Dados indicado na secao 2. Caso nao fique satisfeito com a
resposta, voce tambem pode apresentar reclamacao a Autoridade Nacional de
Protecao de Dados (ANPD) — www.gov.br/anpd."""


def seed_documents(apps, schema_editor):
    # apps.get_model() retorna um model "historico" reconstruido a partir do
    # estado das migrations — ele NAO inclui o save() customizado definido em
    # bonding/models/legal.py, entao o content_hash precisa ser calculado
    # manualmente aqui, com a mesma logica (sha256 do content em utf-8).
    LegalDocumentVersion = apps.get_model("bonding", "LegalDocumentVersion")
    from django.utils import timezone

    now = timezone.now()
    LegalDocumentVersion.objects.get_or_create(
        document_type="terms_of_use",
        version_label="1.0",
        defaults={
            "content": TERMS_OF_USE_CONTENT,
            "content_hash": hashlib.sha256(TERMS_OF_USE_CONTENT.encode("utf-8")).hexdigest(),
            "is_current": True,
            "effective_date": now.date(),
            "published_at": now,
        },
    )
    LegalDocumentVersion.objects.get_or_create(
        document_type="privacy_policy",
        version_label="1.0",
        defaults={
            "content": PRIVACY_POLICY_CONTENT,
            "content_hash": hashlib.sha256(PRIVACY_POLICY_CONTENT.encode("utf-8")).hexdigest(),
            "is_current": True,
            "effective_date": now.date(),
            "published_at": now,
        },
    )


def unseed_documents(apps, schema_editor):
    LegalDocumentVersion = apps.get_model("bonding", "LegalDocumentVersion")
    LegalDocumentVersion.objects.filter(
        document_type__in=["terms_of_use", "privacy_policy"], version_label="1.0"
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bonding", "0019_consent_record_worm_trigger"),
    ]

    operations = [
        migrations.RunPython(seed_documents, reverse_code=unseed_documents),
    ]
