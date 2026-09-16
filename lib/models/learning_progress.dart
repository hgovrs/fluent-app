String calendarDate(DateTime date) =>
    '${date.year.toString().padLeft(4, '0')}-'
    '${date.month.toString().padLeft(2, '0')}-'
    '${date.day.toString().padLeft(2, '0')}';

// UTC here represents calendar components, not a conversion of a local instant.
// Subtracting local durations is incorrect across daylight-saving transitions.
DateTime calendarDay(DateTime date) =>
    DateTime.utc(date.year, date.month, date.day);

DateTime parseCalendarDate(String value) {
  if (!RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value)) {
    throw const FormatException('Data inválida.');
  }
  final date = DateTime.tryParse('${value}T00:00:00Z');
  if (date == null || calendarDate(date) != value) {
    throw const FormatException('Data inválida.');
  }
  return date;
}

int nonnegativeInt(dynamic value, String field) {
  if (value is! int || value < 0 || value > 1000000000) {
    throw FormatException('Valor inválido: $field');
  }
  return value;
}

class ReviewSchedule {
  const ReviewSchedule({
    required this.dueDate,
    required this.intervalDays,
    required this.successCount,
  });

  final String dueDate;
  final int intervalDays;
  final int successCount;

  factory ReviewSchedule.fromJson(Map<String, dynamic> json) {
    final date = json['dueDate'];
    if (date is! String) throw const FormatException('Data inválida.');
    parseCalendarDate(date);
    final interval = nonnegativeInt(json['intervalDays'], 'intervalDays');
    if (interval > 30) throw const FormatException('Intervalo inválido.');
    return ReviewSchedule(
      dueDate: date,
      intervalDays: interval,
      successCount: nonnegativeInt(json['successCount'], 'successCount'),
    );
  }

  Map<String, dynamic> toJson() => {
    'dueDate': dueDate,
    'intervalDays': intervalDays,
    'successCount': successCount,
  };
}

class LearningProgress {
  static const defaultFeedbackVoiceId = 'natasha_caldeirao';

  LearningProgress({
    this.totalXp = 0,
    this.dailyGoal = 30,
    Set<String> completedLessonIds = const {},
    Map<String, int> activity = const {},
    Map<String, ReviewSchedule> reviews = const {},
    this.reviewedCount = 0,
    this.feedbackVoiceId = defaultFeedbackVoiceId,
    DateTime Function()? now,
  }) : completedLessonIds = Set.unmodifiable(completedLessonIds),
       activity = Map.unmodifiable(activity),
       reviews = Map.unmodifiable(reviews),
       _now = now ?? DateTime.now;

  final int totalXp;
  final int dailyGoal;
  final Set<String> completedLessonIds;
  final Map<String, int> activity;
  final Map<String, ReviewSchedule> reviews;
  final int reviewedCount;
  final String feedbackVoiceId;
  final DateTime Function() _now;

  int get dailyXp => activity[calendarDate(_now())] ?? 0;

  int get streak {
    var day = calendarDay(_now());
    if (!activity.containsKey(calendarDate(day))) {
      day = day.subtract(const Duration(days: 1));
    }
    var count = 0;
    while (activity.containsKey(calendarDate(day))) {
      count++;
      day = day.subtract(const Duration(days: 1));
    }
    return count;
  }

  LearningProgress copyWith({
    int? totalXp,
    int? dailyGoal,
    Set<String>? completedLessonIds,
    Map<String, int>? activity,
    Map<String, ReviewSchedule>? reviews,
    int? reviewedCount,
    String? feedbackVoiceId,
  }) => LearningProgress(
    totalXp: totalXp ?? this.totalXp,
    dailyGoal: dailyGoal ?? this.dailyGoal,
    completedLessonIds: completedLessonIds ?? this.completedLessonIds,
    activity: activity ?? this.activity,
    reviews: reviews ?? this.reviews,
    reviewedCount: reviewedCount ?? this.reviewedCount,
    feedbackVoiceId: feedbackVoiceId ?? this.feedbackVoiceId,
    now: _now,
  );

  factory LearningProgress.fromJson(
    Map<String, dynamic> json, {
    DateTime Function()? now,
  }) {
    final completed = json['completedLessonIds'];
    final activityJson = json['activity'];
    final reviewsJson = json['reviews'];
    final feedbackVoiceId =
        json['feedbackVoiceId'] ??
        json['feedbackThemeId'] ??
        defaultFeedbackVoiceId;
    if (feedbackVoiceId is! String ||
        feedbackVoiceId.length > 64 ||
        !RegExp(r'^[a-z][a-z0-9_]*$').hasMatch(feedbackVoiceId)) {
      throw const FormatException('Voz de feedback inválida.');
    }
    if (completed is! List ||
        completed.any((id) => id is! String || id.isEmpty) ||
        activityJson is! Map<String, dynamic> ||
        reviewsJson is! Map<String, dynamic>) {
      throw const FormatException('Progresso inválido.');
    }
    final goal = nonnegativeInt(json['dailyGoal'], 'dailyGoal');
    if (goal < 1 || goal > 1000) {
      throw const FormatException('Meta inválida.');
    }
    final activity = activityJson.map((key, value) {
      parseCalendarDate(key);
      return MapEntry(key, nonnegativeInt(value, 'activity'));
    });
    final reviews = reviewsJson.map((key, value) {
      if (value is! Map<String, dynamic>) {
        throw const FormatException('Revisão inválida.');
      }
      return MapEntry(key, ReviewSchedule.fromJson(value));
    });
    return LearningProgress(
      totalXp: nonnegativeInt(json['totalXp'], 'totalXp'),
      dailyGoal: goal,
      completedLessonIds: completed.cast<String>().toSet(),
      activity: activity,
      reviews: reviews,
      reviewedCount: nonnegativeInt(json['reviewedCount'], 'reviewedCount'),
      feedbackVoiceId: feedbackVoiceId,
      now: now,
    );
  }

  Map<String, dynamic> toJson() => {
    'totalXp': totalXp,
    'dailyGoal': dailyGoal,
    'completedLessonIds': completedLessonIds.toList()..sort(),
    'activity': Map<String, int>.from(activity),
    'reviews': reviews.map((key, value) => MapEntry(key, value.toJson())),
    'reviewedCount': reviewedCount,
    'feedbackVoiceId': feedbackVoiceId,
  };
}
