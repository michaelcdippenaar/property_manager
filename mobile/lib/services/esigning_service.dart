import 'api_client.dart';

class ESigningSigner {
  ESigningSigner({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    required this.status,
    required this.embedSrc,
    required this.order,
  });

  final int? id;
  final String name;
  final String email;
  final String role;
  final String status;
  final String embedSrc;
  final int order;

  factory ESigningSigner.fromJson(Map<String, dynamic> j) {
    final rawId = j['id'];
    return ESigningSigner(
      id: rawId is int ? rawId : int.tryParse(rawId?.toString() ?? ''),
      name: j['name'] as String? ?? '',
      email: j['email'] as String? ?? '',
      role: j['role'] as String? ?? '',
      status: j['status'] as String? ?? '',
      embedSrc: j['embed_src'] as String? ?? '',
      order: j['order'] is int ? j['order'] as int : int.tryParse('${j['order'] ?? 0}') ?? 0,
    );
  }
}

class ESigningSubmission {
  ESigningSubmission({
    required this.id,
    required this.leaseId,
    required this.leaseLabel,
    required this.status,
    required this.signingMode,
    required this.signers,
    required this.signedPdfUrl,
    required this.createdAt,
  });

  final int id;
  final int leaseId;
  final String leaseLabel;
  final String status;
  final String signingMode;
  final List<ESigningSigner> signers;
  final String signedPdfUrl;
  final String createdAt;

  factory ESigningSubmission.fromJson(Map<String, dynamic> j) {
    final rawSigners = j['signers'];
    final list = rawSigners is List
        ? rawSigners.map((e) => ESigningSigner.fromJson(e as Map<String, dynamic>)).toList()
        : <ESigningSigner>[];
    list.sort((a, b) => a.order.compareTo(b.order));
    return ESigningSubmission(
      id: j['id'] as int,
      leaseId: j['lease'] as int,
      leaseLabel: j['lease_label'] as String? ?? '',
      status: j['status'] as String? ?? '',
      signingMode: j['signing_mode'] as String? ?? 'sequential',
      signers: list,
      signedPdfUrl: j['signed_pdf_url'] as String? ?? '',
      createdAt: j['created_at'] as String? ?? '',
    );
  }
}

/// First signer (by order) who may still sign and matches [userEmail], respecting sequential turns.
ESigningSigner? actionableSignerForUser({
  required String userEmail,
  required ESigningSubmission submission,
}) {
  final email = userEmail.trim().toLowerCase();
  if (email.isEmpty) return null;
  final mode = submission.signingMode.toLowerCase();
  final sorted = [...submission.signers]..sort((a, b) => a.order.compareTo(b.order));

  bool isDone(String s) {
    final x = s.toLowerCase();
    return x == 'completed' || x == 'signed' || x == 'declined';
  }

  if (mode == 'parallel') {
    for (final s in sorted) {
      if (!isDone(s.status) && s.email.toLowerCase() == email) {
        return s;
      }
    }
    return null;
  }

  for (final s in sorted) {
    if (isDone(s.status)) continue;
    if (s.email.toLowerCase() == email) return s;
    return null;
  }
  return null;
}

class ESigningService {
  Future<List<ESigningSubmission>> listForLease(int leaseId) async {
    final data = await apiClient.getList(
      '/esigning/submissions/',
      params: {'lease_id': '$leaseId'},
    );
    return (data as List)
        .map((e) => ESigningSubmission.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ESigningSubmission> getSubmission(int id) async {
    final data = await apiClient.get('/esigning/submissions/$id/');
    return ESigningSubmission.fromJson(data);
  }
}

final esigningService = ESigningService();
