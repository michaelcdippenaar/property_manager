import 'package:flutter_test/flutter_test.dart';
import 'package:klikk_tenant/services/esigning_service.dart';

ESigningSubmission _sub(String mode, List<ESigningSigner> signers) {
  return ESigningSubmission(
    id: 1,
    leaseId: 1,
    leaseLabel: 'Test',
    status: 'in_progress',
    signingMode: mode,
    signers: signers,
    signedPdfUrl: '',
    createdAt: '',
  );
}

void main() {
  group('actionableSignerForUser', () {
    test('sequential: only first pending signer who matches email', () {
      final sub = _sub('sequential', [
        ESigningSigner(
          id: 1,
          name: 'Landlord',
          email: 'll@test.com',
          role: 'First',
          status: 'sent',
          embedSrc: 'https://a',
          order: 0,
        ),
        ESigningSigner(
          id: 2,
          name: 'Tenant',
          email: 'tenant@test.com',
          role: 'Second',
          status: 'sent',
          embedSrc: 'https://b',
          order: 1,
        ),
      ]);
      expect(
        actionableSignerForUser(userEmail: 'tenant@test.com', submission: sub),
        isNull,
      );
      expect(
        actionableSignerForUser(userEmail: 'll@test.com', submission: sub)?.embedSrc,
        'https://a',
      );
    });

    test('sequential: after first completes, tenant is actionable', () {
      final sub = _sub('sequential', [
        ESigningSigner(
          id: 1,
          name: 'Landlord',
          email: 'll@test.com',
          role: 'First',
          status: 'completed',
          embedSrc: 'https://a',
          order: 0,
        ),
        ESigningSigner(
          id: 2,
          name: 'Tenant',
          email: 'tenant@test.com',
          role: 'Second',
          status: 'sent',
          embedSrc: 'https://b',
          order: 1,
        ),
      ]);
      expect(
        actionableSignerForUser(userEmail: 'tenant@test.com', submission: sub)?.embedSrc,
        'https://b',
      );
    });

    test('parallel: any pending signer matching email', () {
      final sub = _sub('parallel', [
        ESigningSigner(
          id: 1,
          name: 'Landlord',
          email: 'll@test.com',
          role: 'First',
          status: 'sent',
          embedSrc: 'https://a',
          order: 0,
        ),
        ESigningSigner(
          id: 2,
          name: 'Tenant',
          email: 'tenant@test.com',
          role: 'Second',
          status: 'sent',
          embedSrc: 'https://b',
          order: 1,
        ),
      ]);
      expect(
        actionableSignerForUser(userEmail: 'tenant@test.com', submission: sub)?.embedSrc,
        'https://b',
      );
    });
  });
}
