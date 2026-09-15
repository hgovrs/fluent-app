# Fluent 🌱

Um app de prática de idiomas em **Flutter + Firebase**, com interface em português,
curso inicial de inglês e funcionamento **offline, sem conta e sem assinatura**.
O Firebase é opcional: ao configurá-lo, o aluno pode guardar e recuperar seu
progresso manualmente entre dispositivos.

## O que está implementado

- Trilha progressiva de inglês iniciante: 4 unidades, 12 lições e 60 exercícios
  originais, com saudações, apresentações, situações cotidianas e viagens.
- Exercícios de múltipla escolha, escrita e organização de frases.
- Feedback explicativo, correção tolerante a maiúsculas e pontuação, sem vidas
  limitadas nem punição por errar.
- Feedback de áudio opcional por tema (Zoação leve, Torcida e Tranquilo), com
  catálogo de frases originais e geração editorial usando sua voz no ElevenLabs.
  Os MP3 precisam ser gerados antes da publicação; não acompanham este código.
- XP, meta diária configurável, sequência de dias e progresso por curso.
- Revisão espaçada de exercícios estudados, incluindo erros.
- Persistência local e recuperação de falhas de armazenamento.
- Conta opcional com e-mail/senha, recuperação de senha e backup privado no
  Cloud Firestore. Nenhum envio automático do progresso.
- Layout adaptável, sem fontes ou imagens pagas. Nenhuma API de IA é chamada
  durante as aulas; a geração opcional de áudio pode consumir créditos pagos.
- Testes de domínio, navegação, exercícios e regras de acesso; workflow de CI.

O curso é uma **introdução**, não um curso A1 completo ou uma certificação de
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

## Feedback de áudio e ElevenLabs

No ícone de alto-falante da tela inicial, escolha o tema **antes da lição**.
O mesmo seletor aparece durante as aulas e revisões. **Sem áudio** é o padrão;
a escolha é salva por curso no aparelho. Progresso antigo continua válido e
temas removidos voltam efetivamente ao modo sem áudio. Restaurar um backup não
substitui a escolha local de áudio, para não ativar brincadeiras sem consentimento.

Ao verificar uma resposta, o app sorteia uma frase da categoria `correct`
(acerto) ou `incorrect` (erro), evitando repetição imediata dentro de cada
tema/categoria enquanto a sessão estiver aberta. A explicação e a resposta
correta continuam visíveis: o áudio é uma reação, **não substitui a correção
pedagógica** e não avalia pronúncia.

| Tema | Exemplo de acerto | Exemplo de erro |
| --- | --- | --- |
| Zoação leve | “Receba! Mais uma pro gabarito!” | “Você foi com tanta certeza que até eu acreditei.” |
| Torcida | “Que categoria! Mais uma resposta no fundo da rede!” | “Hora de ajustar a estratégia! A correção mostra o caminho.” |
| Tranquilo | “Resposta correta. Continue no seu ritmo.” | “Sem pressa. Leia a explicação para se preparar para a próxima.” |

