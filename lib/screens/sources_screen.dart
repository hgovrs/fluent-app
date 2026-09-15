import 'package:flutter/material.dart';

import '../data/content_sources.dart';
import '../theme.dart';

class SourcesScreen extends StatefulWidget {
  const SourcesScreen({super.key, this.sourceIds});

  final List<String>? sourceIds;

  @override
  State<SourcesScreen> createState() => _SourcesScreenState();
}

class _SourcesScreenState extends State<SourcesScreen> {
  late final Future<List<ContentSource>> _sources = ContentSource.load();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Fontes e licenças')),
      body: SafeArea(
        child: FutureBuilder<List<ContentSource>>(
          future: _sources,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return const Center(
                child: Text('Não foi possível ler as referências locais.'),
              );
            }
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final sources = snapshot.data!.where(
              (source) =>
                  widget.sourceIds == null ||
                  widget.sourceIds!.contains(source.id),
            );
            return ListView(
              padding: const EdgeInsets.all(24),
              children: [
                const Text(
                  'Os exercícios e resumos do Fluent são originais e estão disponíveis offline. '
                  'Estas são leituras complementares, não livros importados. '
                  'Os links exigem internet; copie o endereço para consultar a fonte.',
                ),
                const SizedBox(height: 12),
                const Text(
                  'Uso pessoal não comercial: respeite atribuição e exceções de cada obra. '
                  'Gratuito ou local não significa livre de direitos. '
                  'Áudios, vídeos e imagens de terceiros podem ter outras licenças.',
                ),
                if (sources.isEmpty)
                  const Padding(
                    padding: EdgeInsets.only(top: 24),
                    child: Text('Esta lição utiliza somente material original.'),
                  ),
                for (final source in sources)
                  Padding(
                    padding: const EdgeInsets.only(top: 20),
                    child: SurfaceCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            source.title,
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 8),
                          Text('${source.authors}\n${source.institution}'),
                          const SizedBox(height: 8),
                          Text(source.description),
                          const SizedBox(height: 8),
                          Text('Licença indicada: ${source.license}'),
                          Text(source.limitations),
                          const SizedBox(height: 8),
                          SelectableText(source.url),
                          if (source.licenseUrl != source.url)
                            SelectableText(source.licenseUrl),
                        ],
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
