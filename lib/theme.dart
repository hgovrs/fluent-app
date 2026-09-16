import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const kBackgroundDark = Color(0xFF0D0D0D);
const kBrandPurple = Color(0xFF6064A6);
const kBrandPurpleLight = Color(0xFF9195D9);
// Reserved for solid logo intersections, never for surfaces or blending.
const kBrandPurpleDeep = Color(0xFF363A8D);
const kBrandCoral = Color(0xFFF27166);
const kBrandCoralLight = Color(0xFFF28E85);
const kTextPrimary = Color(0xFFFFFFFF);
const kTextSecondary = Color.fromRGBO(255, 255, 255, 0.70);
const kTextHint = Color.fromRGBO(255, 255, 255, 0.60);
const kTextPlaceholder = Color.fromRGBO(255, 255, 255, 0.20);
const kTextChip = Color.fromRGBO(255, 255, 255, 0.90);
const kError = Color(0xFFE57373); // Colors.red.shade300.
const kTransparent = Color(0x000D0D0D);

const kSurfacePurple = Color.fromRGBO(96, 100, 166, 0.15);
const kSurfacePurpleRaised = Color.fromRGBO(96, 100, 166, 0.18);
const kSurfaceBorder = Color.fromRGBO(145, 149, 217, 0.35);
const kFieldBorder = Color.fromRGBO(96, 100, 166, 0.30);
const kIconMuted = Color.fromRGBO(145, 149, 217, 0.60);
const kPurpleGlow = Color.fromRGBO(96, 100, 166, 0.30);
const kCoralSurface = Color.fromRGBO(242, 113, 102, 0.15);
const kCoralBorder = Color.fromRGBO(242, 142, 133, 0.35);
const kImageVeil = Color.fromRGBO(13, 13, 13, 0.70);

// Opaque backing keeps menus and overlays from showing the content below them.
final kOverlaySurface = Color.alphaBlend(kSurfacePurpleRaised, kBackgroundDark);

const kFontBody = 'Tech';
const kFontBrand = 'Genhead';
const kRadiusIcon = 10.0;
const kRadiusSmall = 12.0;
const kRadius = 16.0;
const kRadiusPill = 999.0;
const kBorderWidth = 0.8;
const kCardRadius = BorderRadius.all(Radius.circular(kRadius));
const kSmallRadius = BorderRadius.all(Radius.circular(kRadiusSmall));
const kIconRadius = BorderRadius.all(Radius.circular(kRadiusIcon));
const kPillRadius = BorderRadius.all(Radius.circular(kRadiusPill));
const kChipPadding = EdgeInsets.symmetric(horizontal: 10, vertical: 5);
const kIconPadding = EdgeInsets.all(8);
const kIconSize = 20.0;

const kPrimaryGradient = LinearGradient(
  colors: [kBrandPurple, kBrandPurpleLight],
  begin: Alignment.centerLeft,
  end: Alignment.centerRight,
);
const kPrimaryShadow = BoxShadow(
  color: kPurpleGlow,
  blurRadius: 16,
  offset: Offset(0, 6),
);
const kImageOverlayGradient = LinearGradient(
  colors: [kTransparent, kBackgroundDark],
  begin: Alignment.topCenter,
  end: Alignment.bottomCenter,
);
const kBrandHeadlineStyle = TextStyle(
  fontFamily: kFontBrand,
  fontSize: 24,
  fontWeight: FontWeight.w700,
  height: 1.25,
  color: kTextPrimary,
);
const kButtonTextStyle = TextStyle(
  fontFamily: kFontBody,
  fontSize: 16,
  fontWeight: FontWeight.w700,
);
const kChipTextStyle = TextStyle(
  fontFamily: kFontBody,
  fontSize: 11,
  fontWeight: FontWeight.w600,
  color: kTextChip,
);
const kSelectedChipTextStyle = TextStyle(
  fontFamily: kFontBody,
  fontSize: 11,
  fontWeight: FontWeight.w600,
  color: kBrandPurpleLight,
);
const kSecondaryTextStyle = TextStyle(
  fontFamily: kFontBody,
  fontSize: 14,
  height: 1.45,
  color: kTextSecondary,
);
const kFieldShape = OutlineInputBorder(
  borderRadius: kSmallRadius,
  borderSide: BorderSide(color: kFieldBorder, width: kBorderWidth),
);
const kSurfaceShape = RoundedRectangleBorder(
  borderRadius: kCardRadius,
  side: BorderSide(color: kSurfaceBorder, width: kBorderWidth),
);

