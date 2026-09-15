import 'dart:math' as math;

import 'package:flutter/foundation.dart';

import '../models/course.dart';
import '../models/feedback_catalog.dart';
import '../models/learning_progress.dart';
import '../services/progress_store.dart';

class LearningController extends ChangeNotifier {
  LearningController({
    required List<Course> courses,
    required ProgressStore store,
    FeedbackCatalog? feedbackCatalog,
    DateTime Function()? now,
  })  : courses = List.unmodifiable(courses),
        feedbackCatalog = feedbackCatalog ?? FeedbackCatalog([]),
        _store = store,
        _now = now ?? DateTime.now {
    if (courses.isEmpty ||
        courses.map((course) => course.id).toSet().length != courses.length) {
      throw ArgumentError('É necessário um catálogo com IDs únicos.');
    }
    _selectedCourseId = courses.first.id;
    for (final course in courses) {
      _progress[course.id] = LearningProgress(now: _now);
    }
  }

  final List<Course> courses;
  final FeedbackCatalog feedbackCatalog;
  final ProgressStore _store;
  final DateTime Function() _now;
  final Map<String, LearningProgress> _progress = {};
  late String _selectedCourseId;
  String? storageError;
  bool _disposed = false;

  Course get course =>
      courses.firstWhere((course) => course.id == _selectedCourseId);
  LearningProgress get progress => _progress[_selectedCourseId]!;
  bool get goalReached => progress.dailyXp >= progress.dailyGoal;
  FeedbackTheme? get feedbackTheme =>
      feedbackCatalog.theme(progress.feedbackThemeId);
  String get feedbackThemeId => feedbackTheme?.id ?? FeedbackCatalog.off;

  bool isCompleted(Lesson lesson) =>
      course.lessons.any((item) => item.id == lesson.id) &&
      progress.completedLessonIds.contains(lesson.id);

  bool isUnlocked(Lesson lesson) {
    final lessons = course.lessons;
    final index = lessons.indexWhere((item) => item.id == lesson.id);
    return index >= 0 &&
        (index == 0 || isCompleted(lessons[index - 1]));
  }

  Lesson? get nextLesson {
    for (final lesson in course.lessons) {
      if (!isCompleted(lesson) && isUnlocked(lesson)) return lesson;
    }
    return null;
  }

  List<Exercise> get dueExercises {
    final today = calendarDate(_now());
    final result = course.lessons
        .expand((lesson) => lesson.exercises)
        .where((exercise) {
      final review = progress.reviews[exercise.id];
      return review != null && review.dueDate.compareTo(today) <= 0;
    }).toList();
    result.sort((a, b) {
      final order = progress.reviews[a.id]!.dueDate
          .compareTo(progress.reviews[b.id]!.dueDate);
      return order == 0 ? a.id.compareTo(b.id) : order;
    });
    return List.unmodifiable(result);
  }

  Future<void> load() async {
    try {
      final saved = await _store.load();
      if (saved != null) {
        final parsed = _parseEnvelope(saved);
        _progress.addAll(parsed);
        final selected = saved['selectedCourseId'];
        if (selected is String && _progress.containsKey(selected)) {
          _selectedCourseId = selected;
        }
      }
      storageError = null;
    } catch (_) {
      storageError =
          'Não foi possível ler o progresso salvo. Você pode continuar offline.';
    }
    _notify();
  }

  Future<void> completeLesson(
      Lesson lesson, Map<String, bool> results) async {
    final matches = course.lessons.where((item) => item.id == lesson.id);
    if (matches.isEmpty || !isUnlocked(matches.first)) {
      throw ArgumentError('Lição indisponível.');
    }
    final canonical = matches.first;
    final ids = canonical.exercises.map((item) => item.id).toSet();
    if (results.length != ids.length ||
        !ids.every(results.containsKey)) {
      throw ArgumentError('Responda todos os exercícios da lição.');
    }
    final firstCompletion = !isCompleted(canonical);
    final xp = firstCompletion
        ? 20 + results.values.where((correct) => correct).length * 10
        : 0;
    final currentDay = calendarDay(_now());
    final today = calendarDate(currentDay);
    final reviews = Map<String, ReviewSchedule>.from(progress.reviews);
    for (final exercise in canonical.exercises) {
      if (!results[exercise.id]!) {
        reviews[exercise.id] = ReviewSchedule(
            dueDate: today, intervalDays: 0, successCount: 0);
      } else if (!reviews.containsKey(exercise.id)) {
        reviews[exercise.id] = ReviewSchedule(
          dueDate: calendarDate(currentDay.add(const Duration(days: 1))),
          intervalDays: 1,
          successCount: 0,
        );
      }
    }
    _progress[_selectedCourseId] = progress.copyWith(
      totalXp: progress.totalXp + xp,
      completedLessonIds: {...progress.completedLessonIds, canonical.id},
      activity: {
        ...progress.activity,
        today: (progress.activity[today] ?? 0) + xp,
      },
      reviews: reviews,
    );
    await _persist();
  }

