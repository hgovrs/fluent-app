import 'package:flutter/material.dart';

import '../theme.dart';

class SelectionTile extends StatelessWidget {
  const SelectionTile({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Material(
      color: selected ? kSurfacePurpleRaised : kSurfacePurple,
      shape: RoundedRectangleBorder(
        borderRadius: kCardRadius,
        side: BorderSide(
          color: selected ? kBrandPurpleLight : kSurfaceBorder,
          width: kBorderWidth,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: ListTile(
        leading: BrandIconBox(
          icon,
          color: selected ? kBrandPurpleLight : kIconMuted,
        ),
        title: Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: selected ? kBrandPurpleLight : kTextPrimary,
          ),
        ),
        subtitle: Text(subtitle, style: kSecondaryTextStyle),
        selected: selected,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        onTap: onTap,
      ),
    ),
  );
}
