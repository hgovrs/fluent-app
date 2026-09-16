import 'dart:async';
import 'dart:convert';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';

/// Optional cloud account. Progress only leaves this device on explicit backup.
class CloudService extends ChangeNotifier {
  CloudService._();

  FirebaseAuth? _auth;
  FirebaseFirestore? _store;
  StreamSubscription<User?>? _subscription;
  Future<UserCredential>? _pendingAuth;
  User? _user;
  bool _busy = false;
  bool _signingOut = false;
  bool _disposed = false;
  int _operation = 0;
  int _session = 0;
  String? _error;

  bool get available => _auth != null && _store != null;
  bool get busy => _busy;
  String? get email => _user?.email;
  bool get signedIn => _user != null;
  String? get error => _error;

  static Future<CloudService> initialize() async {
    final service = CloudService._();
    const apiKey = String.fromEnvironment('FIREBASE_API_KEY');
    const appId = String.fromEnvironment('FIREBASE_APP_ID');
    const senderId = String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
    const projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
    const authDomain = String.fromEnvironment('FIREBASE_AUTH_DOMAIN');
    const bundleId = String.fromEnvironment('IOS_BUNDLE_ID');
    if ([apiKey, appId, senderId, projectId].any((value) => value.isEmpty)) {
      return service;
    }
    try {
      final app = await Firebase.initializeApp(
        options: FirebaseOptions(
          apiKey: apiKey,
          appId: appId,
          messagingSenderId: senderId,
          projectId: projectId,
          authDomain: authDomain.isEmpty
              ? '$projectId.firebaseapp.com'
              : authDomain,
          iosBundleId: bundleId.isEmpty ? null : bundleId,
        ),
      );
      service._auth = FirebaseAuth.instanceFor(app: app);
      service._store = FirebaseFirestore.instanceFor(app: app);
      // No offline write queue: an explicit backup must reach the server.
      service._store!.settings = const Settings(persistenceEnabled: false);
      service._user = service._auth!.currentUser;
      service._subscription = service._auth!.authStateChanges().listen(
        (user) {
          if (service._signingOut) return;
          if (service._user?.uid != user?.uid) service._session++;
          service._user = user;
          service._notify();
        },
        onError: (Object _) {
          service._error =
              'Não foi possível atualizar a conta. Seus dados locais estão seguros.';
          service._notify();
        },
      );
    } catch (_) {
      service._auth = null;
      service._store = null;
      service._user = null;
      service._error =
          'A nuvem está indisponível. Você pode continuar estudando neste aparelho.';
    }
    return service;
  }

  Future<bool> signIn(String email, String password) =>
      _authenticate(email, password, create: false);

  Future<bool> signUp(String email, String password) =>
      _authenticate(email, password, create: true);

  Future<bool> _authenticate(
    String email,
    String password, {
    required bool create,
  }) async {
    final operation = _begin();
    if (operation == null) return false;
    try {
      final pending = create
          ? _auth!.createUserWithEmailAndPassword(
              email: email.trim(),
              password: password,
            )
          : _auth!.signInWithEmailAndPassword(
              email: email.trim(),
              password: password,
            );
      _pendingAuth = pending;
      final credentials = await pending;
      if (!_current(operation)) return false;
      if (_user?.uid != credentials.user?.uid) _session++;
      _user = credentials.user;
      return true;
    } catch (error) {
      _fail(operation, error);
      return false;
    } finally {
      _pendingAuth = null;
      _finish(operation);
    }
  }

  Future<bool> resetPassword(String email) async {
    final operation = _begin();
    if (operation == null) return false;
    try {
      await _auth!.sendPasswordResetEmail(email: email.trim());
      return _current(operation);
    } catch (error) {
      _fail(operation, error);
      return false;
    } finally {
      _finish(operation);
    }
  }

  Future<void> signOut() async {
    if (!available || _disposed || _signingOut) return;
    final operation = ++_operation;
    _session++;
    _signingOut = true;
    _busy = true;
    _error = null;
    _user = null;
    _notify();
    try {
      // Wait for an in-flight sign-in so it cannot reauthenticate after logout.
      try {
        await _pendingAuth;
      } catch (_) {
        // A failed sign-in still needs the requested sign-out to finish.
      }
      await _auth!.signOut();
    } catch (error) {
      _fail(operation, error);
      _user = _auth!.currentUser;
    } finally {
      _signingOut = false;
      _finish(operation);
    }
  }

