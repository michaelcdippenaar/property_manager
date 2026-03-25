import 'api_client.dart';

class UnitInfoItem {
  UnitInfoItem({
    required this.id,
    required this.iconType,
    required this.label,
    required this.value,
  });

  final int id;
  final String iconType;
  final String label;
  final String value;

  factory UnitInfoItem.fromJson(Map<String, dynamic> j) => UnitInfoItem(
    id: j['id'] as int,
    iconType: j['icon_type'] as String? ?? 'other',
    label: j['label'] as String? ?? '',
    value: j['value'] as String? ?? '',
  );
}

class InfoService {
  Future<List<UnitInfoItem>> listUnitInfo() async {
    final data = await apiClient.getList('/properties/unit-info/');
    return (data as List).map((e) => UnitInfoItem.fromJson(e as Map<String, dynamic>)).toList();
  }
}

final infoService = InfoService();
