import 'package:flutter/material.dart';

import '../theme.dart';

class FluentLogo extends StatelessWidget {
  const FluentLogo({super.key, this.size = 48}) : assert(size > 0);

  static const assetPath = 'logo.png';

  final double size;

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    image: true,
    label: 'Fluent',
    child: Image.asset(
      assetPath,
      width: size,
      height: size,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      excludeFromSemantics: true,
    ),
  );
}

class FluentWordmark extends StatelessWidget {
  const FluentWordmark({
    super.key,
    this.logoSize = 48,
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
