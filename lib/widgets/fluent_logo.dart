import 'package:flutter/material.dart';

import '../theme.dart';

/// Marca do Fluent: um balão de fala com a letra F e o ponto de conquista.
///
/// A geometria é desenhada em uma grade de 108x108 — a mesma usada pelo
/// favicon web e pelo ícone do Android — para manter o logo idêntico em
/// todas as áreas do app.
class FluentLogo extends StatelessWidget {
  const FluentLogo({super.key, this.size = 40, this.withBackground = true});

  /// Lado do logo em pixels lógicos.
  final double size;

  /// Quando falso, desenha apenas o balão sobre fundo transparente.
  final bool withBackground;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: size,
    height: size,
    child: CustomPaint(
      painter: _FluentLogoPainter(withBackground: withBackground),
      isComplex: true,
      willChange: false,
    ),
  );
}

/// Logo com o nome do app ao lado, usado em cabeçalhos e na abertura.
class FluentWordmark extends StatelessWidget {
  const FluentWordmark({super.key, this.logoSize = 30, this.fontSize = 22, this.color = ink});

  final double logoSize;
  final double fontSize;
  final Color color;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      FluentLogo(size: logoSize),
      const SizedBox(width: 10),
      Text(
        'fluent',
        style: TextStyle(
          fontSize: fontSize,
          fontWeight: FontWeight.w900,
          letterSpacing: -1,
          color: color,
        ),
      ),
    ],
  );
}

class _FluentLogoPainter extends CustomPainter {
  const _FluentLogoPainter({required this.withBackground});

  final bool withBackground;

  static const _logoGreenLight = Color(0xFF2F9A69);
  static const _logoGreenDark = Color(0xFF1E5F44);

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    final scale = size.shortestSide / 108;
    canvas.scale(scale);

    if (withBackground) {
      final background = RRect.fromRectAndRadius(
        const Rect.fromLTWH(0, 0, 108, 108),
        const Radius.circular(26),
      );
      canvas.drawRRect(
        background,
        Paint()
          ..shader = const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [_logoGreenLight, _logoGreenDark],
          ).createShader(const Rect.fromLTWH(0, 0, 108, 108)),
      );
    }

    canvas.drawPath(_bubble(), Paint()..color = withBackground ? Colors.white : green);
    canvas.drawPath(_letter(), Paint()..color = withBackground ? green : Colors.white);
    canvas.drawCircle(
      const Offset(76, 56),
      7,
      Paint()..color = withBackground ? amber : mint,
    );
    canvas.restore();
  }

  /// Balão de fala com cauda inferior esquerda.
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

  /// Letra F dentro do balão.
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