final fluentTheme = ThemeData(
  useMaterial3: true,
  brightness: Brightness.dark,
  fontFamily: kFontBody,
  scaffoldBackgroundColor: kBackgroundDark,
  canvasColor: kBackgroundDark,
  shadowColor: kPurpleGlow,
  dividerColor: kSurfaceBorder,
  disabledColor: kTextHint,
  hoverColor: kSurfacePurple,
  focusColor: kSurfacePurpleRaised,
  highlightColor: kSurfacePurple,
  splashColor: kSurfacePurpleRaised,
  applyElevationOverlayColor: false,
  colorScheme: const ColorScheme(
    brightness: Brightness.dark,
    primary: kBrandPurple,
    onPrimary: kTextPrimary,
    primaryContainer: kSurfacePurpleRaised,
    onPrimaryContainer: kTextPrimary,
    primaryFixed: kSurfacePurpleRaised,
    primaryFixedDim: kSurfacePurple,
    onPrimaryFixed: kTextPrimary,
    onPrimaryFixedVariant: kTextSecondary,
    secondary: kBrandPurpleLight,
    onSecondary: kBackgroundDark,
    secondaryContainer: kSurfacePurpleRaised,
    onSecondaryContainer: kBrandPurpleLight,
    secondaryFixed: kSurfacePurpleRaised,
    secondaryFixedDim: kSurfacePurple,
    onSecondaryFixed: kTextPrimary,
    onSecondaryFixedVariant: kTextSecondary,
    tertiary: kBrandCoral,
    onTertiary: kBackgroundDark,
    tertiaryContainer: kCoralSurface,
    onTertiaryContainer: kTextPrimary,
    tertiaryFixed: kCoralSurface,
    tertiaryFixedDim: kCoralSurface,
    onTertiaryFixed: kTextPrimary,
    onTertiaryFixedVariant: kTextSecondary,
    error: kError,
    onError: kBackgroundDark,
    errorContainer: kCoralSurface,
    onErrorContainer: kError,
    surface: kBackgroundDark,
    onSurface: kTextPrimary,
    onSurfaceVariant: kTextSecondary,
    surfaceDim: kBackgroundDark,
    surfaceBright: kSurfacePurpleRaised,
    surfaceContainerLowest: kBackgroundDark,
    surfaceContainerLow: kSurfacePurple,
    surfaceContainer: kSurfacePurple,
    surfaceContainerHigh: kSurfacePurpleRaised,
    surfaceContainerHighest: kSurfacePurpleRaised,
    outline: kSurfaceBorder,
    outlineVariant: kFieldBorder,
    shadow: kPurpleGlow,
    scrim: kImageVeil,
    inverseSurface: kSurfacePurpleRaised,
    onInverseSurface: kTextPrimary,
    inversePrimary: kBrandPurpleLight,
    surfaceTint: kTransparent,
  ),
  appBarTheme: const AppBarTheme(
    backgroundColor: kBackgroundDark,
    foregroundColor: kTextPrimary,
    surfaceTintColor: kTransparent,
    centerTitle: false,
    elevation: 0,
    scrolledUnderElevation: 0,
    iconTheme: IconThemeData(color: kBrandPurpleLight, size: kIconSize),
    titleTextStyle: TextStyle(
      fontFamily: kFontBody,
      fontSize: 20,
      fontWeight: FontWeight.w700,
      color: kTextPrimary,
    ),
    systemOverlayStyle: SystemUiOverlayStyle(
      statusBarColor: kBackgroundDark,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
      systemNavigationBarColor: kBackgroundDark,
      systemNavigationBarDividerColor: kBackgroundDark,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  ),
  textTheme: const TextTheme(
    headlineLarge: TextStyle(
      fontSize: 24,
      height: 1.25,
      fontWeight: FontWeight.w700,
      color: kTextPrimary,
    ),
    headlineMedium: TextStyle(
      fontSize: 22,
      height: 1.3,
      fontWeight: FontWeight.w700,
      color: kTextPrimary,
    ),
    headlineSmall: TextStyle(
      fontSize: 20,
      height: 1.3,
      fontWeight: FontWeight.w700,
      color: kTextPrimary,
    ),
    titleLarge: TextStyle(
      fontSize: 20,
      fontWeight: FontWeight.w700,
      color: kTextPrimary,
    ),
    titleMedium: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w700,
      color: kTextPrimary,
    ),
    titleSmall: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w600,
      color: kTextPrimary,
    ),
    bodyLarge: TextStyle(fontSize: 16, height: 1.5, color: kTextPrimary),
    bodyMedium: TextStyle(fontSize: 14, height: 1.45, color: kTextPrimary),
    bodySmall: TextStyle(fontSize: 12, height: 1.4, color: kTextSecondary),
    labelLarge: kButtonTextStyle,
    labelMedium: TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.w600,
      color: kTextSecondary,
    ),
    labelSmall: kChipTextStyle,
  ),
  iconTheme: const IconThemeData(color: kBrandPurpleLight, size: kIconSize),
  elevatedButtonTheme: ElevatedButtonThemeData(
    style:
        ElevatedButton.styleFrom(
          minimumSize: const Size(48, 54),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          backgroundColor: kTransparent,
          disabledBackgroundColor: kTransparent,
          foregroundColor: kTextPrimary,
          disabledForegroundColor: kTextHint,
          shadowColor: kTransparent,
          surfaceTintColor: kTransparent,
          elevation: 0,
          textStyle: kButtonTextStyle,
          shape: const RoundedRectangleBorder(borderRadius: kCardRadius),
        ).copyWith(
          elevation: const WidgetStatePropertyAll(0),
          overlayColor: const WidgetStatePropertyAll(kSurfacePurpleRaised),
        ),
  ),
  outlinedButtonTheme: OutlinedButtonThemeData(
    style: OutlinedButton.styleFrom(
      minimumSize: const Size(48, 48),
      foregroundColor: kBrandPurpleLight,
      disabledForegroundColor: kTextHint,
      backgroundColor: kSurfacePurple,
      disabledBackgroundColor: kSurfacePurple,
      side: const BorderSide(color: kSurfaceBorder, width: kBorderWidth),
      textStyle: kButtonTextStyle,
      shape: const RoundedRectangleBorder(borderRadius: kCardRadius),
    ),
  ),
  textButtonTheme: TextButtonThemeData(
    style: TextButton.styleFrom(
      foregroundColor: kBrandPurpleLight,
      disabledForegroundColor: kTextHint,
      textStyle: kButtonTextStyle,
      shape: const RoundedRectangleBorder(borderRadius: kCardRadius),
    ),
  ),
  iconButtonTheme: IconButtonThemeData(
    style: IconButton.styleFrom(
      foregroundColor: kIconMuted,
      disabledForegroundColor: kTextHint,
      backgroundColor: kSurfacePurple,
      padding: kIconPadding,
      iconSize: kIconSize,
      shape: const RoundedRectangleBorder(borderRadius: kIconRadius),
    ),
  ),
  inputDecorationTheme: const InputDecorationTheme(
    filled: true,
    fillColor: kSurfacePurple,
    labelStyle: TextStyle(color: kTextHint),
    floatingLabelStyle: TextStyle(color: kTextHint),
    hintStyle: TextStyle(color: kTextPlaceholder),
    helperStyle: TextStyle(color: kTextHint, fontSize: 12),
    errorStyle: TextStyle(color: kError, fontSize: 12),
    prefixIconColor: kBrandPurpleLight,
    suffixIconColor: kBrandPurpleLight,
    border: kFieldShape,
    enabledBorder: kFieldShape,
    disabledBorder: kFieldShape,
    focusedBorder: OutlineInputBorder(
      borderRadius: kSmallRadius,
      borderSide: BorderSide(color: kBrandPurple),
    ),
    errorBorder: OutlineInputBorder(
      borderRadius: kSmallRadius,
      borderSide: BorderSide(color: kError, width: kBorderWidth),
    ),
    focusedErrorBorder: OutlineInputBorder(
      borderRadius: kSmallRadius,
      borderSide: BorderSide(color: kError),
    ),
  ),
  textSelectionTheme: const TextSelectionThemeData(
    cursorColor: kBrandPurple,
    selectionColor: kSurfacePurpleRaised,
    selectionHandleColor: kBrandPurpleLight,
  ),
  chipTheme: ChipThemeData(
    backgroundColor: kSurfacePurpleRaised,
    selectedColor: kSurfacePurpleRaised,
    secondarySelectedColor: kSurfacePurpleRaised,
    disabledColor: kSurfacePurple,
    labelStyle: kChipTextStyle,
    secondaryLabelStyle: kSelectedChipTextStyle,
    padding: kChipPadding,
    labelPadding: EdgeInsets.zero,
    side: WidgetStateBorderSide.resolveWith(
      (states) => BorderSide(
        color: states.contains(WidgetState.selected)
            ? kBrandPurpleLight
            : kSurfaceBorder,
        width: kBorderWidth,
      ),
    ),
    shape: const RoundedRectangleBorder(borderRadius: kPillRadius),
    checkmarkColor: kBrandPurpleLight,
    deleteIconColor: kBrandPurpleLight,
    iconTheme: const IconThemeData(color: kBrandPurpleLight, size: kIconSize),
    elevation: 0,
    pressElevation: 0,
    shadowColor: kPurpleGlow,
    surfaceTintColor: kTransparent,
  ),
  navigationBarTheme: NavigationBarThemeData(
    backgroundColor: kBackgroundDark,
    surfaceTintColor: kTransparent,
    shadowColor: kPurpleGlow,
    elevation: 0,
    indicatorColor: kSurfacePurpleRaised,
    indicatorShape: kSurfaceShape,
    iconTheme: WidgetStateProperty.resolveWith(
      (states) => IconThemeData(
        color: states.contains(WidgetState.selected)
            ? kBrandPurpleLight
            : kBrandPurple,
        size: kIconSize,
      ),
    ),
    labelTextStyle: WidgetStateProperty.resolveWith(
      (states) => TextStyle(
        fontFamily: kFontBody,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: states.contains(WidgetState.selected)
            ? kBrandPurpleLight
            : kTextHint,
      ),
    ),
  ),
  listTileTheme: const ListTileThemeData(
    shape: RoundedRectangleBorder(borderRadius: kCardRadius),
    iconColor: kBrandPurple,
    textColor: kTextPrimary,
    selectedColor: kBrandPurpleLight,
    selectedTileColor: kSurfacePurpleRaised,
    subtitleTextStyle: kSecondaryTextStyle,
  ),
  expansionTileTheme: const ExpansionTileThemeData(
    backgroundColor: kSurfacePurple,
    collapsedBackgroundColor: kSurfacePurple,
    shape: kSurfaceShape,
    collapsedShape: kSurfaceShape,
    clipBehavior: Clip.antiAlias,
    iconColor: kBrandPurpleLight,
    collapsedIconColor: kBrandPurple,
    textColor: kTextPrimary,
    collapsedTextColor: kTextPrimary,
  ),
  cardTheme: const CardThemeData(
    color: kSurfacePurple,
    surfaceTintColor: kTransparent,
    shadowColor: kPurpleGlow,
    elevation: 0,
    shape: kSurfaceShape,
    clipBehavior: Clip.antiAlias,
  ),
  dialogTheme: DialogThemeData(
    backgroundColor: kOverlaySurface,
    surfaceTintColor: kTransparent,
    barrierColor: kImageVeil,
    shadowColor: kPurpleGlow,
    elevation: 0,
    shape: kSurfaceShape,
    titleTextStyle: const TextStyle(
      fontFamily: kFontBody,
      fontSize: 20,
      fontWeight: FontWeight.w700,
      color: kTextPrimary,
    ),
    contentTextStyle: kSecondaryTextStyle,
  ),
  bottomSheetTheme: BottomSheetThemeData(
    backgroundColor: kOverlaySurface,
    modalBackgroundColor: kOverlaySurface,
    modalBarrierColor: kImageVeil,
    surfaceTintColor: kTransparent,
    shadowColor: kPurpleGlow,
    elevation: 0,
    modalElevation: 0,
    shape: kSurfaceShape,
    clipBehavior: Clip.antiAlias,
  ),
  snackBarTheme: SnackBarThemeData(
    backgroundColor: kOverlaySurface,
    contentTextStyle: const TextStyle(
      fontFamily: kFontBody,
      fontSize: 14,
      color: kTextPrimary,
    ),
    actionTextColor: kBrandPurpleLight,
    disabledActionTextColor: kTextHint,
    behavior: SnackBarBehavior.floating,
    elevation: 0,
    shape: kSurfaceShape,
  ),
  tooltipTheme: TooltipThemeData(
    decoration: BoxDecoration(
      color: kOverlaySurface,
      borderRadius: kSmallRadius,
      border: Border.all(color: kSurfaceBorder, width: kBorderWidth),
    ),
    textStyle: const TextStyle(
      fontFamily: kFontBody,
      fontSize: 12,
      color: kTextPrimary,
    ),
  ),
  progressIndicatorTheme: const ProgressIndicatorThemeData(
    color: kBrandPurple,
    linearTrackColor: kSurfacePurpleRaised,
    circularTrackColor: kBackgroundDark,
    borderRadius: kPillRadius,
  ),
);

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({super.key, required this.onPressed, required this.child})
    : icon = null;

  const PrimaryButton.icon({
    super.key,
    required this.onPressed,
    required this.icon,
    required Widget label,
  }) : child = label;

  final VoidCallback? onPressed;
  final Widget child;
  final Widget? icon;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      gradient: onPressed == null ? null : kPrimaryGradient,
      color: onPressed == null ? kSurfacePurpleRaised : null,
      borderRadius: kCardRadius,
      boxShadow: onPressed == null ? null : const [kPrimaryShadow],
    ),
    child: icon == null
        ? ElevatedButton(onPressed: onPressed, child: child)
        : ElevatedButton.icon(onPressed: onPressed, icon: icon, label: child),
  );
}