  Future<bool> backup(Map<String, dynamic> progress) async {
    final operation = _begin(requireUser: true);
    if (operation == null) return false;
    final uid = _auth!.currentUser!.uid;
    final session = _session;
    try {
      final payload = jsonEncode(progress);
      if (payload.length >= 200000) {
        throw const FormatException('Backup too large');
      }
      if (!_sameUser(operation, session, uid)) return false;
      // Bind every request to the captured user, never a later account.
      await _store!.doc('users/$uid/backups/progress').set({
        'schemaVersion': 1,
        'payload': payload,
        'updatedAt': FieldValue.serverTimestamp(),
      });
      return _sameUser(operation, session, uid);
    } catch (error) {
      _fail(operation, error);
      return false;
    } finally {
      _finish(operation);
    }
  }

  Future<Map<String, dynamic>?> restore() async {
    final operation = _begin(requireUser: true);
    if (operation == null) return null;
    final uid = _auth!.currentUser!.uid;
    final session = _session;
    try {
      final snapshot = await _store!
          .doc('users/$uid/backups/progress')
          .get(const GetOptions(source: Source.server));
      if (!_sameUser(operation, session, uid)) return null;
      final data = snapshot.data();
      if (data == null) {
        _error = 'Nenhum backup encontrado para esta conta.';
        return null;
      }
      final payload = data['payload'];
      if (data['schemaVersion'] != 1 ||
          payload is! String ||
          payload.length >= 200000) {
        throw const FormatException('Invalid backup');
      }
      final decoded = jsonDecode(payload);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('Invalid progress');
      }
      return decoded;
    } catch (error) {
      _fail(operation, error);
      return null;
    } finally {
      _finish(operation);
    }
  }

  int? _begin({bool requireUser = false}) {
    if (_disposed || _busy) return null;
    _error = null;
    if (!available) {
      _error =
          'A nuvem não está configurada. Seus dados continuam neste aparelho.';
    } else if (requireUser && _auth!.currentUser == null) {
      _error = 'Entre na sua conta para usar o backup.';
    }
    if (_error != null) {
      _notify();
      return null;
    }
    _busy = true;
    final operation = ++_operation;
    _notify();
    return operation;
  }

  bool _current(int operation) => !_disposed && operation == _operation;

  bool _sameUser(int operation, int session, String uid) =>
      _current(operation) &&
      session == _session &&
      _auth?.currentUser?.uid == uid;

  void _fail(int operation, Object error) {
    if (!_current(operation)) return;
    _error = switch (error) {
      FirebaseAuthException(code: 'invalid-email') =>
        'Digite um endereço de e-mail válido.',
      FirebaseAuthException(code: 'weak-password') =>
        'Use uma senha mais forte, com pelo menos 6 caracteres.',
      FirebaseAuthException(code: 'email-already-in-use') =>
        'Este e-mail já está cadastrado. Entre ou redefina sua senha.',
      FirebaseAuthException(
        code: 'invalid-credential' || 'wrong-password' || 'user-not-found',
      ) =>
        'E-mail ou senha incorretos.',
      FirebaseAuthException(code: 'too-many-requests') =>
        'Muitas tentativas. Aguarde um pouco e tente novamente.',
      FirebaseAuthException(code: 'operation-not-allowed') =>
        'O acesso por e-mail ainda não foi habilitado neste projeto.',
      FirebaseAuthException(code: 'user-disabled') =>
        'Esta conta foi desativada. Entre em contato com o suporte.',
      FirebaseException(code: 'network-request-failed' || 'unavailable') =>
        'Sem conexão com a nuvem. Verifique sua internet e tente novamente.',
      FirebaseException(code: 'permission-denied' || 'unauthenticated') =>
        'Não foi possível acessar o backup. Entre novamente na sua conta.',
      FormatException() =>
        'O backup é inválido ou muito grande. Seus dados locais não foram alterados.',
      _ =>
        'Não foi possível concluir. Tente novamente; seus dados locais estão seguros.',
    };
  }

  void _finish(int operation) {
    if (!_current(operation)) return;
    _busy = false;
    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _operation++;
    _subscription?.cancel();
    super.dispose();
  }
}
