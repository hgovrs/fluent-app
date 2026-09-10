import 'package:flutter/material.dart';

import '../services/cloud_service.dart';
import '../state/learning_controller.dart';
import '../theme.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key, required this.controller, required this.cloud});

  final LearningController controller;
  final CloudService cloud;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _createAccount = false;
  bool _hidePassword = true;
  bool _working = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  Future<void> _authenticate() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _working = true);
    try {
      final success = _createAccount
          ? await widget.cloud.signUp(_email.text.trim(), _password.text)
          : await widget.cloud.signIn(_email.text.trim(), _password.text);
      if (success) {
        _password.clear();
        _message('Conta conectada. Você escolhe quando salvar seu progresso na nuvem.');
      }
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _resetPassword() async {
    if (!_email.text.contains('@')) {
      _message('Digite seu e-mail para receber o link de recuperação.');
      return;
    }
    setState(() => _working = true);
    try {
      final success = await widget.cloud.resetPassword(_email.text.trim());
      if (success) _message('Se houver uma conta para este e-mail, você receberá as instruções.');
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  Future<void> _sync({required bool restore}) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(restore ? 'Trazer progresso da nuvem?' : 'Salvar nesta conta?'),
        content: Text(restore
            ? 'O backup de ${widget.cloud.email} será combinado com o progresso deste dispositivo. Nada é enviado automaticamente.'
            : 'O progresso deste dispositivo será salvo em ${widget.cloud.email}, substituindo o backup anterior desta conta. Em aparelhos compartilhados, confira a conta antes de continuar.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancelar')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Confirmar')),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _working = true);
    try {
      if (restore) {
        final data = await widget.cloud.restore();
        if (data != null) {
          await widget.controller.mergeRemote(data);
          _message(widget.controller.storageError ?? 'Progresso recuperado.');
        } else if (widget.cloud.error == null) {
          _message('Esta conta ainda não tem um backup.');
        }
      } else {
        final success = await widget.cloud.backup(widget.controller.exportProgress());
        if (success) _message('Backup salvo na sua conta.');
      }
    } catch (_) {
      _message('Não foi possível recuperar este backup. Seu progresso local foi mantido.');
    } finally {
      if (mounted) setState(() => _working = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.cloud,
      builder: (context, _) {
        final progress = widget.controller.progress;
        final cloud = widget.cloud;
        final busy = _working || cloud.busy;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Seu espaço.', style: Theme.of(context).textTheme.headlineLarge),
            const SizedBox(height: 8),
            const Text('Pequenos hábitos, grandes descobertas.'),
            const SizedBox(height: 24),
            SurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CircleAvatar(radius: 30, backgroundColor: mint,
                      child: Icon(Icons.spa_rounded, color: green, size: 34)),
                  const SizedBox(height: 16),
                  Text('Aprendiz de novos mundos', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 18),
                  Wrap(
                    spacing: 24, runSpacing: 16,
                    children: [
                      _stat(context, '${progress.totalXp}', 'XP no curso'),
                      _stat(context, '${progress.completedLessonIds.length}', 'lições concluídas'),
                      _stat(context, '${progress.reviewedCount}', 'revisões feitas'),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            SurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('No seu ritmo', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  const Text('Escolha sua meta diária. Você pode mudar quando quiser.'),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final goal in [10, 20, 40])
                        ChoiceChip(
                          label: Text('$goal XP'),
                          selected: progress.dailyGoal == goal,
                          onSelected: (_) => widget.controller.setDailyGoal(goal),
                        ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  DropdownButtonFormField<String>(
                    initialValue: widget.controller.course.id,
                    decoration: const InputDecoration(labelText: 'Idioma em prática'),
                    isExpanded: true,
                    items: [
                      for (final course in widget.controller.courses)
                        DropdownMenuItem(value: course.id, child: Text('${course.title} · ${course.level}')),
                    ],
                    onChanged: (id) {
                      if (id != null) widget.controller.selectCourse(id);
                    },
                  ),
                  const SizedBox(height: 10),
                  const Text('Primeiro destino: inglês. A estrutura já está preparada para novos cursos.'),
                ],
              ),
            ),
            const SizedBox(height: 20),
            SurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Icon(cloud.signedIn ? Icons.cloud_done_outlined : Icons.cloud_outlined, color: green),
                    const SizedBox(width: 10),
                    Expanded(child: Text('Seu progresso, com você', style: Theme.of(context).textTheme.titleLarge)),
                  ]),
                  const SizedBox(height: 12),
                  const Text('As lições funcionam sem conta e sem internet. Uma conta é opcional para guardar um backup e levá-lo a outro aparelho.'),
                  const SizedBox(height: 16),
                  if (!cloud.available)
                    const SurfaceCard(
                      color: mint,
                      child: Text('Modo local ativo. O Firebase ainda não foi configurado nesta versão. Seu progresso fica salvo neste dispositivo.'),
                    )
                  else if (cloud.signedIn) ...[
                    Text(cloud.email ?? 'Conta conectada', style: const TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 14),
                    FilledButton.icon(
                      onPressed: busy ? null : () => _sync(restore: false),
                      icon: const Icon(Icons.cloud_upload_outlined),
                      label: const Text('Salvar backup'),
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: busy ? null : () => _sync(restore: true),
                      icon: const Icon(Icons.cloud_download_outlined),
                      label: const Text('Recuperar da nuvem'),
                    ),
                    TextButton(
                      onPressed: busy ? null : () async {
                        await cloud.signOut();
                        if (!cloud.signedIn) {
                          _message('Conta desconectada. O progresso local continua neste aparelho.');
                        }
                      },
                      child: const Text('Sair da conta'),
                    ),
                  ] else
                    Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          TextFormField(
                            controller: _email,
                            enabled: !busy,
                            keyboardType: TextInputType.emailAddress,
                            autofillHints: const [AutofillHints.email],
                            decoration: const InputDecoration(labelText: 'E-mail'),
                            validator: (value) => value != null && RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(value.trim())
                                ? null : 'Digite um e-mail válido.',
                          ),
                          const SizedBox(height: 12),
                          TextFormField(
                            controller: _password,
                            enabled: !busy,
                            obscureText: _hidePassword,
                            autocorrect: false,
                            enableSuggestions: false,
                            autofillHints: [_createAccount ? AutofillHints.newPassword : AutofillHints.password],
                            decoration: InputDecoration(
                              labelText: 'Senha',
                              helperText: _createAccount ? 'Use pelo menos 8 caracteres.' : null,
                              suffixIcon: IconButton(
                                tooltip: _hidePassword ? 'Mostrar senha' : 'Ocultar senha',
                                onPressed: () => setState(() => _hidePassword = !_hidePassword),
                                icon: Icon(_hidePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                              ),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) return 'Digite sua senha.';
                              if (_createAccount && value.length < 8) return 'Use pelo menos 8 caracteres.';
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          FilledButton(
                            onPressed: busy ? null : _authenticate,
                            child: Text(busy ? 'Conectando…' : _createAccount ? 'Criar conta gratuita' : 'Entrar'),
                          ),
                          TextButton(
                            onPressed: busy ? null : () => setState(() => _createAccount = !_createAccount),
                            child: Text(_createAccount ? 'Já tenho uma conta' : 'Quero criar uma conta'),
                          ),
                          if (!_createAccount)
                            TextButton(onPressed: busy ? null : _resetPassword, child: const Text('Esqueci minha senha')),
                          const Text('Ao criar uma conta, seu e-mail é enviado ao Firebase para autenticação. Apenas o backup que você solicitar será enviado à nuvem.'),
                        ],
                      ),
                    ),
                  if (busy) ...[
                    const SizedBox(height: 12),
                    const LinearProgressIndicator(semanticsLabel: 'Conectando ao Firebase'),
                  ],
                  if (cloud.error != null) ...[
                    const SizedBox(height: 12),
                    Semantics(liveRegion: true, child: Text(cloud.error!, style: const TextStyle(color: Color(0xFFAC3025)))),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 24),
            const Text('Feito para aprender, não para competir.',
                style: TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            const Text('Sem anúncios, assinatura, ranking ou limite de vidas. Seus dados locais permanecem neste aparelho ao sair da conta; limpar os dados do app os remove.'),
          ],
        );
      },
    );
  }

  Widget _stat(BuildContext context, String value, String label) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(value, style: Theme.of(context).textTheme.headlineMedium),
      Text(label),
    ],
  );
}