class SurfaceCard extends StatelessWidget {
  const SurfaceCard({
    super.key,
    required this.child,
    this.emphasized = false,
    this.compact = false,
    this.padding = const EdgeInsets.all(20),
  });

  final Widget child;
  final bool emphasized;
  final bool compact;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Container(
    padding: padding,
    decoration: BoxDecoration(
      color: emphasized ? kSurfacePurpleRaised : kSurfacePurple,
      borderRadius: compact ? kSmallRadius : kCardRadius,
      border: Border.all(color: kSurfaceBorder, width: kBorderWidth),
    ),
    child: child,
  );
}

class BrandIconBox extends StatelessWidget {
  const BrandIconBox(this.icon, {super.key, this.color, this.accent = false});

  final IconData icon;
  final Color? color;
  final bool accent;

  @override
  Widget build(BuildContext context) => Container(
    padding: kIconPadding,
    decoration: BoxDecoration(
      color: accent ? kCoralSurface : kSurfacePurple,
      borderRadius: kIconRadius,
      border: accent
          ? Border.all(color: kCoralBorder, width: kBorderWidth)
          : null,
    ),
    child: Icon(
      icon,
      size: kIconSize,
      color: color ?? (accent ? kBrandCoral : kIconMuted),
    ),
  );
}

class AppLoading extends StatelessWidget {
  const AppLoading({super.key, this.semanticsLabel});

  final String? semanticsLabel;

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: kSmallRadius,
    child: ColoredBox(
      color: kBackgroundDark,
      child: Center(
        child: CircularProgressIndicator(
          color: kBrandPurple,
          semanticsLabel: semanticsLabel,
        ),
      ),
    ),
  );
}
