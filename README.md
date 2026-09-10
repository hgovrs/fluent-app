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
- XP, meta diária configurável, sequência de dias e progresso por curso.
- Revisão espaçada de exercícios estudados, incluindo erros.
- Persistência local e recuperação de falhas de armazenamento.
- Conta opcional com e-mail/senha, recuperação de senha e backup privado no
  Cloud Firestore. Nenhum envio automático do progresso.
- Layout adaptável, sem fontes, imagens ou APIs de IA pagas.
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
lib/models/          Cursos, exercícios, progresso e revisões
lib/data/            Carregamento e validação do catálogo
lib/state/           Regras de aprendizado e coordenação do progresso
lib/services/        Persistência local e Firebase opcional
lib/screens/         Trilha, exercícios, revisão e conta
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