O catálogo tem 20 frases. O tema Zoação leve usa as oito reações curtas aprovadas,
incluindo adaptações de bordões brasileiros; Torcida e Tranquilo mantêm suas
frases originais. Não usamos gravações de terceiros nem imitamos suas vozes.
Referências culturais não equivalem a autorização: confira direitos e licenças
antes da distribuição. A pesquisa de feedback da
[Education Endowment Foundation](https://educationendowmentfoundation.org.uk/education-evidence/teaching-learning-toolkit/feedback)
orientou a decisão de comentar a tarefa e indicar um próximo passo, em vez de
atacar a pessoa. As brincadeiras são opcionais, sem insultos à inteligência,
comparações entre alunos ou humilhação. Não se promete que o humor, por si só,
melhore o aprendizado.

### Gerar pelo GitHub no celular (sem Flutter local)

O workflow **Gerar áudios ElevenLabs** instala Flutter/Dart no runner do GitHub
Actions. Você não precisa instalar SDK, abrir terminal ou ter computador.

1. Primeiro, integre esta alteração à **branch padrão** do repositório. O botão
   de execução manual só aparece depois que o workflow existe nessa branch;
   por segurança, o job não executa em outras branches.
2. Em **Settings → Environments**, use `copilot` ou `fluent`, onde já cadastrou
   `ELEVENLABS_API_KEY` e `ELEVENLABS_VOICE_ID`. O Voice ID pode ser um secret
   ou uma variável; a chave deve ser um secret. Não envie valores no chat.
   Configure revisores e restrição à branch padrão no ambiente quando disponíveis.
3. Abra [Actions → Gerar áudios ElevenLabs](https://github.com/hgovrs/fluent-app/actions/workflows/generate-feedback-audio.yml).
   Se a interface do aplicativo móvel não exibir **Run workflow**, abra esse
   link no navegador do celular (modo desktop, se necessário).
4. Selecione a branch padrão e o ambiente que contém os segredos. Execute
   primeiro com **generate desmarcado**: isso testa o projeto e mostra a
   quantidade de frases/caracteres sem enviar nada ao ElevenLabs.
5. Depois de conferir a prévia, execute com **generate marcado** para autorizar
   o consumo de créditos. Marque **force** se houver MP3 antigos no repositório
   após mudar voz ou frases. Para as frases novas de Zoação leve, arquivos
   previamente gerados com os mesmos IDs precisam ser substituídos.
6. Ao terminar, abra a execução e a seção **Artifacts**. O pacote
   `feedback-audio-success-…` contém MP3 e catálogo, disponível por 30 dias;
   a prévia fica disponível por 14 dias. Baixe o ZIP para ouvir os arquivos.

O ambiente é selecionado explicitamente pelo workflow: segredos em `fluent`
funcionam aqui sem precisar renomeá-lo para `copilot`. Não há execução paga
automática em pushes ou pull requests. Testes precisam passar antes da geração;
a chave fica disponível apenas na etapa que chama o ElevenLabs.

**Integração sem terminal:** após conferir os áudios, envie ao Copilot o link
da execução e peça para incorporar os MP3 ao projeto e validar o build. O ZIP
tem os arquivos na raiz; no repositório, eles pertencem a
`assets/audio_feedback/`. O workflow não faz commits, não publica releases e
não produz um APK: disponibilizar um artefato não incorpora áudio ao aplicativo.

**Falhas e custos:** lotes com `failure` no nome são parciais e podem conter
apenas o catálogo. Confira o resultado e os logs antes de repetir. Cada execução
começa em um runner limpo e não recupera artefatos anteriores; enquanto os MP3
não estiverem no repositório, rodar novamente pode cobrar todas as frases de novo,
mesmo com **force desmarcado**. Execuções são serializadas, sem cancelar uma
geração em andamento, mas cliques repetidos podem enfileirar outra cobrança.
Não publique chaves nos logs e revogue qualquer chave anteriormente exposta.

### Gerar com a sua voz em um ambiente com Flutter

A integração com a [API de síntese do ElevenLabs](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)
é **editorial, antes do build**, não uma chamada do celular a cada resposta.
Isso mantém a chave fora do APK/site e evita latência e gasto por tentativa.
O aluno não precisa de conta no ElevenLabs; suas respostas não são enviadas.

1. Na sua conta ElevenLabs, copie o **Voice ID** da voz criada e confirme que
   você tem autorização para usá-la e que a API tem acesso a ela.
2. Em um terminal confiável, configure `ELEVENLABS_API_KEY` e
   `ELEVENLABS_VOICE_ID` como variáveis de ambiente. Não coloque a chave no
   Flutter, no catálogo, em `dart-define`, em comandos salvos no histórico,
   em screenshots ou em commits. Não é necessário fornecê-la no chat.
3. Na raiz do projeto, com Dart/Flutter disponíveis, faça primeiro a prévia:

   ```sh
   dart run tool/generate_feedback_audio.dart --dry-run
   ```

4. Depois de conferir a quantidade de frases/caracteres e os créditos da conta,
   autorize explicitamente as chamadas:

   ```sh
   dart run tool/generate_feedback_audio.dart --generate
   ```

5. Ouça e revise todos os MP3 gerados em `assets/audio_feedback/`, incluindo
   entonação, pronúncia, volume e adequação do humor. Só então execute
   `flutter pub get` e os testes/builds habituais, distribuindo os MP3 junto
   com o app. Limpe as variáveis sensíveis do terminal ao terminar.

O gerador usa `POST /v1/text-to-speech/{voice_id}`, o modelo
`eleven_multilingual_v2`, idioma português e MP3 `mp3_44100_128`. Faz uma
requisição por frase pendente, sem retries automáticos. Recusa redirecionamentos,
respostas não MP3, arquivos acima de 10 MiB e respostas incompletas; aplica
timeout e não registra credenciais nem corpos de erros do provedor.
Uma falha encerra a geração, preservando os arquivos já concluídos.

Arquivos MP3 existentes com cabeçalho reconhecido são ignorados por padrão.
Ao alterar **texto, voz ou modelo**, use
`dart run tool/generate_feedback_audio.dart --generate --force` para substituir
os arquivos — isso volta a consumir créditos. O gerador não mantém fingerprint
da voz/texto nem garante qualidade sonora pela inspeção do cabeçalho.

**Custos e direitos:** ElevenLabs não é uma API ilimitada gratuita; cotas,
vozes disponíveis e licenças dependem do plano. Conforme a
[política de publicação do ElevenLabs](https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform),
o plano gratuito não inclui licença comercial e exige atribuição para
publicação não comercial. Confirme as condições aplicáveis antes de distribuir;
não presuma que a licença open source do player cobre os áudios gerados.
Esta integração não habilita Blaze nem altera o Firebase.

### Ampliar temas e categorias

O catálogo independente `assets/audio_feedback/catalog.json` tem
`schemaVersion: 1` e uma lista `themes`. Cada tema define `id`, `name`,
`description` e `clips`; cada frase define `id`, `category` e `text`.
IDs usam letras minúsculas, números e sublinhado, iniciando por letra, com até
64 caracteres; `off` é reservado. Textos têm no máximo 500 caracteres.
Cada tema deve ter ao menos uma frase de acerto e uma de erro.

Para adicionar um tema, basta cadastrar suas frases e gerar os áudios:
o seletor lê o catálogo, sem lista fixa de temas na interface. Os arquivos
seguem `assets/audio_feedback/<tema>_<frase>.mp3`; caminhos resultantes
duplicados são rejeitados. Não altere os IDs dos cursos ou exercícios.
Novos **eventos**, além de acerto/erro, exigem ampliar `FeedbackCategory`, a
validação do catálogo e o ponto de disparo correspondente, com testes.

A reprodução usa [just_audio](https://pub.dev/packages/just_audio), compatível
com Android, iOS e web. O repositório atualmente contém runners Android e web;
iOS ainda exige seu runner e validação nativa. Ao avançar, abrir o seletor,
sair ou colocar o app em segundo plano, a reação é interrompida.
É possível parar/repetir a reação. Arquivo ausente, erro de reprodução ou
bloqueio de autoplay no navegador mostram uma mensagem sem impedir a aula.
No app instalado, os MP3 empacotados funcionam offline; a limitação de
carregamento inicial da versão web continua valendo.

**Estado desta entrega:** nenhum áudio foi sintetizado sem as credenciais do
proprietário. Até gerar e empacotar os MP3, os temas mostram suas frases por
escrito e informam que o áudio está indisponível.

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
assets/audio_feedback/ Temas, frases e MP3 gerados antes da publicação
lib/models/          Cursos, exercícios, progresso e revisões
lib/data/            Carregamento e validação do catálogo
lib/state/           Regras de aprendizado e coordenação do progresso
lib/services/        Persistência local e Firebase opcional
lib/screens/         Trilha, exercícios, revisão e conta
lib/widgets/         Seletor reutilizável de temas
tool/                Geração editorial de áudio via ElevenLabs
test/                Testes de domínio e widgets
firebase/            Testes das regras Firestore
android/ ios/ web/   Runners Flutter
firestore.rules      Isolamento de usuários e validação de backups
```

## Estado da validação

O ambiente usado para criar esta implementação não tinha `flutter` nem `dart`,
e o download do SDK foi bloqueado pela rede. Os comandos de scaffolding,
resolução de dependências e validação foram tentados, mas os testes Flutter e
os builds **não puderam ser executados localmente**. Não há APK validado
incluído neste repositório. Execute o workflow de CI ou os comandos acima em
um ambiente com Flutter antes de distribuir.