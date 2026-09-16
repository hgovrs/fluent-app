import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class ProgressStore {
  ProgressStore({
    Future<String?> Function()? read,
    Future<bool> Function(String value)? write,
  }) : _read = read ?? _readPreferences,
       _write = write ?? _writePreferences;

  static const storageKey = 'fluent.learning.v1';
  final Future<String?> Function() _read;
  final Future<bool> Function(String value) _write;
  Future<void> _pending = Future<void>.value();

  static Future<String?> _readPreferences() async =>
      (await SharedPreferences.getInstance()).getString(storageKey);

  static Future<bool> _writePreferences(String value) async =>
      (await SharedPreferences.getInstance()).setString(storageKey, value);

  Future<Map<String, dynamic>?> load() async {
    final raw = await _read();
    if (raw == null) return null;
    final decoded = jsonDecode(raw);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Formato de progresso inválido.');
    }
    return decoded;
  }

  Future<void> save(Map<String, dynamic> progress) {
    final encoded = jsonEncode(progress);
    final next = _pending.then((_) async {
      if (!await _write(encoded)) {
        throw StateError('Não foi possível salvar o progresso.');
      }
    });
    // A failed write must not poison subsequent writes.
    _pending = next.then<void>((_) {}, onError: (Object _, StackTrace _) {});
    return next;
  }
}
