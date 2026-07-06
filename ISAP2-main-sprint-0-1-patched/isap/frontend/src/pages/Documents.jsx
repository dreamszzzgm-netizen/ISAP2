import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { pmlaApi, facilitiesApi, organizationsApi } from '../api';
import { statusLabels, statusBadgeClass } from '../constants';

const sectionsList = [
  { id: 'section_1', title: '1. Характеристика ОПО' },
  { id: 'section_2', title: '2. Сценарии аварий' },
  { id: 'section_3', title: '3. Характеристика аварийности' },
  { id: 'section_4', title: '4. Силы и средства' },
  { id: 'section_5', title: '5. Взаимодействие сил' },
  { id: 'section_6', title: '6. Состав и дислокация' },
  { id: 'section_7', title: '7. Готовность сил' },
  { id: 'section_8', title: '8. Управление и оповещение' },
  { id: 'section_9', title: '9. Обмен информацией' },
  { id: 'section_10', title: '10. Первоочередные действия' },
  { id: 'section_11', title: '11. Действия персонала' },
  { id: 'section_12', title: '12. Безопасность населения' },
  { id: 'section_13', title: '13. Материально-техническое обеспечение' },
  { id: 'special_section', title: 'Специальный раздел' },
];

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [facilities, setFacilities] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [filterOrg, setFilterOrg] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [loading, setLoading] = useState(true);
  const [previewDoc, setPreviewDoc] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [regenDoc, setRegenDoc] = useState(null);
  const [regenSections, setRegenSections] = useState([]);
  const [regenLoading, setRegenLoading] = useState(false);
  const [aiReview, setAiReview] = useState(null);
  const [versions, setVersions] = useState([]);

  useEffect(() => {
    Promise.all([
      facilitiesApi.list().catch(() => []),
      organizationsApi.list().catch(() => []),
    ]).then(([facs, orgs]) => {
      setFacilities(facs);
      setOrganizations(orgs);
    });
  }, []);

  useEffect(() => {
    setLoading(true);
    const loadDocs = async () => {
      try {
        const data = await pmlaApi.list();
        setDocs(Array.isArray(data) ? data : []);
      } catch {
        setDocs([]);
      } finally {
        setLoading(false);
      }
    };
    loadDocs();
  }, []);

  // Закрытие модалок по Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setPreviewDoc(null);
        setPreviewData(null);
        setRegenDoc(null);
        setRegenSections([]);
      }
    };
    if (previewDoc || regenDoc) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [previewDoc, regenDoc]);

  const facilityName = (id) => facilities.find(f => f.id === id)?.name || '—';
  const orgName = (facId) => {
    const fac = facilities.find(f => f.id === facId);
    if (!fac) return '—';
    return organizations.find(o => o.id === fac.organization_id)?.name || '—';
  };

  const filtered = docs.filter(d => {
    if (filterOrg) {
      const fac = facilities.find(f => f.id === d.facility_id);
      if (!fac || fac.organization_id !== filterOrg) return false;
    }
    if (filterStatus && d.status !== filterStatus) return false;
    return true;
  });

  const handleDownload = async (docId, format = 'docx') => {
    try {
      const blob = format === 'pdf'
        ? await pmlaApi.downloadPdf(docId)
        : await pmlaApi.download(docId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pmla_${docId}.${format}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) {
      alert(`Ошибка: ${e.message}`);
    }
  };

  const handlePreview = async (doc) => {
    setPreviewDoc(doc);
    setPreviewLoading(true);
    setPreviewData(null);
    setAiReview(null);
    try {
      const data = await pmlaApi.preview(doc.id);
      setPreviewData(data);
      // Загружаем AI-ревью если есть
      try {
        const review = await pmlaApi.aiReview(doc.id);
        setAiReview(review);
      } catch { /* AI review not available */ }
      // Загружаем историю версий
      try {
        const vers = await pmlaApi.versions(doc.id);
        setVersions(vers);
      } catch { /* versions not available */ }
    } catch (e) {
      setPreviewData({ error: e.message });
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleRegen = async () => {
    if (!regenDoc || regenSections.length === 0) return;
    setRegenLoading(true);
    try {
      await pmlaApi.regenerate(regenDoc.id, regenSections);
      alert('Перегенерация завершена!');
      setRegenDoc(null);
      setRegenSections([]);
      // Перезагрузка документов
      const data = await pmlaApi.list();
      setDocs(Array.isArray(data) ? data : []);
    } catch (e) {
      alert(`Ошибка: ${e.message}`);
    } finally {
      setRegenLoading(false);
    }
  };

  const toggleRegenSection = (sectionId) => {
    setRegenSections(prev =>
      prev.includes(sectionId)
        ? prev.filter(s => s !== sectionId)
        : [...prev, sectionId]
    );
  };

  return (
    <div>
      <div className="section">
        <div className="section-header">
          <div className="section-title">Документы ПМЛА</div>
          <div className="section-actions">
            <Link to="/pmla" className="btn btn-primary btn-sm">
              <i className="fas fa-plus"></i> Создать ПМЛА
            </Link>
          </div>
        </div>

        <div style={{ padding: '16px 24px', display: 'flex', gap: 16, borderBottom: '1px solid var(--gray-100)' }}>
          <div className="form-group" style={{ flex: 1 }}>
            <select className="form-select" value={filterOrg} onChange={e => setFilterOrg(e.target.value)}>
              <option value="">Все организации</option>
              {organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <select className="form-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
              <option value="">Все статусы</option>
              <option value="draft">Черновик</option>
              <option value="processing">Генерация</option>
              <option value="pending_review">На ревью</option>
              <option value="approved">Утверждён</option>
              <option value="rejected">Возвращён</option>
              <option value="auto_validation_failed">Ошибка</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="loading-center"><div className="spinner"></div></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <i className="fas fa-folder-open"></i>
            <div>Нет документов</div>
            <Link to="/pmla" className="btn btn-primary btn-sm" style={{ marginTop: 16 }}>
              <i className="fas fa-plus"></i> Создать ПМЛА
            </Link>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Документ</th>
                <th>Объект</th>
                <th>Организация</th>
                <th>Статус</th>
                <th>Дата</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(doc => (
                <tr key={doc.id}>
                  <td><span className="tag tag-blue">{doc.id?.slice(0, 8)}</span></td>
                  <td><strong>{facilityName(doc.facility_id)}</strong></td>
                  <td>{orgName(doc.facility_id)}</td>
                  <td>
                    <span className={`badge ${statusBadgeClass[doc.status] || 'badge-draft'}`}>
                      {doc.status === 'processing' && <span className="badge-dot processing"></span>}
                      {statusLabels[doc.status] || doc.status}
                    </span>
                  </td>
                  <td>{doc.created_at ? new Date(doc.created_at).toLocaleDateString('ru-RU') : '—'}</td>
                  <td>
                    <div className="row-actions">
                      <button className="btn btn-ghost btn-sm" onClick={() => handlePreview(doc)} title="Просмотр">
                        <i className="fas fa-eye"></i>
                      </button>
                      {doc.status !== 'processing' && (
                        <button className="btn btn-ghost btn-sm" onClick={() => { setRegenDoc(doc); setRegenSections([]); }} title="Перегенерировать разделы">
                          <i className="fas fa-sync-alt"></i>
                        </button>
                      )}
                      {doc.status === 'approved' && (
                        <>
                          <button className="btn btn-ghost btn-sm" onClick={() => handleDownload(doc.id, 'docx')} title="Скачать DOCX">
                            <i className="fas fa-download"></i>
                          </button>
                          <button className="btn btn-ghost btn-sm" onClick={() => handleDownload(doc.id, 'pdf')} title="Скачать PDF">
                            <i className="fas fa-file-pdf"></i>
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Модалка превью */}
        {previewDoc && (
          <div className="modal-backdrop" onClick={() => { setPreviewDoc(null); setPreviewData(null); }}>
            <div className="modal-content" style={{ maxWidth: 800 }} onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>{previewDoc.title || 'ПМЛА'}</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>
                    {previewDoc.facility_name || '—'} | {statusLabels[previewDoc.status] || previewDoc.status}
                  </div>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => { setPreviewDoc(null); setPreviewData(null); }}>
                  <i className="fas fa-times"></i>
                </button>
              </div>
              <div style={{ padding: 24 }}>
                {previewLoading ? (
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <div className="spinner" style={{ margin: '0 auto 16px' }}></div>
                    <div style={{ color: 'var(--gray-500)' }}>Загрузка превью...</div>
                  </div>
                ) : previewData?.error ? (
                  <div style={{ textAlign: 'center', padding: 40, color: 'var(--danger)' }}>
                    <i className="fas fa-exclamation-circle" style={{ fontSize: 32, marginBottom: 12 }}></i>
                    <div>{previewData.error}</div>
                  </div>
                ) : previewData?.sections?.length > 0 ? (
                  <div>
                    {previewData.issues?.length > 0 && (
                      <div style={{ background: 'var(--warning-light)', border: '1px solid var(--warning)', borderRadius: 8, padding: 12, marginBottom: 20 }}>
                        <div style={{ fontWeight: 600, color: 'var(--warning)', marginBottom: 8 }}><i className="fas fa-exclamation-triangle"></i> Замечания:</div>
                        {previewData.issues.map((issue, i) => (
                          <div key={i} style={{ fontSize: 13, marginBottom: 4 }}>
                            <strong>{issue.section}</strong>: {issue.reason}
                          </div>
                        ))}
                      </div>
                    )}
                    {previewData.sections.map((section, i) => (
                      <div key={i} style={{ marginBottom: 20 }}>
                        {section.title && (
                          <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--gray-800)', marginBottom: 8, paddingBottom: 6, borderBottom: '1px solid var(--gray-100)' }}>
                            {section.title}
                          </h3>
                        )}
                        {section.content?.map((p, j) => (
                          <p key={j} style={{ fontSize: 13, color: 'var(--gray-700)', lineHeight: 1.6, marginBottom: 4 }}>{p}</p>
                        ))}
                      </div>
                    ))}

                    {/* История версий */}
                    {versions.length > 0 && (
                      <div style={{ marginBottom: 20 }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>
                          <i className="fas fa-history" style={{ color: 'var(--primary)' }}></i> История версий ({versions.length})
                        </h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {versions.map((v, i) => (
                            <div key={v.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: i === 0 ? 'var(--primary-light)' : 'var(--gray-50)', borderRadius: 8, fontSize: 13, border: `1px solid ${i === 0 ? 'var(--primary)' : 'var(--gray-200)'}` }}>
                              <div>
                                <span style={{ fontWeight: 600 }}>Версия {v.version_number}</span>
                                {v.reviewer_decision && (
                                  <span className={`badge ${v.reviewer_decision === 'approved' ? 'badge-approved' : 'badge-rejected'}`} style={{ marginLeft: 8 }}>
                                    {v.reviewer_decision === 'approved' ? 'Утверждена' : 'Отклонена'}
                                  </span>
                                )}
                                <span style={{ color: 'var(--gray-400)', marginLeft: 8 }}>{v.created_at ? new Date(v.created_at).toLocaleString('ru-RU') : '—'}</span>
                              </div>
                              {i > 0 && v.content_docx && (
                                <button
                                  className="btn btn-ghost btn-sm"
                                  onClick={async () => {
                                    if (!confirm(`Восстановить версию ${v.version_number}? Текущая версия будет перезаписана.`)) return;
                                    try {
                                      await pmlaApi.restoreVersion(previewDoc.id, v.id);
                                      alert('Версия восстановлена!');
                                      setPreviewDoc(null);
                                      setPreviewData(null);
                                      const data = await pmlaApi.list();
                                      setDocs(Array.isArray(data) ? data : []);
                                    } catch (e) {
                                      alert(`Ошибка: ${e.message}`);
                                    }
                                  }}
                                  title="Восстановить эту версию"
                                >
                                  <i className="fas fa-undo"></i> Восстановить
                                </button>
                              )}
                              {i === 0 && <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>текущая</span>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI-ревью */}
                    {aiReview && (
                      <div style={{ marginBottom: 20 }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>
                          <i className="fas fa-robot" style={{ color: 'var(--primary)' }}></i> AI-ревью
                        </h3>
                        <div style={{ background: 'var(--gray-50)', borderRadius: 8, padding: 16 }}>
                          <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
                            <div>
                              <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>Уверенность</div>
                              <div style={{ fontSize: 18, fontWeight: 700, color: aiReview.confidence >= 0.85 ? 'var(--success)' : aiReview.confidence >= 0.6 ? 'var(--warning)' : 'var(--danger)' }}>
                                {(aiReview.confidence * 100).toFixed(0)}%
                              </div>
                            </div>
                            <div>
                              <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>Решение</div>
                              <div style={{ fontSize: 14, fontWeight: 600 }}>
                                {aiReview.decision === 'auto_approve' && <span style={{ color: 'var(--success)' }}>Авто-одобрение</span>}
                                {aiReview.decision === 'escalate_to_human' && <span style={{ color: 'var(--warning)' }}>На проверку</span>}
                                {aiReview.decision === 'needs_revision' && <span style={{ color: 'var(--danger)' }}>Требует доработки</span>}
                              </div>
                            </div>
                          </div>
                          {aiReview.items?.length > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                              {aiReview.items.map((item, i) => (
                                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                                  <i className={item.passed ? 'fas fa-check-circle' : 'fas fa-times-circle'}
                                     style={{ color: item.passed ? 'var(--success)' : 'var(--danger)', fontSize: 12 }}></i>
                                  <span style={{ flex: 1 }}>{item.name}</span>
                                  <span style={{ color: 'var(--gray-400)', fontSize: 12 }}>{(item.confidence * 100).toFixed(0)}%</span>
                                </div>
                              ))}
                            </div>
                          )}
                          {aiReview.summary && (
                            <div style={{ marginTop: 12, fontSize: 12, color: 'var(--gray-600)', whiteSpace: 'pre-line' }}>
                              {aiReview.summary}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    <div style={{ borderTop: '1px solid var(--gray-200)', paddingTop: 16, marginTop: 20, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
                      <button className="btn btn-secondary" onClick={() => { setPreviewDoc(null); setPreviewData(null); }}>Закрыть</button>
                      {previewDoc.status === 'approved' && (
                        <button className="btn btn-primary" onClick={() => { handleDownload(previewDoc.id, 'docx'); setPreviewDoc(null); setPreviewData(null); }}>
                          <i className="fas fa-download"></i> Скачать DOCX
                        </button>
                      )}
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>
                    <div>Содержимое недоступно для просмотра</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Модалка перегенерации */}
        {regenDoc && (
          <div className="modal-backdrop" onClick={() => { setRegenDoc(null); setRegenSections([]); }}>
            <div className="modal-content" style={{ maxWidth: 500 }} onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700 }}>Перегенерация разделов</div>
                  <div style={{ fontSize: 12, color: 'var(--gray-500)' }}>{facilityName(regenDoc.facility_id)}</div>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => { setRegenDoc(null); setRegenSections([]); }}>
                  <i className="fas fa-times"></i>
                </button>
              </div>
              <div style={{ padding: 24 }}>
                <div style={{ fontSize: 13, color: 'var(--gray-600)', marginBottom: 16 }}>
                  Выберите разделы для перегенерации. Остальные разделы останутся без изменений.
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
                  {sectionsList.map(s => (
                    <label key={s.id} className="checkbox-label" style={{ padding: '8px 12px', background: regenSections.includes(s.id) ? 'var(--primary-light)' : 'var(--gray-50)', borderRadius: 6, border: `1px solid ${regenSections.includes(s.id) ? 'var(--primary)' : 'var(--gray-200)'}` }}>
                      <input
                        type="checkbox"
                        checked={regenSections.includes(s.id)}
                        onChange={() => toggleRegenSection(s.id)}
                      />
                      {s.title}
                    </label>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                  <button className="btn btn-secondary btn-sm" onClick={() => { setRegenDoc(null); setRegenSections([]); }}>Отмена</button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleRegen}
                    disabled={regenSections.length === 0 || regenLoading}
                  >
                    {regenLoading ? <><i className="fas fa-spinner fa-spin"></i> Генерация...</> : <><i className="fas fa-sync-alt"></i> Перегенерировать ({regenSections.length})</>}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