  Future<void> completeReview(Map<String, bool> results) async {
    final due = dueExercises.map((exercise) => exercise.id).toSet();
    if (results.keys.any((id) => !due.contains(id))) {
      throw ArgumentError('A revisão contém exercícios que não estão pendentes.');
    }
    if (results.isEmpty) return;
    final currentDay = calendarDay(_now());
    final today = calendarDate(currentDay);
    final reviews = Map<String, ReviewSchedule>.from(progress.reviews);
    const intervals = [1, 3, 7, 14, 30];
    for (final entry in results.entries) {
      final previous = reviews[entry.key]!;
      final successCount = entry.value ? previous.successCount + 1 : 0;
      // A failed review returns tomorrow, rather than enabling an endless
      // same-day queue; mistakes in a new lesson remain due immediately.
      final interval = entry.value
          ? intervals[math.min(successCount - 1, intervals.length - 1)]
          : 1;
      reviews[entry.key] = ReviewSchedule(
        dueDate: calendarDate(currentDay.add(Duration(days: interval))),
        intervalDays: interval,
        successCount: successCount,
      );
    }
    _progress[_selectedCourseId] = progress.copyWith(
      reviewedCount: progress.reviewedCount + results.length,
      activity: {
        ...progress.activity,
        today: progress.activity[today] ?? 0,
      },
      reviews: reviews,
    );
    await _persist();
  }

  Future<void> setDailyGoal(int goal) async {
    if (goal < 1 || goal > 1000) {
      throw ArgumentError.value(goal, 'goal', 'Use uma meta de 1 a 1000 XP.');
    }
    _progress[_selectedCourseId] = progress.copyWith(dailyGoal: goal);
    await _persist();
  }

  Future<void> selectCourse(String id) async {
    if (!_progress.containsKey(id)) throw ArgumentError('Curso desconhecido.');
    _selectedCourseId = id;
    await _persist();
  }

  Future<void> setFeedbackTheme(String id) async {
    if (id != FeedbackCatalog.off && feedbackCatalog.theme(id) == null) {
      throw ArgumentError('Tema de feedback desconhecido.');
    }
    _progress[_selectedCourseId] = progress.copyWith(feedbackThemeId: id);
    await _persist();
  }

  Map<String, dynamic> exportProgress() => {
        'schemaVersion': 1,
        'selectedCourseId': _selectedCourseId,
        'courses': _progress.map((key, value) => MapEntry(key, value.toJson())),
      };

  Future<void> mergeRemote(Map<String, dynamic> remote) async {
    final parsed = _parseEnvelope(remote);
    for (final entry in parsed.entries) {
      final local = _progress[entry.key]!;
      final incoming = entry.value;
      final activity = Map<String, int>.from(local.activity);
      for (final day in incoming.activity.entries) {
        activity[day.key] = math.max(activity[day.key] ?? 0, day.value);
      }
      final reviews = Map<String, ReviewSchedule>.from(local.reviews);
      for (final review in incoming.reviews.entries) {
        final existing = reviews[review.key];
        if (existing == null ||
            review.value.dueDate.compareTo(existing.dueDate) < 0) {
          reviews[review.key] = review.value;
        }
      }
      _progress[entry.key] = local.copyWith(
        totalXp: math.max(local.totalXp, incoming.totalXp),
        dailyGoal: incoming.dailyGoal,
        completedLessonIds: {
          ...local.completedLessonIds,
          ...incoming.completedLessonIds,
        },
        activity: activity,
        reviews: reviews,
        reviewedCount: math.max(local.reviewedCount, incoming.reviewedCount),
      );
    }
    await _persist();
  }

  Map<String, LearningProgress> _parseEnvelope(Map<String, dynamic> data) {
    final savedCourses = data['courses'];
    if (data['schemaVersion'] is! int ||
        data['schemaVersion'] != 1 ||
        data['selectedCourseId'] is! String ||
        savedCourses is! Map<String, dynamic>) {
      throw const FormatException('Versão ou formato de progresso inválido.');
    }
    final parsed = <String, LearningProgress>{};
    for (final course in courses) {
      final json = savedCourses[course.id];
      if (json == null) continue;
      if (json is! Map<String, dynamic>) {
        throw const FormatException('Progresso de curso inválido.');
      }
      final value = LearningProgress.fromJson(json, now: _now);
      final lessonIds = course.lessons.map((lesson) => lesson.id).toSet();
      final exerciseIds = course.lessons
          .expand((lesson) => lesson.exercises)
          .map((exercise) => exercise.id)
          .toSet();
      if (!lessonIds.containsAll(value.completedLessonIds) ||
          value.reviews.keys.any((id) => !exerciseIds.contains(id))) {
        throw const FormatException('Conteúdo salvo desconhecido.');
      }
      parsed[course.id] = value;
    }
    return parsed;
  }

  Future<void> _persist() async {
    _notify();
    try {
      await _store.save(exportProgress());
      storageError = null;
    } catch (_) {
      storageError =
          'Seu progresso está nesta sessão, mas não pôde ser salvo no aparelho.';
    }
    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
