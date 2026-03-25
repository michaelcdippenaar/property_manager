// Factory methods to create test fixtures for models.

Map<String, dynamic> authUserJson({
  int id = 1,
  String email = 'test@example.com',
  String fullName = 'Test User',
  String role = 'tenant',
}) => {
  'id': id,
  'email': email,
  'full_name': fullName,
  'role': role,
};

Map<String, dynamic> maintenanceIssueJson({
  int id = 1,
  String title = 'Leaking tap',
  String description = 'Kitchen tap is dripping',
  String status = 'open',
  String priority = 'medium',
  String category = 'plumbing',
  String ticketRef = 'MNT-001',
  String createdAt = '2025-01-15T10:00:00Z',
}) => {
  'id': id,
  'title': title,
  'description': description,
  'status': status,
  'priority': priority,
  'category': category,
  'ticket_reference': ticketRef,
  'created_at': createdAt,
};

Map<String, dynamic> unitInfoItemJson({
  int id = 1,
  String iconType = 'wifi',
  String label = 'WiFi Password',
  String value = 'secret123',
}) => {
  'id': id,
  'icon_type': iconType,
  'label': label,
  'value': value,
};

Map<String, dynamic> loginResponseJson({
  String access = 'test-access-token',
  String refresh = 'test-refresh-token',
  Map<String, dynamic>? user,
}) => {
  'access': access,
  'refresh': refresh,
  'user': user ?? authUserJson(),
};

Map<String, dynamic> conversationJson({
  int id = 1,
  String title = 'Test Conversation',
  String lastMessage = 'Hello',
  String updatedAt = '2025-01-15T10:00:00Z',
}) => {
  'id': id,
  'title': title,
  'last_message': lastMessage,
  'updated_at': updatedAt,
};

Map<String, dynamic> messageJson({
  int id = 1,
  String role = 'user',
  String content = 'Hello',
  String? attachmentUrl,
  String? attachmentKind,
}) => {
  'id': id,
  'role': role,
  'content': content,
  if (attachmentUrl != null) 'attachment_url': attachmentUrl,
  if (attachmentKind != null) 'attachment_kind': attachmentKind,
};
