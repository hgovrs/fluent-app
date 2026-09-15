# Fluent 🌱

Um app de prática de idiomas em **Flutter + Firebase**, com interface em português,
curso inicial de inglês e funcionamento **offline, sem conta e sem assinatura**.
O Firebase é opcional: ao configurá-lo, o aluno pode guardar e recuperar seu
progresso manualmente entre dispositivos.

## O que está implementado

- Trilha inicial preservada: 4 unidades, 12 lições e 60 exercícios originais.
- Cinco trilhas adicionais de prática parcial A1–C1, com material de estudo,
  exercícios originais e referências institucionais complementares.
- Exercícios de múltipla escolha, escrita e organização de frases.
- Feedback explicativo, correção tolerante a maiúsculas e pontuação, sem vidas
  limitadas nem punição por errar.
- XP, meta diária configurável, sequência de dias e progresso por curso.
- Revisão espaçada de exercícios estudados, incluindo erros.
- Persistência local e recuperação de falhas de armazenamento.
- Conta opcional com e-mail/senha, recuperação de senha e backup privado no
  Cloud Firestore. Nenhum envio automático do progresso.
- Layout adaptável, sem fontes, imagens ou APIs de IA pagas.
- Testes de domínio, navegação, exercícios e regras de acesso; workflow de CI.

As trilhas são **prática parcial**, não cursos CEFR completos nem certificação de
proficiência. Não há avaliação de pronúncia, reconhecimento de voz, vídeos,
chatbot, ranking público ou conteúdo copiado de outros aplicativos.

## Pesquisa e decisões de produto

Pesquisa realizada antes da implementação, em setembro de 2026:

