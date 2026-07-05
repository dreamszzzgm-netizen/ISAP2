import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { pmlaApi, facilitiesApi, organizationsApi, equipmentApi, substancesApi, personsApi } from '../api';
import { useAuth } from '../context/AuthContext';
import { statusLabels } from '../constants';
import GenerationProgress from './GenerationProgress';

export default function PmlaWizard() {
  const navigate = useNavigate();
  const { apiKey } = useAuth();
  const [step, setStep] = useState(1);
  const [organizations, setOrganizations] = useState([]);
  const [facilities, setFacilities] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedFacility, setSelectedFacility] = useState('');
  const [facilityData, setFacilityData] = useState(null);
  const [equipment, setEquipment] = useState([]);
  const [substances, setSubstances] = useState([]);
  const [persons, setPersons] = useState([]);
  const [documentId, setDocumentId] = useState(null);
  const [status, setStatus] = useState(null);
  const [statusData, setStatusData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [genStep, setGenStep] = useState(0);
  const [previewData, setPreviewData] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    organizationsApi.list().then(setOrganizations).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedOrg) { setFacilities([]); setSelectedFacility(''); return; }
    facilitiesApi.list(selectedOrg).then(setFacilities).catch(() => {});
  }, [selectedOrg]);

  useEffect(() => {
    if (!selectedFacility) return;
    Promise.all([
      facilitiesApi.get(selectedFacility),
      equipmentApi.list(selectedFacility),
      substancesApi.list(selectedFacility),
    ]).then(([fac, eq, sub]) => {
      setFacilityData(fac);
      setEquipment(eq);
      setSubstances(sub);
      const org = organizations.find(o => o.id === fac.organization_id);
      if (org) personsApi.list(org.id).then(setPersons).catch(() => setPersons([]));
    }).catch(() => {});
  }, [selectedFacility, organizations]);

  useEffect(() => {
    if (!documentId || status !== 'processing') return;
    const iv = setInterval(async () => {
      try {
        const data = await pmlaApi.getStatus(documentId);
        setStatusData(data);
        setStatus(data.status);
      } catch (e) { console.error(e); }
    }, 2000);
    return () => clearInterval(iv);
  }, [documentId, status]);

  const handleGenerate = async () => {
    setLoading(true);
    setGenStep(1);
    setStatus('processing');
    try {
      const result = await pmlaApi.generate(selectedFacility);
      setDocumentId(result.document_id);
      setStatus(result.status);
      setStatusData(result);
      setGenStep(4);
    } catch (e) {
      setStatus('error');
      alert(`Ошибка: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async (decision) => {
    if (!documentId) return;
    setLoading(true);
    try {
      const reviewerId = apiKey || 'anonymous';
      await pmlaApi.review(documentId, reviewerId, decision, statusData?.issues || []);
      setStatus(decision);
      setStatusData({ ...statusData, status: decision });
    } catch (e) {
      alert(`Ошибка: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (format = 'docx') => {
    if (!documentId) return;
    try {
      const blob = format === 'pdf'
        ? await pmlaApi.downloadPdf(documentId)
        : await pmlaApi.download(documentId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pmla_${documentId}.${format}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch (e) {
      alert(`Ошибка скачивания: ${e.message}`);
    }
  };

  const stepCompleted = (s) => s < step;
  const stepActive = (s) => s === step;

  return (
    <div>
      <div className="section mb-24">
        <div className="section-header">
          <div>
            <div className="section-title">Создание нового ПМЛА</div>
            <div style={{ fontSize: 13, color: 'var(--gray-500)', marginTop: 4 }}>
              Пошаговый мастер генерации плана мероприятий
            </div>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/')}>
            <i className="fas fa-arrow-left"></i> Назад
          </button>
        </div>
      </div>

      <div className="wizard">
        {[1,2,3,4,5,6].map(s => (
          <div key={s} className={`wizard-step ${stepActive(s) ? 'active' : ''} ${stepCompleted(s) ? 'completed' : ''}`}>
            <div className="step-num">{stepCompleted(s) ? <i className="fas fa-check"></i> : s}</div>
            <div className="step-info">
              <div className="step-title">{['Выбор объекта', 'Контекст', 'Расчёты', 'Генерация', 'Просмотр', 'Ревью'][s-1]}</div>
              <div className="step-desc">{['Организация и ОПО', 'Оборудование и вещества', 'Зоны поражения', 'AI + валидация', 'Содержимое документа', 'Утверждение'][s-1]}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Step 1: Выбор объекта */}
      {step === 1 && (
        <div className="section">
          <div className="section-header"><div className="section-title">Шаг 1: Выбор организации и объекта ОПО</div></div>
          <div className="p-24">
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label">Организация <span className="required">*</span></label>
                <select className="form-select" value={selectedOrg} onChange={e => setSelectedOrg(e.target.value)}>
                  <option value="">— Выберите —</option>
                  {organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Объект ОПО <span className="required">*</span></label>
                <select className="form-select" value={selectedFacility} onChange={e => setSelectedFacility(e.target.value)} disabled={!selectedOrg}>
                  <option value="">— Выберите —</option>
                  {facilities.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>
              </div>
              {facilityData && (
                <>
                  <div className="form-group">
                    <label className="form-label">Класс опасности</label>
                    <input className="form-input" value={facilityData.hazard_class || '—'} readOnly style={{ background: 'var(--gray-50)' }} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Регистрационный номер</label>
                    <input className="form-input" value={facilityData.reg_number || '—'} readOnly style={{ background: 'var(--gray-50)' }} />
                  </div>
                  <div className="form-group full">
                    <label className="form-label">Адрес объекта</label>
                    <input className="form-input" value={facilityData.address || '—'} readOnly style={{ background: 'var(--gray-50)' }} />
                  </div>
                </>
              )}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 24 }}>
              <button className="btn btn-primary" onClick={() => setStep(2)} disabled={!selectedFacility}>
                Далее <i className="fas fa-arrow-right"></i>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Контекст */}
      {step === 2 && (
        <div className="section">
          <div className="section-header"><div className="section-title">Шаг 2: Проверка контекста</div></div>
          <div className="p-24">
            <div style={{ marginBottom: 24 }}>
              <div className="form-header mb-12">Оборудование на объекте</div>
              {equipment.length === 0 ? (
                <div style={{ color: 'var(--gray-400)', fontSize: 13 }}>Нет оборудования</div>
              ) : (
                <table className="data-table">
                  <thead><tr><th>Наименование</th><th>Тип</th><th>Зав. номер</th></tr></thead>
                  <tbody>
                    {equipment.map(eq => (
                      <tr key={eq.id}>
                        <td><strong>{eq.name}</strong></td>
                        <td>{eq.equipment_type || '—'}</td>
                        <td>{eq.serial_number || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div style={{ marginBottom: 24 }}>
              <div className="form-header mb-12">Опасные вещества</div>
              {substances.length === 0 ? (
                <div style={{ color: 'var(--gray-400)', fontSize: 13 }}>Нет веществ</div>
              ) : (
                <table className="data-table">
                  <thead><tr><th>Вещество</th><th>CAS</th><th>Количество, кг</th></tr></thead>
                  <tbody>
                    {substances.map(s => (
                      <tr key={s.id}>
                        <td><strong>{s.name}</strong></td>
                        <td>{s.cas_number || '—'}</td>
                        <td>{s.quantity_kg ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div>
              <div className="form-header mb-12">Ответственные лица</div>
              {persons.length === 0 ? (
                <div style={{ color: 'var(--gray-400)', fontSize: 13 }}>Нет лиц</div>
              ) : (
                <table className="data-table">
                  <thead><tr><th>ФИО</th><th>Должность</th><th>Телефон</th></tr></thead>
                  <tbody>
                    {persons.map(p => (
                      <tr key={p.id}>
                        <td><strong>{p.full_name}</strong></td>
                        <td>{p.position || '—'}</td>
                        <td>{p.phone || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="flex-between mt-24">
              <button className="btn btn-secondary" onClick={() => setStep(1)}><i className="fas fa-arrow-left"></i> Назад</button>
              <button className="btn btn-primary" onClick={() => setStep(3)}>Далее <i className="fas fa-arrow-right"></i></button>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Расчёты */}
      {step === 3 && (
        <div className="section">
          <div className="section-header"><div className="section-title">Шаг 3: Расчёт зон поражения</div></div>
          <div className="p-24">
            <div className="cards-grid" style={{ marginBottom: 24 }}>
              <div className="info-card">
                <div className="info-card-header">
                  <div className="info-card-icon" style={{ background: 'var(--danger-light)', color: 'var(--danger)' }}><i className="fas fa-bomb"></i></div>
                  <div><div className="info-card-title">Взрыв</div><div className="text-muted text-sm">Метод эквивалента ТНТ</div></div>
                </div>
                <div className="info-card-desc">Расчёт зон смертельного поражения, тяжёлых ранений и осколочного поражения.</div>
                <div className="info-card-meta"><div className="info-card-meta-item">Норматив: <strong>РД 03-409-01</strong></div></div>
              </div>
              <div className="info-card">
                <div className="info-card-header">
                  <div className="info-card-icon" style={{ background: 'var(--warning-light)', color: 'var(--warning)' }}><i className="fas fa-fire"></i></div>
                  <div><div className="info-card-title">Тепловое излучение</div><div className="text-muted text-sm">Модель пожарного шара</div></div>
                </div>
                <div className="info-card-desc">Расчёт зон термического поражения при пожарах пролива и факельных пожарах.</div>
                <div className="info-card-meta"><div className="info-card-meta-item">Норматив: <strong>ГОСТ Р 12.3.047</strong></div></div>
              </div>
              <div className="info-card">
                <div className="info-card-header">
                  <div className="info-card-icon" style={{ background: 'var(--primary-light)', color: 'var(--primary)' }}><i className="fas fa-skull-crossbones"></i></div>
                  <div><div className="info-card-title">Токсическое облако</div><div className="text-muted text-sm">Атмосферная дисперсия</div></div>
                </div>
                <div className="info-card-desc">Расчёт зон химического заражения при аварийном выбросе токсичных веществ.</div>
                <div className="info-card-meta"><div className="info-card-meta-item">Норматив: <strong>Методика ОМТ</strong></div></div>
              </div>
            </div>
            <div className="flex-between mt-24">
              <button className="btn btn-secondary" onClick={() => setStep(2)}><i className="fas fa-arrow-left"></i> Назад</button>
              <button className="btn btn-primary" onClick={() => setStep(4)}>Далее <i className="fas fa-arrow-right"></i></button>
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Генерация */}
      {step === 4 && (
        <div className="section">
          <div className="section-header"><div className="section-title">Шаг 4: Генерация документа</div></div>
          <div className="p-24">
            {!status || status === 'processing' ? (
              <div>
                <GenerationProgress
                  facilityId={selectedFacility}
                  onComplete={(data) => {
                    setDocumentId(data.document_id);
                    setStatus(data.status || 'pending_review');
                  }}
                  onError={(err) => {
                    setStatus('error');
                    alert(`Ошибка: ${err.message || err}`);
                  }}
                />
              </div>
            ) : status === 'error' ? (
              <div className="empty-state">
                <i className="fas fa-times-circle" style={{ fontSize: 40, color: 'var(--danger)', marginBottom: 12 }}></i>
                <div className="font-bold mb-8">Ошибка генерации</div>
                <button className="btn btn-primary" onClick={() => { setStatus(null); setGenStep(0); }}>Попробовать снова</button>
              </div>
            ) : (
              <div>
                <div className="alert alert-success" style={{ textAlign: 'center' }}>
                  <i className="fas fa-check-circle" style={{ fontSize: 24, marginRight: 8 }}></i>
                  <span style={{ fontWeight: 600 }}>ПМЛА успешно сгенерирован!</span>
                </div>
                <div className="grid-2 gap-16 mb-20">
                  <div className="info-block">
                    <div className="info-block-label">Документ</div>
                    <div className="info-block-value">{documentId?.slice(0, 8)}</div>
                  </div>
                  <div className="info-block">
                    <div className="info-block-label">Статус</div>
                    <div className="info-block-value" style={{ color: status === 'approved' ? 'var(--success)' : 'var(--warning)' }}>{statusLabels[status] || status}</div>
                  </div>
                </div>
                <div className="flex-center gap-8 flex-wrap">
                  <button className="btn btn-secondary" onClick={() => handleDownload('docx')} disabled={status !== 'approved'} title={status !== 'approved' ? 'Сначала утвердите документ' : 'Скачать DOCX'}><i className="fas fa-download"></i> Скачать DOCX</button>
                  <button className="btn btn-secondary" onClick={() => handleDownload('pdf')} disabled={status !== 'approved'} title={status !== 'approved' ? 'Сначала утвердите документ' : 'Скачать PDF'}><i className="fas fa-file-pdf"></i> Скачать PDF</button>
                </div>
                {status !== 'approved' && (
                  <div className="text-center mt-12 text-muted">
                    <i className="fas fa-info-circle"></i> Для скачивания необходимо утвердить документ
                  </div>
                )}
                <div className="flex-between mt-24">
                  <button className="btn btn-secondary" onClick={() => setStep(3)}><i className="fas fa-arrow-left"></i> Назад</button>
                  <button className="btn btn-primary" onClick={() => { setPreviewLoading(true); pmlaApi.preview(documentId).then(setPreviewData).catch(() => {}).finally(() => setPreviewLoading(false)); setStep(5); }}>Просмотреть <i className="fas fa-arrow-right"></i></button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 5: Просмотр */}
      {step === 5 && (
        <div className="section">
          <div className="section-header"><div className="section-title">Шаг 5: Просмотр документа</div></div>
          <div className="p-24">
            {previewLoading ? (
              <div className="loading-center"><div className="spinner"></div><div style={{ marginTop: 12, color: 'var(--gray-500)' }}>Загрузка превью...</div></div>
            ) : previewData ? (
              <div>
                <div className="info-block mb-20">
                  <div className="grid-3 gap-16" style={{ fontSize: 13 }}>
                    <div><span className="text-muted">Организация: </span><strong>{previewData.organization_name || '—'}</strong></div>
                    <div><span className="text-muted">Объект: </span><strong>{previewData.facility_name || '—'}</strong></div>
                    <div><span className="text-muted">Статус: </span><strong>{statusLabels[previewData.status] || previewData.status}</strong></div>
                  </div>
                </div>

                {previewData.issues && previewData.issues.length > 0 && (
                  <div className="alert alert-warning" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                    <div className="font-bold mb-8"><i className="fas fa-exclamation-triangle"></i> Замечания валидации:</div>
                    {previewData.issues.map((issue, i) => (
                      <div key={i} className="text-primary mb-4">
                        <strong>{issue.section}</strong>: {issue.reason} <span className="badge badge-review" style={{ marginLeft: 4 }}>{issue.severity}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div style={{ marginBottom: 20 }}>
                  {previewData.sections && previewData.sections.map((section, i) => (
                    <div key={i} style={{ marginBottom: 16 }}>
                      {section.title && <h3 className="font-bold mb-8" style={{ fontSize: 15, borderBottom: '1px solid var(--gray-100)', paddingBottom: 6 }}>{section.title}</h3>}
                      {section.content && section.content.map((p, j) => (
                        <p key={j} className="text-primary mb-4" style={{ lineHeight: 1.6 }}>{p}</p>
                      ))}
                    </div>
                  ))}
                  {(!previewData.sections || previewData.sections.length === 0) && (
                    <div className="text-muted text-center p-24">Содержимое документа недоступно для просмотра</div>
                  )}
                </div>

                {previewData.calculations && previewData.calculations.length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <h3 className="font-bold mb-8" style={{ fontSize: 15 }}>Расчёты</h3>
                    <table className="data-table">
                      <thead><tr><th>Методика</th><th>Вещество</th><th>Зона</th><th>Радиус</th></tr></thead>
                      <tbody>
                        {previewData.calculations.map((c, i) => (
                          <tr key={i}>
                            <td>{c.method || c.calculation_method || '—'}</td>
                            <td>{c.substance || c.substance_name || '—'}</td>
                            <td>{c.zone || c.zone_name || '—'}</td>
                            <td>{c.radius_m ? `${c.radius_m} м` : c.value || '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <div className="flex-between mt-24">
                  <button className="btn btn-secondary" onClick={() => setStep(4)}><i className="fas fa-arrow-left"></i> Назад</button>
                  <div style={{ display: 'flex', gap: 8 }}>
                    {status === 'pending_review' && (
                      <button className="btn btn-success" onClick={() => handleReview('approved')} disabled={loading}>
                        <i className="fas fa-check"></i> Утвердить
                      </button>
                    )}
                    <button className="btn btn-secondary" onClick={() => handleDownload('docx')} disabled={status !== 'approved'} title={status !== 'approved' ? 'Сначала утвердите документ' : 'Скачать DOCX'}><i className="fas fa-download"></i> Скачать DOCX</button>
                    <button className="btn btn-primary" onClick={() => setStep(6)}>Перейти к ревью <i className="fas fa-arrow-right"></i></button>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: 'var(--gray-400)' }}>
                <div style={{ marginBottom: 12 }}>Не удалось загрузить превью</div>
                <button className="btn btn-primary" onClick={() => { setPreviewLoading(true); pmlaApi.preview(documentId).then(setPreviewData).catch(() => {}).finally(() => setPreviewLoading(false)); }}>Повторить</button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Step 6: Ревью */}
      {step === 6 && (
        <div className="section">
          <div className="section-header"><div className="section-title">Шаг 5: Ревью и утверждение</div></div>
          <div className="p-24">
            <div className="grid-2" style={{ gap: 24 }}>
              <div>
                <div className="form-header">Результаты автоматической валидации</div>
                <div className="flex-col gap-10">
                  <div className="alert alert-success mb-0">
                    <i className="fas fa-check-circle"></i>
                    <div className="text-primary">Все обязательные разделы присутствуют</div>
                  </div>
                  <div className="alert alert-success mb-0">
                    <i className="fas fa-check-circle"></i>
                    <div className="text-primary">Контактные данные валидны</div>
                  </div>
                  <div className="alert alert-warning mb-0">
                    <i className="fas fa-exclamation-triangle"></i>
                    <div className="text-primary">Рекомендуется проверить ссылки на нормативы</div>
                  </div>
                  <div className="alert alert-success mb-0">
                    <i className="fas fa-check-circle"></i>
                    <div className="text-primary">Расчёты зон поражения корректны</div>
                  </div>
                </div>
              </div>
              <div>
                <div className="form-header mb-16">Действия</div>
                <div className="flex-col gap-12">
                  <button className="btn btn-success flex-center p-16" onClick={() => handleReview('approved')} disabled={loading || status !== 'pending_review'}>
                    <i className="fas fa-check"></i> Утвердить ПМЛА
                  </button>
                  <button className="btn btn-secondary flex-center p-16" onClick={() => handleDownload('docx')} disabled={status !== 'approved'}>
                    <i className="fas fa-download"></i> Скачать DOCX
                  </button>
                  <button className="btn btn-danger flex-center p-16" onClick={() => handleReview('rejected')} disabled={loading || status !== 'pending_review'}>
                    <i className="fas fa-undo"></i> Вернуть на доработку
                  </button>
                </div>
              </div>
            </div>
            <div className="flex-between mt-24">
              <button className="btn btn-secondary" onClick={() => setStep(5)}><i className="fas fa-arrow-left"></i> Назад</button>
              <button className="btn btn-primary" onClick={() => navigate('/documents')}>Перейти к документам <i className="fas fa-arrow-right"></i></button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
