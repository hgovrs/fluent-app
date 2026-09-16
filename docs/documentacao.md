# Documentação do Fluent 🌱

[Voltar ao README](../README.md)

Os caminhos e comandos deste documento são relativos à raiz do projeto.

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
O texto de apoio acompanha também exercícios isolados na revisão espaçada;
não é necessário ter respondido à pergunta anterior para recuperar a leitura.

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
| [Let's Get to Work! — PCC](https://sites.google.com/pcc.edu/oer-for-esol/home/lets-get-to-work) | Comunicação profissional intermediária | **Licença não verificada**; aquisição bloqueada. |
| [In the Loop — PCC](https://sites.google.com/pcc.edu/oer-for-esol/home/in-the-loop) | Comunicação intermediária superior | **Licença não verificada**; aquisição bloqueada. Nível interno do PCC, não B2 certificado. |
| [Synthesis — PCC](https://openoregon.pressbooks.pub/synthesis/part/part-1/) | Escrita acadêmica avançada | CC BY-NC-SA 4.0 indicada na edição Pressbooks, salvo exceções; não substitui um curso completo C1. |
| [English: skills for learning — Open University](https://www.open.edu/openlearn/education-development/english-skills-learning/content-section-overview) | Leitura e organização da escrita acadêmica | CC BY-NC-SA 4.0 geral, com exceções em Acknowledgements. |

**Limitação desta execução:** o ambiente não conseguiu acessar diretamente
vários sites das editoras (falhas de DNS). A pesquisa de metadados e sumários não
é uma leitura integral de todas as obras. Não se declara download concluído,
auditoria completa de mídia nem reutilização autorizada de arquivos não
inspecionados. O material de prática original funciona independentemente desses
downloads; nenhuma referência inacessível bloqueia o aprendizado.

**Correção da pesquisa anterior:** não foi possível sustentar a atribuição
CC BY-NC-SA a *Let's Get to Work!* e *In the Loop*. As respostas de busca
conflitavam e citavam outros materiais. Ambos permanecem com licença
**não verificada**, mesmo para a aquisição automatizada. Para *Communication
Beginnings*, a licença indicada é **BY-NC**, não BY.

Análise possível a partir dos sumários indexados:

- **BC Reads:** Reader 1 trata de plantas/jardins; 2, vida e poemas de Langston
  Hughes; 3, história/cultura/fauna da Colúmbia Britânica; 4, direitos humanos;
  5, aprendizagem e memória; 6, narrativas digitais. Combinar cada Reader com
  seu Course Pack, objetivos, rubricas e avaliação é mais útil que tratar livros
  numerados como níveis CEFR. Citações literárias e mídias exigem revisão própria.
- **Communication Beginnings:** sete capítulos sobre universidade,
  apresentações, viagens, alimentação, cidade, rotinas/hobbies e trabalho,
  complementando comunicação contextualizada.
- **Synthesis:** processo de escrita, estrutura de ensaios, pesquisa/avaliação
  de fontes, citações, transições e revisão. **OpenLearn** complementa leitura
  ativa, anotações, paráfrase e planejamento acadêmico.
- Os materiais PCC de comunicação incluem recursos separados e links externos;
  não foi confirmado um pacote único completo que funcione offline.

Endereços concretos de descoberta, **não arquivos baixados ou aprovados**:
[Reader 1 XHTML](https://opentextbc.ca/abealfreader1/open/download?type=xhtml),
[Course Pack 1 XHTML](https://opentextbc.ca/abealf1/open/download?type=xhtml),
[livro web PSU](https://pdx.pressbooks.pub/communicationbeginningsanintroductory/),
[Synthesis XHTML](https://openoregon.pressbooks.pub/synthesis/open/download?type=xhtml)
e [OpenLearn imprimível](https://www.open.edu/openlearn/education-development/english-skills-learning/altformat-printable).
XHTML não é PDF/EPUB e não é aceito pelo utilitário; nenhuma URL de exportação
deve ser construída por adivinhação. URLs candidatas de PDF do BC Reads e de
um espelho eCampusOntario também falharam em verificações de acesso por DNS.

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

Nesta execução, `download --allow-noncommercial` retornou **código 1**:
as seis referências ainda não possuem arquivos aprovados no registro. Nenhum
arquivo ou recibo de download bem-sucedido foi criado.

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
   termos e tamanho máximo por arquivo. A documentação oficial consultada lista
   **25 MiB por arquivo, 20 mil arquivos por site e 500 builds/mês** no Free;
   revalidar esses limites antes da migração. Não tratar uma hospedagem pública como
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

## Preparar GIFs de feedback a partir de vídeo

O script editorial `tool/generate_feedback_gifs.py` converte um vídeo local em
`full.gif` e depois divide esse GIF em **trechos temporais**, não em recortes
da imagem. Requer **Python 3 e FFmpeg**, com `ffmpeg` e `ffprobe` no `PATH`
(Ubuntu/Debian: `sudo apt install ffmpeg`; macOS: `brew install ffmpeg`).
O modo de GIFs e a extração WAV não requerem pacotes Python adicionais, serviços
externos ou envio do vídeo. Transcrição e diarização são etapas locais opcionais
com modelos e dependências próprios, descritos abaixo.
Use apenas vídeos próprios ou com autorização para adaptação e distribuição.

Defina `REPO` como o caminho absoluto do seu clone. Para separar um vídeo de
acertos em trechos de 3 segundos:

```sh
REPO="/home/runner/work/fluent-app/fluent-app"
python3 "$REPO/tool/generate_feedback_gifs.py" "/caminho/meu-video.mp4" \
  --output "$REPO/feedback-gifs/acertos" \
  --category correct --segment-duration 3 --fps 10 --width 480
```

Use `--category incorrect` para um vídeo de erros. A categoria é escolhida por
você: o script **não identifica automaticamente** quais cenas são de acerto/erro.
O último trecho pode ser menor; uma sobra menor que um quadro é incorporada ao
trecho anterior. A proporção da imagem é preservada e os GIFs repetem sem áudio.

Para selecionar cenas diferentes do mesmo vídeo, salve um JSON local, por
exemplo em `/tmp/cortes.json`, com tempos em segundos:

```json
[
  {"id": "acerto_01", "category": "correct", "start": 0, "end": 2.5},
  {"id": "erro_01", "category": "incorrect", "start": 4, "end": 6}
]
```

```sh
python3 "$REPO/tool/generate_feedback_gifs.py" "/caminho/meu-video.mp4" \
  --output "$REPO/feedback-gifs/reacoes" --segments "/tmp/cortes.json"
```

Os cortes devem estar dentro da duração do vídeo e durar pelo menos um quadro.
IDs são únicos, começam com letra minúscula ou número e contêm até 80 letras
minúsculas, números, `_` ou `-`; `full` é reservado. Não combine `--segments`
com `--category` ou `--segment-duration`.

Cada execução gera uma **pasta nova** contendo `full.gif`, os GIFs individuais e
`catalog.json`. O catálogo registra `id`, `category`, `start`, `end` e `file`
(relativo à pasta de saída) de cada trecho, além de duração da origem, FPS e
largura. Os tempos são os cortes solicitados; a duração real pode variar pela
precisão dos quadros e pela resolução de centésimos de segundo do formato GIF.
O vídeo original não é alterado, saídas existentes não são sobrescritas e
conversões que falham não publicam uma pasta incompleta.

Prefira vídeos curtos: o GIF completo pode consumir bastante memória e espaço.
Reduza `--width` (16–1920) e `--fps` (1–50) para arquivos menores. O limite é de
1.000 trechos por execução. A pasta `feedback-gifs/` é ignorada pelo Git; se usar
outro destino, mantenha mídias pessoais fora do repositório.

**Este script apenas prepara arquivos.** Ainda não há upload de vídeo nem
exibição de GIFs nas respostas do app. Uma integração futura precisará selecionar
um trecho pela categoria, registrar os assets no Flutter e exibi-los ao corrigir
a questão. O catálogo de GIFs é independente do catálogo de áudio existente.

Testes Python (incluem conversão real de um vídeo sintético quando FFmpeg está
instalado; esses testes de integração são pulados sem ele):

```sh
cd "$REPO"
python3 -m unittest discover -s "$REPO/test" -p '*_test.py' -v
```

### Extrair áudio e texto e reunir trechos por voz

O mesmo script agora aceita etapas opcionais de áudio, sem alterar os comandos
de GIF existentes. Para extrair apenas o áudio:

```sh
python3 "$REPO/tool/generate_feedback_gifs.py" "/caminho/meu-video.mp4" \
  --output "$REPO/feedback-gifs/audio" --audio-only --extract-audio
```

Isso produz `audio.wav` (primeira faixa de áudio, PCM 16 bits, mono, 44,1 kHz)
e `catalog.json`. O vídeo permanece intacto. Vídeos sem áudio falham sem publicar
uma saída parcial. `--audio-only` também aceita arquivos de áudio locais;
não combine essa opção com `--category`, `--segments` ou `--segment-duration`.
Para gerar GIFs **e** áudio, mantenha `--category`/`--segments` e acrescente as
opções de áudio em vez de `--audio-only`.

**Instalação opcional para IA local:** use Python **3.10 ou superior**, FFmpeg e
um ambiente virtual fora do repositório. Os pacotes de IA são grandes e a
diarização instala PyTorch/TorchCodec; confira a compatibilidade destes com o
seu sistema e FFmpeg. A transcrição usa CPU/int8; o pipeline community-1 usa
CPU por padrão. Não é necessário instalar ambos se usar apenas uma etapa:

```sh
python3 -m venv "/tmp/fluent-speech-venv"
. "/tmp/fluent-speech-venv/bin/activate"
python3 -m pip install faster-whisper==1.2.1 pyannote.audio==4.0.7
```

Antes da execução, baixe os modelos completos em pastas **fora do Git**, conforme
as instruções oficiais do [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
e do [pyannote community-1](https://huggingface.co/pyannote/speaker-diarization-community-1).
Exemplo de preparação com o CLI `hf`, instalado por `huggingface-hub` nas
dependências acima:

```sh
hf download Systran/faster-whisper-small --local-dir "/caminho/modelos/whisper-small"
hf auth login
hf download pyannote/speaker-diarization-community-1 \
  --local-dir "/caminho/modelos/community-1"
```

O community-1 requer aceitar os termos de acesso do modelo e autenticar o download
no Hugging Face. Não coloque tokens no código ou nos argumentos do script.
Use somente modelos/configurações de fontes confiáveis: carregar modelos não é
uma operação segura para arquivos arbitrários. A pasta Whisper precisa conter
o modelo no formato CTranslate2; a pasta community-1 deve incluir `config.yaml`
e todos os pesos/subdiretórios, não apenas o arquivo de configuração.

Downloads/instalação são uma preparação separada que usa internet. **Durante o
processamento**, o script exige caminhos locais, configura o Hugging Face em
modo offline e desativa a telemetria do Hugging Face e do pyannote. Não baixa
modelos automaticamente, não envia mídia a serviços externos, não chama
ElevenLabs e não utiliza o pipeline remoto precision-2.

Para extrair áudio, transcrever e separar as vozes automaticamente:

```sh
python3 "$REPO/tool/generate_feedback_gifs.py" "/caminho/meu-video.mp4" \
  --output "$REPO/feedback-gifs/vozes" --audio-only \
  --transcribe-model "/caminho/modelos/whisper-small" --language pt \
  --diarization-model "/caminho/modelos/community-1" \
  --voices-authorized
```

`--transcribe-model` e `--diarization-model` já implicam extração de áudio.
Omitir `--language` ativa a detecção do idioma. Se souber a quantidade de pessoas,
acrescente `--num-speakers 2` à diarização (1–100). A separação agrupa locutores
por semelhança da voz, **não identifica quem são**; os rótulos valem apenas para
aquela execução. Não são inferidos nome, gênero ou identidade real.

Saídas adicionais:

- `transcript.txt` e `transcript.json`: texto completo e segmentos com tempos
  estimados pelo Whisper; não é uma transcrição atribuída a cada locutor.
- `speaker_segments.json`: lista de falas detectadas com `speaker`, `start`, `end`.
- `speakers/speaker_001/clip_0001.wav`, etc.: cortes individuais de cada voz.
- `speakers/speaker_001/combined.wav`, etc.: todos os cortes aproveitáveis dessa
  voz, em ordem cronológica e sem os intervalos de outras vozes/silêncio.
- `catalog.json`: seção `audio` com caminhos relativos, durações, correspondência
  entre rótulos e arquivos, método de separação e avisos.

Os tempos de fala/transcrição são relativos ao início de **`audio.wav`**, que
começa na primeira amostra da faixa selecionada; não se deve presumir alinhamento
com GIFs quando a faixa original tiver atraso. Os WAVs mantêm a taxa de amostragem
e não passam por normalização, redução de ruído ou alteração de timbre.

**Revisão manual ou sem modelo de diarização:** ouça `audio.wav`, ajuste a lista
`speaker_segments.json` ou crie um JSON equivalente:

```json
[
  {"speaker": "voz_a", "start": 0.5, "end": 2.0},
  {"speaker": "voz_b", "start": 2.5, "end": 4.0},
  {"speaker": "voz_a", "start": 4.5, "end": 6.0}
]
```

```sh
python3 "$REPO/tool/generate_feedback_gifs.py" "/caminho/meu-video.mp4" \
  --output "$REPO/feedback-gifs/vozes-revisadas" --audio-only \
  --speaker-segments "/caminho/locutores-revisados.json" --voices-authorized
```

Essa alternativa requer apenas Python/FFmpeg, aceita até 10.000 trechos e 100
locutores e valida os limites contra a duração do áudio extraído. Não combine
`--speaker-segments` com `--diarization-model`. Use sempre uma pasta nova.
Predições automáticas que ultrapassam o início/fim do áudio por preenchimento
das janelas do modelo são recortadas aos limites; previsões inteiramente fora
do áudio são descartadas. O JSON manual continua exigindo limites exatos válidos.

**Sobreposições e limites:** diarização determina *quando* cada voz fala, mas
não separa fisicamente duas vozes simultâneas. Intervalos marcados com mais de um
locutor são **excluídos dos WAVs por voz**, preservados no áudio original e
contabilizados em `excludedOverlapDuration`. Cortes sobrepostos da mesma voz são
unificados para não duplicar amostras. Rótulos sem fala isolada ficam no catálogo
com `file: null`; se não houver falas aproveitáveis, o script emite um aviso.
Música, ruído, vozes muito semelhantes e sobreposições não detectadas podem
contaminar os resultados; transcrição e agrupamento precisam de revisão humana.

**Para ElevenLabs:** `--voices-authorized` confirma que você tem autorização dos
donos das vozes para preparar essas amostras; não constitui comprovação de
consentimento. Use sua própria voz ou obtenha permissão explícita para criação
de voz sintética. Ouça os `combined.wav`, remova trechos incorretos no JSON e
gere novamente antes de enviar manualmente. Confira os requisitos atuais da
modalidade de clonagem e do seu plano no ElevenLabs; o script não garante
aceitação, fidelidade ou duração suficiente das amostras. Não adiciona voz à
conta nem gera clones automaticamente.

Áudio, transcrições e rótulos podem conter dados pessoais. Mantenha todas as
saídas em `feedback-gifs/` (ignorada pelo Git) ou fora do repositório; não
versione nem distribua essas amostras sem autorização.

Os testes de áudio usam mídia sintética e verificam cortes/junção de amostras
reais com FFmpeg. As interfaces de IA são testadas com respostas simuladas;
a qualidade e a execução dos modelos completos precisam ser validadas no seu
ambiente com os modelos instalados.

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
   Se várias questões usam a mesma leitura, coloque o texto em `readingPassage`
   na lição. O carregador associa esse contexto a cada exercício, inclusive
   quando ele aparece sozinho na revisão espaçada. Não deixe perguntas
   dependentes de textos presentes apenas em outro exercício.
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
docs/                Documentação do projeto
assets/courses/       Catálogo e conteúdo original empacotado
assets/content/       Registro de fontes, licenças e downloads revisados
assets/audio_feedback/ Temas, frases e MP3 gerados antes da publicação
content-cache/        Livros pessoais e recibos locais (ignorado pelo Git)
lib/models/          Cursos, exercícios, progresso e revisões
lib/data/            Carregamento e validação do catálogo
lib/state/           Regras de aprendizado e coordenação do progresso
lib/services/        Persistência local e Firebase opcional
lib/screens/         Trilha, exercícios, revisão e conta
test/                Testes de domínio e widgets
lib/widgets/         Seletor reutilizável de temas
tool/                Aquisição editorial de fontes e geração de áudio via ElevenLabs, fora do runtime
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

Resultado disponível: **34 testes do utilitário passaram**; depois disso, apenas
o diretório temporário dos testes foi trocado para o padrão do sistema, sem nova
execução. A análise CodeQL de Python encontrou **zero alertas**. A ferramenta
automática de revisão de código não estava instalada; isso não equivale a uma
revisão automática aprovada nem valida o runtime Flutter.
A revisão estática adicional identificou questões que perdiam o texto de apoio
na revisão espaçada; isso foi corrigido com `readingPassage`/`Exercise.context`,
com testes de regressão adicionados. A revisão da correção não apontou novos
problemas relevantes, mas esses testes Flutter continuam sem execução.