| Referência | Ideia aproveitada | Decisão no Fluent |
| --- | --- | --- |
| [Duolingo — trilha de aprendizado](https://blog.duolingo.com/learning-path-update/) | Lições curtas, progressão e hábito diário | Trilha guiada, XP e sequência, sem limite de vidas |
| [Busuu — curso de inglês](https://www.busuu.com/en/course/learn-english) | Unidades temáticas e situações práticas | Inglês iniciante organizado por contextos cotidianos |
| [Memrise](https://www.memrise.com/) | Retenção por revisão espaçada | Revisão local e determinística, sem IA ou serviço pago |

As referências inspiram as funcionalidades, não a marca, as ilustrações ou o
conteúdo. O visual e os exercícios deste projeto são próprios.

## Conteúdo A1–C1, fontes e uso pessoal

### O que está disponível no app

O seletor **Escolha sua trilha** permite começar em qualquer nível; dentro de
cada trilha, as lições são liberadas em sequência. Progresso e revisão continuam
separados por curso. O curso inicial e seus IDs não foram substituídos.

| Trilha | Unidades / lições / exercícios | Foco |
| --- | --- | --- |
| Primeiros passos (existente) | 4 / 12 / 60 | Introdução cotidiana |
| A1 — Fundamentos | 4 / 12 / 72 | Identidade, rotina, tempo, compras e lugares |
| A2 | 4 / 12 / 72 | Passado, planos, comparação e experiências |
| B1 | 4 / 12 / 72 | Narrativas, hipóteses e comunicação no trabalho |
| B2 — Argumentação | 4 / 12 / 72 | Argumentos, inferência, registro e correspondência |
| C1 — Nuance e precisão | 4 / 12 / 72 | Posicionamento, coesão, leitura crítica e precisão |

São **420 exercícios em 72 lições**, incluindo os 60 anteriores. Cada nova
lição contém uma explicação em português em **Antes de praticar**, também
acessível pelo ícone de livro durante os exercícios. Há leitura de trechos
originais, escolha, preenchimento de respostas delimitadas e ordenação de
palavras, com feedback explicativo. **Fontes e licenças** funciona offline como
registro de referências; os endereços externos precisam de internet.

O mapeamento A1–C1 é **editorial e aproximado**, não validado pelas instituições
citadas. Não equivale a cumprir todos os descritores CEFR. Faltam avaliação oral,
escuta com áudio real, interação espontânea, redações abertas com avaliação e
validação pedagógica independente. B2/C1 especialmente são prática de leitura e
linguagem, não prova de proficiência. Não há C2. O app não promete avaliar
respostas livres com correção determinística.

### Auditoria das referências

A pesquisa distingue **referência de leitura**, **adaptação** e **arquivo
adquirido**. As novas explicações, situações, textos e questões foram escritos
para o Fluent; **não são cópias nem conversões integrais dos livros**.
`sourceIds` indica leitura complementar, não autoria institucional dos exercícios.
Não há associação, endosso ou certificação dessas instituições.

O registro versionado é `assets/content/sources.json`, contendo instituição,
autoria, licença indicada, restrições, estado da análise e arquivos candidatos.

| Fonte | Complementação pretendida | Limites de licença/cobertura |
| --- | --- | --- |
| [BC Reads — BCcampus / Vancouver Community College](https://opentextbc.ca/abealf1/) | Leitura e alfabetização de adultos; Readers e Course Packs 1–6 | CC BY 4.0, salvo exceções. Os seis níveis **não são** A1–C2. |
| [Communication Beginnings — Portland State](https://pdxscholar.library.pdx.edu/pdxopen/18/) | Comunicação, viagens, rotinas, lugares e trabalho | CC BY-NC 4.0 indicada no livro; conferir separadamente áudios e imagens. |
| [Let's Get to Work! — PCC](https://sites.google.com/pcc.edu/oer-for-esol/home/lets-get-to-work) | Comunicação profissional intermediária | Conferir licença no arquivo específico e direitos de vídeos externos. |
| [In the Loop — PCC](https://sites.google.com/pcc.edu/oer-for-esol/home/in-the-loop) | Comunicação intermediária superior | Nível interno do PCC; não converter automaticamente para B2. |
| [Synthesis — PCC](https://sites.google.com/pcc.edu/oer-for-esol/home/synthesis) | Escrita acadêmica avançada | Não substitui um curso completo C1; direitos por arquivo. |
| [English: skills for learning — Open University](https://www.open.edu/openlearn/education-development/english-skills-learning/content-section-overview) | Leitura e organização da escrita acadêmica | CC BY-NC-SA 4.0 geral, com exceções em Acknowledgements. |

**Limitação desta execução:** o ambiente não conseguiu acessar diretamente
vários sites das editoras (falhas de DNS). A pesquisa de metadados e sumários não
é uma leitura integral de todas as obras. Não se declara download concluído,
auditoria completa de mídia nem reutilização autorizada de arquivos não
inspecionados. O material de prática original funciona independentemente desses
downloads; nenhuma referência inacessível bloqueia o aprendizado.

### Licenças: agora e antes de publicar

O uso solicitado é **pessoal, local e não comercial**. Isso permite considerar
obras NC conforme seus termos, mas não dispensa atribuição, avisos de licença,
identificação de alterações e demais condições. Estar no computador local,
ser gratuito ou estar em repositório privado não substitui uma licença.

- **BY:** atribuir autor, título, fonte e licença; informar adaptações.
- **NC:** não explorar comercialmente sem permissão separada. Anúncios,
  assinaturas e distribuição ligada a atividade comercial precisam de análise.
- **SA:** adaptações distribuídas devem respeitar a licença compatível exigida;
  isso não torna automaticamente todo o código do app sujeito à mesma licença.
- Imagens, gravações, músicas, marcas e vídeos incorporados podem ter direitos
  diferentes. Não baixar vídeos de plataformas nem remover proteção de acesso.
- Não adaptar nem distribuir conteúdo **ND**, de licença desconhecida ou
  excluído da licença geral sem autorização adequada.

**Não deixar a revisão de direitos somente para depois da publicação.** Um
repositório público já distribui o que recebe. Por isso, os downloads pessoais
ficam ignorados pelo Git e não entram automaticamente no build. A versão atual
empacota os exercícios originais, as notas próprias e o índice de referências,
não os livros NC nem suas mídias.

Antes de exposição pública ou comercial: inventariar cada arquivo e adaptação;
verificar licença e exceções; manter apenas o que autoriza o uso pretendido;
substituir ou remover os demais; revisar atribuições dentro do app e nos pacotes;
recompilar e invalidar pacotes/cache antigos. Retirar depois não desfaz uma
distribuição anterior. Preservar IDs do conteúdo original e não reutilizar IDs
de exercícios removidos com outro significado.

### Armazenamento e aquisição

Há duas camadas deliberadamente separadas:

1. **App offline:** `assets/courses/` contém catálogo e cursos JSON;
   `assets/content/` contém referências e licenças. Ambos são assets Flutter
   versionados neste repositório. Não há chamadas de rede para estudar.
2. **Biblioteca editorial pessoal:** `content-cache/` guarda livros originais
   e recibos de aquisição, ignorados pelo Git e fora do `pubspec.yaml`.
   Eles servem à leitura/auditoria, **não são automaticamente exibidos pelo app**.
   PDF/EPUB e players de áudio/vídeo não estão implementados nesta versão.

Preferir exportações **PDF/EPUB oferecidas pela própria instituição**, em vez de
espelhar sites inteiros ou baixar páginas de cursos com conteúdo incompleto.
Conservar o original sem alterações e registrar autor, URL, licença, data,
tamanho e SHA-256. Baixar áudio/imagem separadamente só depois de conferir sua
própria autorização. Vídeos grandes não devem ser commits no Git.

O comando de aquisição `tool/content_library.py` usa somente Python 3 padrão:
consulta o registro, exige revisão de licença por arquivo e permite optar
explicitamente por materiais NC. Os comandos devem ser executados na raiz:

```sh
python3 tool/content_library.py list
python3 tool/content_library.py download --source bc-reads
python3 tool/content_library.py download --source communication-beginnings --allow-noncommercial
python3 tool/content_library.py verify --source communication-beginnings
```

Uma lista de downloads vazia significa **não adquirido / aguardando URL e
licença verificadas**, não sucesso. Não transformar uma URL inferida em download
aprovado. Para cadastrar um arquivo, conferir manualmente o link oficial e
os créditos, adicionar `id`, `url`, `format` (`pdf` ou `epub`) e
`licenseReviewed: true` em `downloads` da fonte; acrescentar `sha256` quando
houver um hash confiável previamente obtido. Sem essa revisão o comando recusa
o arquivo. A primeira aquisição registra um hash de integridade local, que não
é por si só prova de autoria ou autorização.

O comando verifica formato, limita tamanho e grava de forma atômica com recibo;
não extrai arquivos nem executa conteúdo baixado. Falhas de rede/licença não
modificam cursos do app. Conferir o recibo antes de confiar no cache; não
versionar o cache apenas porque o download passou.

### Migração futura para nuvem sem cobrança automática

**Não implementada nem ativada agora.** Manter uma cópia local funcional é o
requisito; o backend de progresso continua separado do conteúdo didático.

1. Publicar somente pacotes com direitos aprovados para a distribuição escolhida.
   Manter cursos JSON pequenos e um manifesto versionado com ID, versão, URL,
   tamanho, SHA-256, licença e atribuições; hospedar mídias separadamente.
2. Preferir inicialmente **Firebase Hosting no Spark**, já compatível com este
   projeto, sem conta de faturamento. Hospedar arquivos estáticos, não livros
   binários no Firestore. Conferir cotas atuais de armazenamento e transferência
   em [Hosting usage and pricing](https://firebase.google.com/docs/hosting/usage-quotas-pricing).
   Serviço gratuito tem limites e pode ficar indisponível ao excedê-los.
3. Como alternativa, avaliar **Cloudflare Pages Free** para JSON e arquivos
   estáticos pequenos, conferindo [limites oficiais](https://developers.cloudflare.com/pages/platform/limits/),
   termos e tamanho máximo por arquivo. Não tratar uma hospedagem pública como
   biblioteca privada; não colocar materiais ainda pendentes em URLs públicas.
4. Em uma implementação futura, baixar por HTTPS sob demanda, validar tamanho,
   esquema e hash antes de ativar o pacote, gravar em cache de forma atômica e
   manter a versão anterior/embutida se a rede falhar. Permitir apagar downloads
   sem apagar progresso. Preservar IDs estáveis e definir migração de conteúdo.
5. No Android, usar armazenamento privado do app; na web, planejar IndexedDB/
   Cache Storage, cotas e limpeza pelo navegador. A atual versão web **não
   garante** funcionamento offline depois de fechada.
6. Monitorar cotas e deixar downloads opcionais; não habilitar Blaze nem serviços
   pagos automaticamente. Cloud Storage for Firebase não é a escolha de custo
   zero sem faturamento nesta arquitetura. Áudio/vídeo em escala pode ultrapassar
   qualquer franquia grátis; reduzir/selecionar conteúdo em vez de prometer
   tráfego ilimitado.

## Executar localmente

Requisitos: Flutter estável **3.35 ou superior**, Dart **3.9 ou superior** e o
ambiente da plataforma escolhida. Use uma versão estável atual se os plugins
nativos exigirem SDKs mais recentes.

Na raiz do repositório:

```sh
flutter doctor
flutter pub get
flutter run -d chrome
# ou, com um Android/emulador conectado:
flutter run
```

Sem parâmetros de Firebase, o app inicia em modo local. Não é necessário criar
projeto, cadastrar cartão ou autenticar para experimentar todas as lições.

```sh
flutter analyze
flutter test
flutter build web
flutter build apk --debug
```

O APK de desenvolvimento fica em
`build/app/outputs/flutter-apk/app-debug.apk`. Para uma distribuição Android
pública, configure assinatura de release com sua própria chave fora do Git.
Nunca publique o APK assinado com a chave de debug como release.

O aplicativo instalado no celular usa conteúdo empacotado e funciona offline.
A versão web precisa ser carregada pela rede; não se promete instalação PWA
ou funcionamento web offline após fechar o navegador.

## Firebase sem custo de infraestrutura

Use exclusivamente o plano **Spark**, **sem vincular uma conta de faturamento**.
Não habilite Blaze para este projeto. A gratuidade tem cotas: excedê-las pode
indisponibilizar o backup, mas não deve impedir as lições locais.

1. Crie seu projeto no [Firebase Console](https://console.firebase.google.com/).
2. Em Authentication, habilite **E-mail/senha**. Não habilite SMS.
3. Crie um banco **Cloud Firestore Standard**, em modo de produção; escolha
   conscientemente sua região, pois ela afeta localização dos dados e latência.
4. Registre os apps que utilizará: Android com pacote `app.fluent.fluent_app`,
   web e/ou iOS com o bundle identifier correspondente ao runner.
5. Publique as regras deste repositório antes de usar o backup. Não deixe
   regras abertas de modo de teste.
6. Copie os valores públicos de configuração do app registrado e passe-os
   como `dart-define`. Cada plataforma tem seu próprio `appId`.

```sh
flutter run -d chrome \
  --dart-define=FIREBASE_API_KEY=VALOR_DO_SEU_PROJETO \
  --dart-define=FIREBASE_APP_ID=ID_DO_APP_WEB \
  --dart-define=FIREBASE_MESSAGING_SENDER_ID=ID_DO_REMETENTE \
  --dart-define=FIREBASE_PROJECT_ID=ID_DO_PROJETO \
  --dart-define=FIREBASE_AUTH_DOMAIN=DOMINIO_AUTH_DO_PROJETO
```

Para Android, use a mesma configuração com o `appId` Android e o dispositivo
Android. Para iOS, use o `appId` iOS e `IOS_BUNDLE_ID`. A inicialização é feita
por `FirebaseOptions`, sem arquivo de conta de serviço e sem credenciais
administrativas dentro do aplicativo.

Os parâmetros Firebase identificam seu projeto, mas **não substituem as regras
de segurança**. Não coloque senhas de usuários, chaves privadas, keystores ou
contas de serviço em `dart-define`, no repositório ou no aplicativo.

Com a CLI oficial do Firebase instalada e autenticada na sua própria conta:

```sh
firebase deploy --only firestore:rules,firestore:indexes --project ID_DO_PROJETO
```

No web, adicione seu domínio (e `localhost` para desenvolvimento) aos domínios
autorizados do Authentication conforme necessário. Configure também a política
de senha e proteção contra enumeração de e-mails no console.

### Uso e limites

- O curso inteiro acompanha o app: **zero leituras Firestore por exercício**.
- Não há listeners de progresso, ranking, consultas globais ou sincronização
  automática. A nuvem só é acessada por ações explícitas da conta.
- O backup é um documento privado em `users/{uid}/backups/progress`, com
  versão de esquema, JSON limitado a menos de 200.000 caracteres e timestamp.
- As regras limitam o acesso ao próprio usuário e validam formato/tamanho do
  envelope. O cliente valida o conteúdo ao restaurar. XP não tem valor
  financeiro nem autoridade para competições.
- O backup substitui o anterior da mesma conta. Para combinar dispositivos,
  recupere primeiro o backup e só depois salve um novo. Não é sincronização
  em tempo real nem resolução automática de alterações simultâneas.
- Spark oferece, entre outras cotas, **1 GiB armazenado, 50 mil leituras/dia e
  20 mil escritas/dia** no Firestore. Monitore também cotas de Authentication,
  tráfego e Hosting; elas não são ilimitadas.
- Não usamos Cloud Functions, Cloud Storage, autenticação por telefone,
  tradução paga, APIs generativas nem extensões com cobrança.
- Cloud Storage requer Blaze conforme a transição documentada pelo Firebase;
  por isso, não faz parte desta arquitetura.

Fontes: [preços e cotas](https://firebase.google.com/pricing),
[planos Spark/Blaze](https://firebase.google.com/docs/projects/billing/firebase-pricing-plans),
[cotas Firestore](https://firebase.google.com/docs/firestore/quotas) e
[mudanças no Storage](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024).
Confira sempre as condições atuais antes de publicar.

Hospedar a versão web é opcional, usando o Firebase Hosting no Spark:

```sh
flutter build web # acrescente os dart-defines para habilitar a nuvem
firebase deploy --only hosting --project ID_DO_PROJETO
```

**Custo zero de infraestrutura não significa publicação gratuita nas lojas.**
O APK pode ser instalado diretamente e o site pode usar a cota grátis do
Hosting. Google Play e Apple têm taxas/requisitos próprios. Compilar iOS exige
macOS/Xcode e instalar/distribuir exige a assinatura adequada.

## Progresso, privacidade e armazenamento

O progresso é local ao **dispositivo**, separado por curso, e não é apagado ao
sair da conta. Em aparelho compartilhado, confira a conta antes de salvar um
backup. Limpar os dados do aplicativo ou desinstalá-lo pode apagar o progresso
local; no navegador, a limpeza do armazenamento tem o mesmo efeito.

Uma conta envia e-mail e senha diretamente ao Firebase Authentication. O app
não armazena senhas no progresso nem coleta analytics. O backup só contém dados
de aprendizado e preferências. O estado de autenticação é administrado pelo SDK
Firebase. Para excluir dados na nuvem, o administrador do projeto pode excluir
o documento do usuário no Firestore e a conta no Authentication; a exclusão da
conta, sozinha, **não remove documentos Firestore**.

Antes de uma publicação pública, o responsável deve configurar a política de
privacidade, canal para exclusão de dados e requisitos legais aplicáveis à
audiência, especialmente se houver crianças.

## Adicionar outros idiomas

Os idiomas não são implementados como telas diferentes:

1. Adicione um JSON de curso em `assets/courses/`, seguindo o curso de inglês.
2. Defina `id`, `sourceLanguage`, `targetLanguage`, `title`, `level` e `units`.
3. Cada unidade contém `lessons`; cada lição contém `exercises`.
4. Os exercícios usam `choice`, `typed` ou `wordOrder`, com `prompt`, `answer`,
   `acceptedAnswers`, `options` e `explanation`, conforme o tipo.
   Novas lições também incluem `studyNotes` e `sourceIds` (referências existentes
   em `assets/content/sources.json`). Novos cursos incluem `contentVersion`
   inteiro positivo e `coverage` para explicitar o escopo. Esses campos são
   opcionais para preservar o curso inicial.
5. Registre o caminho em `assets/courses/catalog.json`. O seletor de cursos
   passa a mostrar o novo idioma automaticamente.
6. Mantenha IDs estáveis e únicos dentro do curso. Não reutilize IDs de
   exercícios antigos com outro significado, para preservar as revisões.
7. Revise o conteúdo com alguém que domine o idioma e execute os testes.

A interface é pt-BR nesta versão. Para atender falantes de outros idiomas de
origem, traduza também a interface; adicionar um curso não traduz os textos
fixos do aplicativo. Idiomas com outras regras de escrita podem exigir
ajustes na normalização de respostas.

## Estrutura

```text
assets/courses/       Catálogo e conteúdo original empacotado
assets/content/       Registro de fontes, licenças e downloads revisados
content-cache/        Livros pessoais e recibos locais (ignorado pelo Git)
lib/models/          Cursos, exercícios, progresso e revisões
lib/data/            Carregamento e validação do catálogo
lib/state/           Regras de aprendizado e coordenação do progresso
lib/services/        Persistência local e Firebase opcional
lib/screens/         Trilha, exercícios, revisão e conta
test/                Testes de domínio e widgets
tool/                Aquisição editorial de fontes, fora do runtime
firebase/            Testes das regras Firestore
android/ ios/ web/   Runners Flutter
firestore.rules      Isolamento de usuários e validação de backups
```

## Estado da validação

Na expansão de conteúdo de 15/09/2026, `flutter analyze`, `flutter test` e
`flutter build web` foram tentados, mas o ambiente não tinha `flutter` nem
`dart`; a consulta ao download do SDK retornou HTTP 403. Portanto, os novos
testes Flutter e os builds **não foram executados localmente**. Não há APK
validado incluído nesta alteração. Execute o workflow de CI ou os comandos acima
em um ambiente com Flutter antes de distribuir.

Há testes Flutter para preservar o curso inicial, validar os novos campos,
referências, conteúdo e respostas, além da consulta ao material de estudo.
A validação estrutural dos novos JSONs foi realizada durante a autoria, sem
substituir uma revisão pedagógica independente.

O utilitário de aquisição possui testes sem rede, com a biblioteca padrão:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s test -p content_library_test.py
```

Eles cobrem consentimento NC, arquivos não revisados, limites, formato,
integridade, cache, URLs/redirecionamentos e limpeza de downloads interrompidos.
Esses testes não demonstram que as editoras estejam acessíveis nem que as
licenças de todas as mídias tenham sido verificadas.