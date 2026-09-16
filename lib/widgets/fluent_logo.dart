import 'package:flutter/material.dart';

import '../theme.dart';

// Keep the 108x108 geometry in sync with the SVG and Android vector.
class FluentLogo extends StatelessWidget {
  const FluentLogo({super.key, this.size = 40, this.withBackground = true})
    : assert(size > 0);

  final double size;
  final bool withBackground;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    image: true,
    label: 'Fluent',
    child: DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 26 / 108),
        boxShadow: withBackground ? const [kPrimaryShadow] : null,
      ),
      child: SizedBox.square(
        dimension: size,
        child: CustomPaint(
          painter: _FluentLogoPainter(withBackground: withBackground),
        ),
      ),
    ),
  );
}

class FluentWordmark extends StatelessWidget {
  const FluentWordmark({
    super.key,
    this.logoSize = 30,
    this.fontSize = 24,
    this.color = kTextPrimary,
  }) : assert(fontSize > 0);

  final double logoSize;
  final double fontSize;
  final Color color;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      ExcludeSemantics(child: FluentLogo(size: logoSize)),
      const SizedBox(width: 10),
      Flexible(
        child: FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            'fluent',
            style: kBrandHeadlineStyle.copyWith(
              fontSize: fontSize,
              color: color,
            ),
          ),
        ),
      ),
    ],
  );
}

class _FluentLogoPainter extends CustomPainter {
  const _FluentLogoPainter({required this.withBackground});

  final bool withBackground;
  static const _bounds = Rect.fromLTWH(0, 0, 108, 108);

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.shortestSide / 108);
    if (withBackground) {
      canvas.drawRRect(
        RRect.fromRectAndRadius(_bounds, const Radius.circular(26)),
        Paint()..shader = kPrimaryGradient.createShader(_bounds),
      );
    }
    canvas.drawPath(
      _bubble(),
      Paint()..color = withBackground ? kTextPrimary : kBrandPurple,
    );
    canvas.drawPath(
      _letter(),
      Paint()..color = withBackground ? kBrandPurple : kTextPrimary,
    );
    canvas.drawCircle(const Offset(76, 56), 7, Paint()..color = kBrandCoral);
    canvas.restore();
  }

  Path _bubble() {
    const radius = Radius.circular(18);
    return Path()
      ..moveTo(36, 16)
      ..lineTo(72, 16)
      ..arcToPoint(const Offset(90, 34), radius: radius)
      ..lineTo(90, 56)
      ..arcToPoint(const Offset(72, 74), radius: radius)
      ..lineTo(56, 74)
      ..lineTo(28, 94)
      ..lineTo(36, 74)
      ..arcToPoint(const Offset(18, 56), radius: radius)
      ..lineTo(18, 34)
      ..arcToPoint(const Offset(36, 16), radius: radius)
      ..close();
  }

  Path _letter() => Path()
    ..moveTo(40, 28)
    ..lineTo(70, 28)
    ..lineTo(70, 38)
    ..lineTo(50, 38)
    ..lineTo(50, 44)
    ..lineTo(64, 44)
    ..lineTo(64, 53)
    ..lineTo(50, 53)
    ..lineTo(50, 62)
    ..lineTo(40, 62)
    ..close();

  @override
  bool shouldRepaint(covariant _FluentLogoPainter oldDelegate) =>
      oldDelegate.withBackground != withBackground;
}
