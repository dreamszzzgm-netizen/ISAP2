import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { organizationsApi, facilitiesApi, pmlaApi, regulatoryApi } from '../api';
import { statusLabels, statusBadgeClass } from '../constants';

const dotClass = {
  processing: 'badge-dot processing',
};

export default function Dashboard() {
  const [orgCount, setOrgCount] = useState(0);
  const [facCount, setFacCount] = useState(0);
  const [docs, setDocs] = useState([]);
  const [expiring, setExpiring] = useState([]);
  const [overdue, setOverdue] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [orgs, facs] = await Promise.all([
          organizationsApi.list().catch(() => []),
          facilitiesApi.list().catch(() => []),
        ]);
        setOrgCount(orgs.length);
        setFacCount(facs.length);

        try {
          const documents = await pmlaApi.list();
          setDocs(Array.isArray(documents) ? documents.slice(0, 5) : []);
        } catch { setDocs([]); }

        try {
          setExpiring(await pmlaApi.expiring(90));
        } catch { setExpiring([]); }

        try {
          setOverdue(await pmlaApi.overdue());
        } catch { setOverdue([]); }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const approvedCount = docs.filter(d => d.status === 'approved').length;
  const reviewCount = docs.filter(d => d.status === 'pending_review').length;
  const failedCount = docs.filter(d => d.status === 'auto_validation_failed' || d.status === 'rejected').length;

  return (
    <div>
      <div className="stats-grid">
        <Link to="/documents" className="stat-card">
          <div className="stat-header">
            <div className="stat-label">Всего ПМЛА</div>
            <div className="stat-icon blue"><i className="fas fa-file-shield"></i></div>
          </div>
          <div className="stat-value">{docs.length || '—'}</div>
        </Link>
        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-label">Утверждено</div>
            <div className="stat-icon green"><i className="fas fa-check-circle"></i></div>
          </div>
          <div className="stat-value">{approvedCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-label">На ревью</div>
            <div className="stat-icon orange"><i className="fas fa-clock"></i></div>
          </div>
          <div className="stat-value">{reviewCount}</div>
        </div>
        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-label">Требует внимания</div>
            <div className="stat-icon red"><i className="fas fa-exclamation-triangle"></i></div>
          </div>
          <div className="stat-value">{failedCount + overdue.length}</div>
        </div>
      </div>

      {/* Сроки пересмотра */}
      {(expiring.length > 0 || overdue.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: overdue.length > 0 ? '1fr 1fr' : '1fr', gap: 24, marginBottom: 24 }}>
          {overdue.length > 0 && (
            <div className="section" style={{ borderLeft: '3px solid var(--danger)' }}>
              <div className="section-header">
                <div className="section-title" style={{ color: 'var(--danger)' }}>
                  <i className="fas fa-exclamation-circle"></i> Просроченные ПМЛА ({overdue.length})
                </div>
              </div>
              <div style={{ padding: 16 }}>
                {overdue.map(doc => (
                  <div key={doc.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--gray-100)' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{doc.facility_name || '—'}</div>
                      <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>Истёк: {doc.review_date ? new Date(doc.review_date).toLocaleDateString('ru-RU') : '—'}</div>
                    </div>
                    <span className="badge badge-danger">+{doc.days_overdue} дн</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {expiring.length > 0 && (
            <div className="section" style={{ borderLeft: '3px solid var(--warning)' }}>
              <div className="section-header">
                <div className="section-title" style={{ color: 'var(--warning)' }}>
                  <i className="fas fa-clock"></i> Истекающие сроки ({expiring.length})
                </div>
              </div>
              <div style={{ padding: 16 }}>
                {expiring.map(doc => (
                  <div key={doc.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--gray-100)' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{doc.facility_name || '—'}</div>
                      <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>Пересмотр: {doc.review_date ? new Date(doc.review_date).toLocaleDateString('ru-RU') : '—'}</div>
                    </div>
                    <span className="badge badge-warning">{doc.days_remaining} дн</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
        <div className="section">
          <div className="section-header">
            <div className="section-title">Последние ПМЛА</div>
            <div className="section-actions">
              <Link to="/pmla" className="btn btn-primary btn-sm">
                <i className="fas fa-plus"></i> Создать ПМЛА
              </Link>
            </div>
          </div>
          {loading ? (
            <div className="loading-center"><div className="spinner"></div></div>
          ) : docs.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--gray-400)' }}>
              <i className="fas fa-file-shield" style={{ fontSize: 40, marginBottom: 12, display: 'block' }}></i>
              <div>Нет документов. Создайте первый ПМЛА.</div>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Документ</th>
                  <th>Объект</th>
                  <th>Статус</th>
                  <th>Дата</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr key={doc.id}>
                    <td><span className="tag tag-blue">{doc.id?.slice(0, 8)}</span></td>
                    <td><strong>{doc.facility_name || '—'}</strong></td>
                    <td>
                      <span className={`badge ${statusBadgeClass[doc.status] || 'badge-draft'}`}>
                        {(dotClass[doc.status] || doc.status === 'processing') && <span className="badge-dot processing"></span>}
                        {statusLabels[doc.status] || doc.status}
                      </span>
                    </td>
                    <td>{doc.created_at ? new Date(doc.created_at).toLocaleDateString('ru-RU') : '—'}</td>
                    <td>
                      <Link to="/documents" className="btn btn-ghost btn-sm">
                        <i className="fas fa-ellipsis-v"></i>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="section">
          <div className="section-header">
            <div className="section-title">Справочники</div>
          </div>
          <div style={{ padding: 20 }}>
            <Link to="/organizations" className="nav-item" style={{ marginBottom: 8, background: 'var(--gray-50)', borderRadius: 8 }}>
              <i className="fas fa-building" style={{ color: 'var(--primary)' }}></i>
              <span>Организации</span>
              <span className="nav-badge" style={{ background: 'var(--primary)' }}>{orgCount}</span>
            </Link>
            <Link to="/facilities" className="nav-item" style={{ marginBottom: 8, background: 'var(--gray-50)', borderRadius: 8 }}>
              <i className="fas fa-industry" style={{ color: 'var(--success)' }}></i>
              <span>Объекты ОПО</span>
              <span className="nav-badge" style={{ background: 'var(--success)' }}>{facCount}</span>
            </Link>
            <Link to="/persons" className="nav-item" style={{ marginBottom: 8, background: 'var(--gray-50)', borderRadius: 8 }}>
              <i className="fas fa-users" style={{ color: 'var(--warning)' }}></i>
              <span>Ответственные лица</span>
            </Link>
            <Link to="/regulatory" className="nav-item" style={{ background: 'var(--gray-50)', borderRadius: 8 }}>
              <i className="fas fa-book" style={{ color: 'var(--danger)' }}></i>
              <span>Нормативы</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
