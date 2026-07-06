// ===== Централизованные константы =====

// Статусы ПМЛА-документов
export const statusLabels = {
  draft: 'Черновик',
  processing: 'Генерация',
  auto_validation_failed: 'Ошибка',
  pending_review: 'На ревью',
  approved: 'Утверждён',
  rejected: 'Возвращён',
};

export const statusBadgeClass = {
  draft: 'badge-draft',
  processing: 'badge-processing',
  auto_validation_failed: 'badge-failed',
  pending_review: 'badge-review',
  approved: 'badge-approved',
  rejected: 'badge-rejected',
};

// Классы опасности ОПО
export const hazardLabels = {
  1: 'I — Чрезвычайно высокая',
  2: 'II — Высокая',
  3: 'III — Умеренная',
  4: 'IV — Низкая',
};

export const hazardBadgeClass = {
  1: 'badge-danger',
  2: 'badge-warning',
  3: 'badge-info',
  4: 'badge-success',
};

export const hazardLabel = (cls) => hazardLabels[cls] || `Класс ${cls}`;
export const hazardBadge = (cls) => hazardBadgeClass[cls] || 'badge-draft';

// Роли ответственных лиц
export const roleLabels = {
  director: 'Директор',
  safety_manager: 'Начальник ПБ',
  engineer: 'Инженер',
  other: 'Другое',
};

export const roleLabel = (role) => roleLabels[role] || role || '—';

// Статусы нормативов
export const regulatoryStatusBadge = {
  'действует': 'badge-success',
  'спорный': 'badge-warning',
  'устаревший': 'badge-failed',
  'отменён': 'badge-draft',
};

// Утилиты для поиска по ID
export const orgName = (organizations, id) => organizations.find(o => o.id === id)?.name || id;
export const facilityName = (facilities, id) => facilities.find(f => f.id === id)?.name || '—';
